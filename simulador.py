"""
Simulador local de Snake (2 jugadores, por turnos).

Sirve para probar tu estrategia SIN depender del servidor ni de que haya
rivales conectados. Replica las reglas del enunciado:
  comer = +100 | sobrevivir un movimiento = +1 | chocar = -500 y el rival +1000

Uso:
    python simulador.py                # 50 partidas contra un bot glotón
    python simulador.py --partidas 200
    python simulador.py --ver          # muestra el tablero jugada a jugada
    python simulador.py --rival random
"""

import argparse
import random
import time

import strategy

FILAS, COLUMNAS = 15, 15
MAX_MOVIMIENTOS = 300
MANZANAS = 3

DELTAS = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}


class Serpiente:
    def __init__(self, cabeza, cuerpo, letra):
        self.celdas = [cabeza] + list(cuerpo)   # [0] = cabeza, [-1] = cola
        self.letra = letra
        self.score = 0
        self.viva = True

    @property
    def cabeza(self):
        return self.celdas[0]

    def ocupa(self):
        return set(self.celdas)


class Juego:
    def __init__(self, semilla=None):
        self.rng = random.Random(semilla)
        self.a = Serpiente((7, 3), [(7, 2), (7, 1)], "A")
        self.b = Serpiente((7, 11), [(7, 12), (7, 13)], "B")
        self.comida = set()
        self.movimientos = MAX_MOVIMIENTOS
        while len(self.comida) < MANZANAS:
            self.spawn_comida()

    # -- tablero -----------------------------------------------------------

    def spawn_comida(self):
        libres = [
            (r, c)
            for r in range(FILAS)
            for c in range(COLUMNAS)
            if (r, c) not in self.a.ocupa()
            and (r, c) not in self.b.ocupa()
            and (r, c) not in self.comida
        ]
        if libres:
            self.comida.add(self.rng.choice(libres))

    def render(self):
        grid = [[" "] * COLUMNAS for _ in range(FILAS)]
        for r, c in self.comida:
            grid[r][c] = "*"
        for snake in (self.a, self.b):
            for i, (r, c) in enumerate(snake.celdas):
                grid[r][c] = snake.letra if i == 0 else snake.letra.lower()
        return "\n".join("|" + "".join(fila) + "|" for fila in grid)

    def turn_data(self, quien):
        return {
            "board": self.render(),
            "rows": FILAS,
            "cols": COLUMNAS,
            "remaining_moves": self.movimientos,
            "side": quien.letra,
            "player_1": "bot_a",
            "score_1": self.a.score,
            "player_2": "bot_b",
            "score_2": self.b.score,
            "game_id": "sim",
            "turn_token": "t",
        }

    # -- reglas ------------------------------------------------------------

    def mover(self, quien, rival, direccion):
        dr, dc = DELTAS.get(direccion, (-1, 0))
        r, c = quien.cabeza
        nueva = (r + dr, c + dc)

        fuera = not (0 <= nueva[0] < FILAS and 0 <= nueva[1] < COLUMNAS)
        choca = nueva in quien.ocupa() or nueva in rival.ocupa()

        if fuera or choca:
            quien.viva = False
            quien.score -= 500
            rival.score += 1000
            return False

        come = nueva in self.comida
        quien.celdas.insert(0, nueva)
        if come:
            self.comida.discard(nueva)
            quien.score += 100
            self.spawn_comida()
        else:
            quien.celdas.pop()
        quien.score += 1
        return True

    def jugar(self, estrategia_a, estrategia_b, ver=False, pausa=0.08):
        turno = 0
        while self.movimientos > 0 and self.a.viva and self.b.viva:
            quien, rival, estrategia = (
                (self.a, self.b, estrategia_a) if turno % 2 == 0
                else (self.b, self.a, estrategia_b)
            )
            direccion = estrategia(self.turn_data(quien))
            self.mover(quien, rival, direccion)

            if ver:
                print("\033[2J\033[H", end="")   # limpiar pantalla
                print(self.render())
                print(f"A={self.a.score}  B={self.b.score}  "
                      f"quedan={self.movimientos}  ultimo={quien.letra}:{direccion}")
                time.sleep(pausa)

            turno += 1
            self.movimientos -= 1

        return self.a, self.b


# ---------------------------------------------------------------------------
# Rivales para practicar
# ---------------------------------------------------------------------------

def rival_random(turn_data):
    """Se mueve al azar, pero esquiva la muerte obvia de un paso."""
    estado = strategy.Estado(turn_data)
    if not estado.mi_cabeza:
        return "up"
    r, c = estado.mi_cabeza
    opciones = []
    for nombre, (dr, dc) in DELTAS.items():
        nueva = (r + dr, c + dc)
        if estado.dentro(nueva) and nueva not in estado.ocupadas:
            opciones.append(nombre)
    return random.choice(opciones) if opciones else "up"


def rival_gloton(turn_data):
    """Va derecho a la manzana mas cercana; solo evita morir en el paso siguiente."""
    estado = strategy.Estado(turn_data)
    if not estado.mi_cabeza or not estado.comida:
        return rival_random(turn_data)
    r, c = estado.mi_cabeza
    objetivo = min(estado.comida, key=lambda f: abs(f[0] - r) + abs(f[1] - c))
    mejores = []
    for nombre, (dr, dc) in DELTAS.items():
        nueva = (r + dr, c + dc)
        if not estado.dentro(nueva) or nueva in estado.ocupadas:
            continue
        d = abs(nueva[0] - objetivo[0]) + abs(nueva[1] - objetivo[1])
        mejores.append((d, nombre))
    if not mejores:
        return "up"
    mejores.sort()
    return mejores[0][1]


RIVALES = {
    "gloton": rival_gloton,
    "random": rival_random,
    "yo": strategy.choose_direction,
}


# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--partidas", type=int, default=50)
    parser.add_argument("--rival", choices=sorted(RIVALES), default="gloton")
    parser.add_argument("--ver", action="store_true", help="animar una partida")
    args = parser.parse_args()

    rival = RIVALES[args.rival]

    if args.ver:
        juego = Juego(semilla=random.randrange(10_000))
        a, b = juego.jugar(strategy.choose_direction, rival, ver=True)
        print(f"\nFinal -> yo(A)={a.score}  rival(B)={b.score}")
        return

    ganadas = empates = muertes = 0
    total_mio = 0
    manzanas = 0
    inicio = time.perf_counter()

    for i in range(args.partidas):
        juego = Juego(semilla=i)
        a, b = juego.jugar(strategy.choose_direction, rival)
        total_mio += a.score
        if not a.viva:
            muertes += 1
        if a.score > b.score:
            ganadas += 1
        elif a.score == b.score:
            empates += 1
        manzanas += max(0, (a.score + (500 if not a.viva else 0)) // 100)

    dur = time.perf_counter() - inicio
    print(f"Partidas: {args.partidas} contra '{args.rival}'  ({dur:.1f}s)")
    print(f"  ganadas    : {ganadas} ({100*ganadas/args.partidas:.0f}%)")
    print(f"  empatadas  : {empates}")
    print(f"  choques mios: {muertes} ({100*muertes/args.partidas:.0f}%)")
    print(f"  score promedio: {total_mio/args.partidas:.0f}")


if __name__ == "__main__":
    main()
