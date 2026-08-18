"""Punto de entrada del bot.

Abre la conexion con el servidor y le pasa cada mensaje al cliente. Toda la
logica vive en el paquete ``snake_bot``; este archivo solo se ocupa del
websocket, que es lo unico que no se puede probar sin un servidor real.

Uso::

    python run.py <TOKEN>
    BOT_TOKEN=<TOKEN> python run.py
"""

import asyncio
import sys

import websockets

from snake_bot.cli import crear_cliente


async def escuchar(cliente, oponente):
    """Se conecta y procesa mensajes hasta que se corte la conexion."""
    async with websockets.connect(cliente.url) as conexion:
        print("Conectado. Esperando desafios (Ctrl+C para salir).")
        if oponente:
            await cliente.desafiar(conexion, oponente)
        async for crudo in conexion:
            await cliente.recibir(conexion, crudo)


def main():
    """Arranca el bot desde la linea de comandos."""
    try:
        cliente, oponente = crear_cliente()
    except ValueError as error:
        sys.exit(str(error))
    print("Conectando al servidor...")
    try:
        asyncio.run(escuchar(cliente, oponente))
    except KeyboardInterrupt:
        cliente.logger.cerrar_todo()
        print("\nBot detenido.")


if __name__ == "__main__":
    main()
