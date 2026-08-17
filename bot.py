"""
Cliente websocket para The Code Challenge (juego: Snake).

Uso:
    python bot.py <TU_TOKEN>
    python bot.py <TU_TOKEN> --challenge rival@mail.com
    python bot.py                     # toma el token de la variable BOT_TOKEN

Que hace:
  - se conecta al servidor y se queda esperando
  - acepta automaticamente los desafios que le llegan
  - en cada `your_turn` le pide la jugada a strategy.choose_direction()
  - imprime el tablero y guarda un log por partida en game_<id>.log
"""

import argparse
import asyncio
import json
import os
import sys
import time

try:
    import websockets
except ImportError:
    sys.exit("Falta la libreria websockets. Instalala con:  pip install websockets")

from strategy import choose_direction, evaluar_movimientos

SERVER = "wss://codechallenge-server.up.railway.app:443/ws"
JUEGO = "snake"


class SnakeBot:
    def __init__(self, token, retar_a=None, mostrar_debug=False):
        self.token = token
        self.retar_a = retar_a
        self.mostrar_debug = mostrar_debug
        self.usuarios = []
        self.ya_rete = False
        self.logs = {}          # game_id -> file handle
        self.turnos = 0

    # -- logging -----------------------------------------------------------

    def _log(self, game_id, linea):
        if not game_id:
            return
        if game_id not in self.logs:
            self.logs[game_id] = open(f"game_{game_id}.log", "a", encoding="utf-8")
        self.logs[game_id].write(linea + "\n")
        self.logs[game_id].flush()

    def _cerrar_log(self, game_id):
        f = self.logs.pop(game_id, None)
        if f:
            f.close()

    # -- envio -------------------------------------------------------------

    async def enviar(self, ws, action, data, game_id=None):
        mensaje = {"action": action, "data": data}
        crudo = json.dumps(mensaje)
        await ws.send(crudo)
        self._log(game_id, "> " + crudo)

    # -- manejo de eventos -------------------------------------------------

    async def manejar(self, ws, mensaje):
        evento = mensaje.get("event")
        data = mensaje.get("data") or {}
        game_id = data.get("game_id")
        self._log(game_id, "< " + json.dumps(mensaje))

        if evento == "list_users":
            self.usuarios = data.get("users", [])
            print(f"[online] {', '.join(self.usuarios) or '(nadie mas)'}")
            if self.retar_a and not self.ya_rete and self.retar_a in self.usuarios:
                self.ya_rete = True
                print(f"[reto] desafiando a {self.retar_a}...")
                await self.enviar(ws, "challenge",
                                  {"opponent": self.retar_a, "game": JUEGO})

        elif evento == "challenge":
            challenge_id = data.get("challenge_id")
            print(f"[reto] {data.get('opponent')} me desafio -> acepto ({challenge_id})")
            await self.enviar(ws, "accept_challenge", {"challenge_id": challenge_id})

        elif evento == "your_turn":
            await self.jugar_turno(ws, data)

        elif evento == "game_over":
            self.mostrar_resultado(data)
            self._cerrar_log(game_id)
            self.turnos = 0
            self.ya_rete = False

        elif evento == "error":
            print(f"[ERROR del server] {data}")

        else:
            print(f"[evento desconocido] {evento}: {data}")

    async def jugar_turno(self, ws, data):
        arranque = time.perf_counter()
        direccion = choose_direction(data)
        ms = (time.perf_counter() - arranque) * 1000
        self.turnos += 1

        self.mostrar_tablero(data, direccion, ms)

        await self.enviar(
            ws, "move",
            {
                "game_id": data.get("game_id"),
                "turn_token": data.get("turn_token"),
                "direction": direccion,
            },
            game_id=data.get("game_id"),
        )

    # -- presentacion ------------------------------------------------------

    def mostrar_tablero(self, data, direccion, ms):
        board = data.get("board", "")
        print("\n" + "=" * 40)
        print(f"turno {self.turnos} | lado {data.get('side')} | "
              f"quedan {data.get('remaining_moves')} | "
              f"{data.get('score_1')} - {data.get('score_2')}")
        print(board)
        print(f"-> {direccion.upper()}  ({ms:.1f} ms)")

        if self.mostrar_debug:
            for op in evaluar_movimientos(data):
                print(f"   {op['direccion']:<5} espacio={op['espacio']:<4} "
                      f"comida={op['dist_comida']:<3} riesgo={op['riesgo']} "
                      f"seguro={op['seguro']} puntaje={op['puntaje']:.1f}")

    def mostrar_resultado(self, data):
        print("\n" + "#" * 40)
        print("PARTIDA TERMINADA")
        print(data.get("board", ""))
        print(f"{data.get('player_1')}: {data.get('score_1')}")
        print(f"{data.get('player_2')}: {data.get('score_2')}")
        print(f"ganador: {data.get('winner')}")
        print("#" * 40 + "\n")

    # -- loop principal ----------------------------------------------------

    async def run(self):
        url = f"{SERVER}?token={self.token}"
        print("Conectando al servidor...")
        async for ws in websockets.connect(url, ping_interval=20, ping_timeout=20):
            try:
                print("Conectado. Esperando desafios (Ctrl+C para salir).")
                async for crudo in ws:
                    try:
                        mensaje = json.loads(crudo)
                    except json.JSONDecodeError:
                        print(f"[raw] {crudo}")
                        continue
                    await self.manejar(ws, mensaje)
            except websockets.ConnectionClosed:
                print("Conexion cerrada, reintentando en 3s...")
                await asyncio.sleep(3)
                continue


def main():
    parser = argparse.ArgumentParser(description="Bot de Snake para The Code Challenge")
    parser.add_argument("token", nargs="?", default=os.environ.get("BOT_TOKEN"),
                        help="token del bot (o usa la variable de entorno BOT_TOKEN)")
    parser.add_argument("--challenge", dest="retar_a", default=None,
                        help="email del rival a desafiar apenas este online")
    parser.add_argument("--debug", action="store_true",
                        help="muestra el puntaje de cada movimiento posible")
    args = parser.parse_args()

    if not args.token:
        sys.exit("Falta el token: python bot.py <TU_TOKEN>")

    bot = SnakeBot(args.token, retar_a=args.retar_a, mostrar_debug=args.debug)
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\nChau.")


if __name__ == "__main__":
    main()
