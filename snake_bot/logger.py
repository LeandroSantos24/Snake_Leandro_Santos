"""Registro de partidas.

Cada partida se guarda en su propio archivo ``game_<id>.log`` con el mismo
formato que usan los clientes de ejemplo: ``<`` para lo que llega del
servidor y ``>`` para lo que manda el bot.

Ese registro es lo que permite reconstruir una derrota despues del hecho.
Los dos unicos choques del bot se diagnosticaron asi: volviendo a pasar los
tableros guardados por la estrategia y mirando en que turno se metio en la
trampa.
"""

import json
import os

ENTRADA = "<"
SALIDA = ">"


class MatchLogger:
    """Escribe un archivo de log por partida."""

    def __init__(self, carpeta=".", habilitado=True):
        """Prepara el registro.

        Args:
            carpeta: donde dejar los archivos.
            habilitado: si es False no se escribe nada (util en los tests).
        """
        self.carpeta = carpeta
        self.habilitado = habilitado
        self._abiertos = {}

    def ruta(self, game_id):
        """Devuelve la ruta del archivo de una partida."""
        return os.path.join(self.carpeta, "game_{}.log".format(game_id))

    def _archivo(self, game_id):
        """Abre el archivo de la partida, reutilizando el que ya este abierto."""
        if game_id not in self._abiertos:
            self._abiertos[game_id] = open(self.ruta(game_id), "a",
                                           encoding="utf-8")
        return self._abiertos[game_id]

    def registrar(self, game_id, direccion, mensaje):
        """Anota un mensaje en el log de la partida.

        Args:
            game_id: identificador de la partida; si es falso no se registra.
            direccion: ``"<"`` si llega del servidor, ``">"`` si sale del bot.
            mensaje: diccionario que se guarda como JSON.
        """
        if not self.habilitado or not game_id:
            return
        archivo = self._archivo(game_id)
        archivo.write("{} {}\n".format(direccion, json.dumps(mensaje)))
        archivo.flush()

    def cerrar(self, game_id):
        """Cierra el archivo de una partida terminada."""
        archivo = self._abiertos.pop(game_id, None)
        if archivo:
            archivo.close()

    def cerrar_todo(self):
        """Cierra todos los archivos que hayan quedado abiertos."""
        for game_id in list(self._abiertos):
            self.cerrar(game_id)
