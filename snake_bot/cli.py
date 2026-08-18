"""Interfaz de linea de comandos.

Separada del cliente para poder probar el parseo de argumentos sin abrir
ninguna conexion.

Uso::

    python run.py <TOKEN>
    BOT_TOKEN=<TOKEN> python run.py
    python run.py <TOKEN> --challenge rival@mail.com
"""

import argparse
import os

from .client import SnakeClient

VARIABLE_TOKEN = "BOT_TOKEN"


def construir_parser():
    """Arma el parser de argumentos de la linea de comandos."""
    parser = argparse.ArgumentParser(
        description="Bot de Snake para la plataforma CodeChallenge")
    parser.add_argument("token", nargs="?", default=None,
                        help="token del bot; tambien se puede usar BOT_TOKEN")
    parser.add_argument("--challenge", dest="oponente", default=None,
                        help="desafiar a este bot apenas se conecte")
    return parser


def resolver_token(argumentos, entorno=None):
    """Decide que token usar.

    Prioriza el argumento de la linea de comandos y cae en la variable de
    entorno, que es la forma recomendada: asi el token no queda en el
    historial de la terminal ni se puede subir al repositorio por error.

    Args:
        argumentos: resultado de ``parse_args``.
        entorno: diccionario de variables de entorno; por defecto el real.

    Returns:
        str | None: el token, o None si no hay ninguno.
    """
    if argumentos.token:
        return argumentos.token
    variables = os.environ if entorno is None else entorno
    return variables.get(VARIABLE_TOKEN)


def crear_cliente(argv=None, entorno=None):
    """Construye el cliente a partir de los argumentos recibidos.

    Args:
        argv: lista de argumentos; por defecto los de la linea de comandos.
        entorno: variables de entorno a consultar.

    Returns:
        tuple: ``(cliente, oponente)``.

    Raises:
        ValueError: si no se pudo determinar el token.
    """
    argumentos = construir_parser().parse_args(argv)
    token = resolver_token(argumentos, entorno)
    if not token:
        raise ValueError(
            "Falta el token. Usalo asi: python run.py <TOKEN>, "
            "o exporta la variable BOT_TOKEN.")
    return SnakeClient(token), argumentos.oponente
