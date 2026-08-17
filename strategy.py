"""
Estrategia del bot de Snake.  (v2)

La funcion principal es `choose_direction(turn_data)`: recibe el estado del
turno que manda el servidor y devuelve "up" | "down" | "left" | "right".

Prioridades (salen de las reglas del juego):
  Chocar = -500 y le regala +1000 al rival -> 1500 de diferencia.
  Una manzana = +100.  Sobrevivir un movimiento = +1.
  Conclusion: NO MORIR vale mas que cualquier otra cosa.

Novedades de la v2 (despues de analizar 21 partidas reales, 2 con choque):
  * FLOOD FILL TEMPORAL: no alcanza con saber que una celda esta "conectada",
    hay que saber si llego a tiempo. Las celdas de un cuerpo se liberan recien
    cuando pasa la cola, asi que se modela CUANDO queda libre cada una. Antes
    el bot creia tener 200 celdas libres estando metido en un pasillo ciego.
  * CONTROL DE TERRITORIO (Voronoi): solo cuentan las celdas a las que llego
    ANTES que el rival. Asi deja de meterse en pasillos que el rival cierra.
"""

from collections import deque

# ---------------------------------------------------------------------------
# Configuracion / pesos que podes tunear
# ---------------------------------------------------------------------------

# (fila, columna). Fila 0 = arriba del tablero.
# Verificado contra el servidor real: "up" sube. No hace falta invertir.
DIRECTIONS = {
    "up": (-1, 0),
    "down": (1, 0),
    "left": (0, -1),
    "right": (0, 1),
}
INVERTIR_VERTICAL = False

PESO_ESPACIO = 1.0       # espacio alcanzable a tiempo
PESO_TERRITORIO = 1.5    # celdas que gano yo antes que el rival
PESO_LIBERTAD = 10.0     # salidas de la celda destino
PESO_COMIDA = 20.0       # acercarse a la comida
PESO_RIESGO = 30.0       # castigo por quedar pegado a la cabeza rival
MARGEN_SEGURIDAD = 2     # celdas libres extra que exijo ademas de mi largo


# ---------------------------------------------------------------------------
# Parseo del tablero
# ---------------------------------------------------------------------------

def parse_board(board_str):
    """Convierte el string del tablero en una lista de filas (strings).

    El servidor manda las filas envueltas en '|...|' y unidas por '\\n'.
    Ojo: los espacios DENTRO de las barras son celdas vacias y hay que
    respetarlos, por eso no se hace strip() del contenido.
    """
    filas = []
    for linea in board_str.split("\n"):
        linea = linea.rstrip("\r")
        if not linea.strip():
            continue
        ini = linea.find("|")
        fin = linea.rfind("|")
        if ini != -1 and fin != -1 and fin > ini:
            linea = linea[ini + 1:fin]
        filas.append(linea)

    if not filas:
        return []
    ancho = max(len(f) for f in filas)
    return [f.ljust(ancho) for f in filas]


def _vecinos(celda):
    r, c = celda
    return ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))


def _indices_cuerpo(cabeza, cuerpo):
    """Distancia de cada celda del cuerpo a la cabeza, siguiendo la serpiente.

    Devuelve {celda: indice}, con la cabeza en 0. Sirve para saber en cuantos
    turnos se libera cada celda: la cola es la primera en liberarse.
    """
    if cabeza is None:
        return {}
    indices = {cabeza: 0}
    cola_bfs = deque([cabeza])
    while cola_bfs:
        celda = cola_bfs.popleft()
        for vec in _vecinos(celda):
            if vec in cuerpo and vec not in indices:
                indices[vec] = indices[celda] + 1
                cola_bfs.append(vec)
    return indices


class Estado:
    """Vista comoda del turno: donde esta cada cosa en el tablero."""

    def __init__(self, turn_data):
        data = dict(turn_data)
        if isinstance(data.get("turn_data"), dict):
            anidado = data.pop("turn_data")
            data = {**anidado, **data}

        self.grid = parse_board(data.get("board", ""))
        self.rows = len(self.grid)
        self.cols = len(self.grid[0]) if self.grid else 0
        self.remaining_moves = data.get("remaining_moves", 0)

        self.side = (data.get("side") or "A").strip().upper() or "A"
        mi_cabeza = self.side
        mi_cuerpo = self.side.lower()
        rival_cabeza = "B" if self.side == "A" else "A"
        rival_cuerpo = rival_cabeza.lower()

        self.comida = set()
        self.mi_cabeza = None
        self.mi_cuerpo = set()
        self.rival_cabeza = None
        self.rival_cuerpo = set()

        for r, fila in enumerate(self.grid):
            for c, ch in enumerate(fila):
                if ch == "*":
                    self.comida.add((r, c))
                elif ch == mi_cabeza:
                    self.mi_cabeza = (r, c)
                elif ch == mi_cuerpo:
                    self.mi_cuerpo.add((r, c))
                elif ch == rival_cabeza:
                    self.rival_cabeza = (r, c)
                elif ch == rival_cuerpo:
                    self.rival_cuerpo.add((r, c))

        self.ocupadas = set(self.mi_cuerpo) | set(self.rival_cuerpo)
        if self.mi_cabeza:
            self.ocupadas.add(self.mi_cabeza)
        if self.rival_cabeza:
            self.ocupadas.add(self.rival_cabeza)

        self.mi_largo = len(self.mi_cuerpo) + (1 if self.mi_cabeza else 0)
        self.rival_largo = len(self.rival_cuerpo) + (1 if self.rival_cabeza else 0)

        # indices a lo largo del cuerpo: dicen cuando se libera cada celda
        self.mis_indices = _indices_cuerpo(self.mi_cabeza, self.mi_cuerpo)
        self.indices_rival = _indices_cuerpo(self.rival_cabeza, self.rival_cuerpo)

        self.mi_cola = (max(self.mis_indices, key=self.mis_indices.get)
                        if len(self.mis_indices) > 1 else None)
        self.rival_cola = (max(self.indices_rival, key=self.indices_rival.get)
                           if len(self.indices_rival) > 1 else None)

    def dentro(self, celda):
        r, c = celda
        return 0 <= r < self.rows and 0 <= c < self.cols

    def liberacion(self, crezco=False):
        """{celda ocupada: en cuantos turnos mios queda libre}.

        Una celda con indice i (0 = cabeza) queda libre cuando la cola la pasa,
        o sea dentro de (largo - i) movimientos. Si como, mi cuerpo no se
        acorta este turno y todo se corre uno.
        """
        libre_en = {}
        extra = 1 if crezco else 0
        for celda, i in self.mis_indices.items():
            libre_en[celda] = self.mi_largo - i + extra
        for celda, i in self.indices_rival.items():
            # asumo que el rival tambien puede crecer (pesimista)
            libre_en[celda] = self.rival_largo - i + 1
        return libre_en


# ---------------------------------------------------------------------------
# Medidas de espacio
# ---------------------------------------------------------------------------

def espacio_temporal(estado, inicio, libre_en, bloqueo_duro=()):
    """Flood fill que tiene en cuenta EL TIEMPO.

    Avanza turno a turno desde `inicio`. Una celda ocupada solo se puede pisar
    si para cuando llego ya se libero. Esto evita el error de contar como libre
    medio tablero al que en realidad nunca llego.
    """
    if not estado.dentro(inicio):
        return 0, set()
    visitadas = {inicio}
    cola = deque([(inicio, 1)])
    while cola:
        celda, t = cola.popleft()
        for vec in _vecinos(celda):
            if vec in visitadas or not estado.dentro(vec) or vec in bloqueo_duro:
                continue
            if libre_en.get(vec, 0) > t + 1:
                continue          # todavia hay cuerpo ahi cuando llego
            visitadas.add(vec)
            cola.append((vec, t + 1))
    return len(visitadas), visitadas


def _distancias(estado, inicio, bloqueadas):
    """BFS clasico: {celda: distancia} desde `inicio`."""
    if inicio is None or not estado.dentro(inicio):
        return {}
    dist = {inicio: 0}
    cola = deque([inicio])
    while cola:
        celda = cola.popleft()
        for vec in _vecinos(celda):
            if vec in dist or not estado.dentro(vec) or vec in bloqueadas:
                continue
            dist[vec] = dist[celda] + 1
            cola.append(vec)
    return dist


def territorio(mis_dist, dist_rival):
    """Celdas a las que llego yo antes que el rival (diagrama de Voronoi).

    Es la medida que evita los pasillos: si el rival llega antes a la salida,
    ese pasillo no es mio por mas que este "conectado".
    """
    if not dist_rival:
        return len(mis_dist)
    return sum(1 for celda, d in mis_dist.items()
               if d < dist_rival.get(celda, 10 ** 6))


def distancia_bfs(estado, inicio, objetivos, bloqueadas):
    """Distancia al objetivo mas cercano. None si no llego."""
    objetivos = {o for o in objetivos if o is not None}
    if not objetivos:
        return None
    if inicio in objetivos:
        return 0
    visitadas = {inicio}
    cola = deque([(inicio, 0)])
    while cola:
        celda, d = cola.popleft()
        for vec in _vecinos(celda):
            if vec in visitadas or not estado.dentro(vec):
                continue
            visitadas.add(vec)
            if vec in objetivos:
                return d + 1
            if vec in bloqueadas:
                continue
            cola.append((vec, d + 1))
    return None


def region_alcanzable(estado, inicio, bloqueadas):
    """Compatibilidad con la v1."""
    return set(_distancias(estado, inicio, bloqueadas))


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------

def _direcciones():
    for nombre, (dr, dc) in DIRECTIONS.items():
        if INVERTIR_VERTICAL and dr != 0:
            yield nombre, (-dr, dc)
        else:
            yield nombre, (dr, dc)


def evaluar_movimientos(turn_data):
    """Lista de movimientos evaluados, del mejor al peor. Util para debuggear."""
    estado = Estado(turn_data)
    if estado.mi_cabeza is None:
        return []

    # obstaculos para moverme: todo cuerpo (conservador, ni mi propia cola)
    bloqueadas_mov = set(estado.ocupadas)

    # celdas que el rival puede ocupar el turno que viene
    zona_rival = set()
    if estado.rival_cabeza:
        zona_rival = {v for v in _vecinos(estado.rival_cabeza) if estado.dentro(v)}

    # distancias del rival, para el calculo de territorio
    bloq_rival = set(estado.ocupadas)
    bloq_rival.discard(estado.rival_cabeza)
    bloq_rival.discard(estado.rival_cola)
    dist_rival = _distancias(estado, estado.rival_cabeza, bloq_rival)

    resultados = []
    r0, c0 = estado.mi_cabeza

    for nombre, (dr, dc) in _direcciones():
        nueva = (r0 + dr, c0 + dc)
        if not estado.dentro(nueva):
            continue                      # pared
        if nueva in bloqueadas_mov:
            continue                      # cuerpo mio o del rival

        come = nueva in estado.comida
        largo_futuro = estado.mi_largo + (1 if come else 0)

        # --- espacio real, contando el tiempo ---
        libre_en = estado.liberacion(crezco=come)
        espacio, region = espacio_temporal(estado, nueva, libre_en)

        # --- espacio pesimista: el rival avanza y me tapa una salida ---
        espacio_p, _ = espacio_temporal(estado, nueva, libre_en,
                                        bloqueo_duro=zona_rival - {nueva})

        # --- territorio: celdas que gano yo antes que el rival ---
        bloq_est = set(estado.ocupadas)
        bloq_est.discard(estado.mi_cola)
        bloq_est.discard(estado.rival_cola)
        mis_dist = _distancias(estado, nueva, bloq_est)
        terr = territorio(mis_dist, dist_rival)

        # --- puedo volver a mi cola? es la garantia de no encerrarme ---
        alcanzo_cola = estado.mi_cola is None or estado.mi_cola in region

        # --- comida ---
        objetivos = estado.comida & region
        dist_comida = distancia_bfs(estado, nueva, objetivos - {nueva}, bloq_est)
        if come:
            dist_comida = 0

        persiguiendo_cola = False
        if dist_comida is None:
            dist_comida = distancia_bfs(estado, nueva, {estado.mi_cola}, bloq_est)
            persiguiendo_cola = dist_comida is not None
        if dist_comida is None:
            dist_comida = 20

        riesgo = 1 if nueva in zona_rival else 0
        umbral = largo_futuro + MARGEN_SEGURIDAD
        espacio_ok = espacio >= umbral
        espacio_p_ok = espacio_p >= umbral
        territorio_ok = terr >= umbral

        # nivel 2 = comodo | 1 = justo | 0 = peligroso
        if alcanzo_cola and espacio_ok and espacio_p_ok and territorio_ok:
            nivel = 2
        elif espacio_ok and (alcanzo_cola or espacio_p_ok):
            nivel = 1
        else:
            nivel = 0

        libertad = sum(1 for v in _vecinos(nueva)
                       if estado.dentro(v) and v not in bloqueadas_mov)

        puntaje = (
            PESO_ESPACIO * (espacio + espacio_p) / 2
            + PESO_TERRITORIO * terr
            + PESO_LIBERTAD * libertad
            - PESO_COMIDA * min(dist_comida, 20)
            - PESO_RIESGO * riesgo
        )
        if persiguiendo_cola:
            puntaje -= 30

        resultados.append({
            "direccion": nombre,
            "celda": nueva,
            "nivel": nivel,
            "seguro": nivel == 2,
            "alcanzo_cola": alcanzo_cola,
            "espacio": espacio,
            "espacio_p": espacio_p,
            "territorio": terr,
            "dist_comida": dist_comida,
            "libertad": libertad,
            "riesgo": riesgo,
            "come": come,
            "puntaje": puntaje,
        })

    resultados.sort(key=lambda m: (m["nivel"], m["puntaje"]), reverse=True)
    return resultados


def choose_direction(turn_data):
    """Decide el movimiento del turno. Siempre devuelve una direccion valida."""
    try:
        opciones = evaluar_movimientos(turn_data)
        if opciones:
            return opciones[0]["direccion"]
    except Exception as e:
        print(f"[strategy] error evaluando el turno: {e!r}")

    try:
        estado = Estado(turn_data)
        if estado.mi_cabeza:
            r0, c0 = estado.mi_cabeza
            for nombre, (dr, dc) in _direcciones():
                if estado.dentro((r0 + dr, c0 + dc)):
                    return nombre
    except Exception:
        pass
    return "up"
