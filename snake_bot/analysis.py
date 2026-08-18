"""Herramientas para analizar el tablero.

Son las tres medidas que usa el bot para decidir si un movimiento es seguro:

* :class:`FloodFill` responde "cuanto espacio me queda si voy para alla",
  pero teniendo en cuenta el tiempo: una celda ocupada hoy puede estar libre
  cuando yo llegue, y una celda libre hoy puede no servirme si esta demasiado
  lejos. Ignorar esto fue la causa de los dos unicos choques registrados.
* :class:`PathFinder` mide distancias en cantidad de movimientos, para ir a
  buscar la comida.
* :class:`Territory` compara mis distancias con las del rival y cuenta las
  celdas que puedo reclamar antes que el (diagrama de Voronoi). Es lo que
  detecta a tiempo los pasillos que el rival esta por cerrar.
"""

from collections import deque

from .snake import vecinos


class FloodFill:
    """Cuenta el espacio alcanzable desde una celda, respetando el tiempo.

    Un flood fill comun cuenta celdas conectadas. Ese numero engania: sirve
    de poco un hueco de 200 celdas si para entrar hay que atravesar un cuerpo
    que recien se mueve dentro de quince turnos. Esta version avanza turno a
    turno y solo pisa una celda si ya se libero para cuando llega.
    """

    def __init__(self, board, libre_en=None):
        """Prepara el recorrido.

        Args:
            board: instancia de :class:`~snake_bot.board.Board`.
            libre_en: diccionario ``{celda: turnos que faltan para liberarse}``,
                tal como lo arma ``GameState.liberacion()``. Si no se pasa, se
                asume que el tablero esta vacio de serpientes.
        """
        self._board = board
        self._libre_en = dict(libre_en or {})

    def _disponible(self, celda, turno, visitadas, bloqueadas):
        """Indica si se puede pisar `celda` al llegar en el turno indicado."""
        if celda in visitadas or celda in bloqueadas:
            return False
        if not self._board.dentro(celda):
            return False
        return self._libre_en.get(celda, 0) <= turno

    def _expandir(self, celda, turno, visitadas, pendientes, bloqueadas):
        """Agrega a la cola los vecinos que se puedan pisar."""
        for vecino in vecinos(celda):
            if self._disponible(vecino, turno, visitadas, bloqueadas):
                visitadas.add(vecino)
                pendientes.append((vecino, turno))

    def alcanzables(self, inicio, bloqueadas=frozenset()):
        """Devuelve el conjunto de celdas a las que llego a tiempo.

        Args:
            inicio: celda desde donde arranca el recorrido.
            bloqueadas: celdas prohibidas sin importar el tiempo. Se usa para
                el calculo pesimista, marcando donde podria estar el rival.

        Returns:
            set: celdas alcanzables, incluida `inicio`.
        """
        if not self._board.dentro(inicio):
            return set()
        visitadas = {inicio}
        pendientes = deque([(inicio, 1)])
        while pendientes:
            celda, turno = pendientes.popleft()
            self._expandir(celda, turno + 1, visitadas, pendientes, bloqueadas)
        return visitadas

    def espacio(self, inicio, bloqueadas=frozenset()):
        """Cantidad de celdas alcanzables desde `inicio`."""
        return len(self.alcanzables(inicio, bloqueadas))


class PathFinder:
    """Calcula distancias en movimientos sobre el tablero (BFS)."""

    def __init__(self, board):
        """Guarda el tablero sobre el que se van a medir las distancias."""
        self._board = board

    def _vecinos_libres(self, celda, distancias, bloqueadas):
        """Vecinos de `celda` que estan dentro, libres y sin visitar."""
        return [vecino for vecino in vecinos(celda)
                if vecino not in distancias
                and vecino not in bloqueadas
                and self._board.dentro(vecino)]

    def distancias(self, inicio, bloqueadas=frozenset()):
        """Mide la distancia desde `inicio` a cada celda alcanzable.

        Args:
            inicio: celda de partida, o None.
            bloqueadas: celdas que no se pueden atravesar.

        Returns:
            dict: ``{celda: cantidad de movimientos}``. Vacio si `inicio` no
            es una celda valida del tablero.
        """
        if inicio is None or not self._board.dentro(inicio):
            return {}
        distancias = {inicio: 0}
        pendientes = deque([inicio])
        while pendientes:
            celda = pendientes.popleft()
            self._registrar(celda, distancias, pendientes, bloqueadas)
        return distancias

    def _registrar(self, celda, distancias, pendientes, bloqueadas):
        """Anota la distancia de los vecinos todavia no visitados."""
        for vecino in self._vecinos_libres(celda, distancias, bloqueadas):
            distancias[vecino] = distancias[celda] + 1
            pendientes.append(vecino)

    @staticmethod
    def _metas_validas(objetivos):
        """Descarta los objetivos nulos."""
        return {objetivo for objetivo in objetivos if objetivo is not None}

    def distancia_a(self, inicio, objetivos, bloqueadas=frozenset()):
        """Distancia al objetivo mas cercano.

        Los objetivos nunca se consideran bloqueados: si hay comida sobre una
        celda que ademas figura como obstaculo, igual se puede llegar a ella.

        Args:
            inicio: celda de partida.
            objetivos: celdas a las que se quiere llegar.
            bloqueadas: celdas que no se pueden atravesar.

        Returns:
            int | None: cantidad de movimientos, o None si no se llega a ninguno.
        """
        metas = self._metas_validas(objetivos)
        if not metas:
            return None
        alcanzadas = self.distancias(inicio, set(bloqueadas) - metas)
        return min((alcanzadas[meta] for meta in metas if meta in alcanzadas),
                   default=None)


class Territory:
    """Reparte el tablero entre las dos serpientes segun quien llega antes.

    Es un diagrama de Voronoi simplificado. Una celda "es mia" si llego a ella
    en menos movimientos que el rival. Cuando quedan pocas celdas propias, el
    movimiento me esta metiendo en una zona que el rival domina, aunque el
    espacio total todavia parezca amplio.
    """

    def __init__(self, mis_distancias, distancias_rival):
        """Recibe los dos mapas de distancias ya calculados.

        Args:
            mis_distancias: ``{celda: distancia}`` desde mi posicion.
            distancias_rival: ``{celda: distancia}`` desde la cabeza rival.
        """
        self._mias = dict(mis_distancias)
        self._rival = dict(distancias_rival)

    def _gano(self, celda, distancia):
        """True si llego a `celda` estrictamente antes que el rival."""
        return distancia < self._rival.get(celda, float("inf"))

    def celdas_propias(self):
        """Conjunto de celdas que alcanzo antes que el rival."""
        return {celda for celda, distancia in self._mias.items()
                if self._gano(celda, distancia)}

    def contar(self):
        """Cantidad de celdas bajo mi control."""
        return len(self.celdas_propias())
