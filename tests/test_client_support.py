"""Tests del registro de partidas y de la linea de comandos."""

import json
import os
import tempfile
import unittest

from snake_bot.cli import (construir_parser, crear_cliente, resolver_token)
from snake_bot.logger import ENTRADA, SALIDA, MatchLogger


class TestMatchLogger(unittest.TestCase):
    """Escritura de los archivos de partida."""

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.logger = MatchLogger(carpeta=self.carpeta.name)

    def tearDown(self):
        self.logger.cerrar_todo()
        self.carpeta.cleanup()

    def _leer(self, game_id):
        with open(self.logger.ruta(game_id), encoding="utf-8") as archivo:
            return archivo.read()

    def test_la_ruta_usa_el_id_de_partida(self):
        self.assertTrue(self.logger.ruta("g_1").endswith("game_g_1.log"))

    def test_escribe_lo_que_llega(self):
        self.logger.registrar("g_1", ENTRADA, {"event": "your_turn"})
        self.assertTrue(self._leer("g_1").startswith("< "))

    def test_escribe_lo_que_sale(self):
        self.logger.registrar("g_1", SALIDA, {"action": "move"})
        self.assertTrue(self._leer("g_1").startswith("> "))

    def test_guarda_json_valido(self):
        self.logger.registrar("g_1", SALIDA, {"action": "move", "data": {}})
        linea = self._leer("g_1").strip()
        self.assertEqual(json.loads(linea[2:])["action"], "move")

    def test_acumula_varias_lineas(self):
        self.logger.registrar("g_1", ENTRADA, {"n": 1})
        self.logger.registrar("g_1", SALIDA, {"n": 2})
        self.assertEqual(len(self._leer("g_1").strip().split("\n")), 2)

    def test_separa_las_partidas(self):
        self.logger.registrar("g_1", ENTRADA, {"n": 1})
        self.logger.registrar("g_2", ENTRADA, {"n": 2})
        self.assertTrue(os.path.exists(self.logger.ruta("g_2")))

    def test_sin_game_id_no_escribe(self):
        self.logger.registrar(None, ENTRADA, {"n": 1})
        self.assertEqual(os.listdir(self.carpeta.name), [])

    def test_cerrar_una_partida_inexistente_no_rompe(self):
        self.logger.cerrar("no-existe")

    def test_cerrar_todo_libera_los_archivos(self):
        self.logger.registrar("g_1", ENTRADA, {"n": 1})
        self.logger.cerrar_todo()
        self.assertEqual(self.logger._abiertos, {})


class TestLoggerDeshabilitado(unittest.TestCase):
    """Modo silencioso, usado en los tests del cliente."""

    def test_no_escribe_nada(self):
        with tempfile.TemporaryDirectory() as carpeta:
            logger = MatchLogger(carpeta=carpeta, habilitado=False)
            logger.registrar("g_1", ENTRADA, {"n": 1})
            self.assertEqual(os.listdir(carpeta), [])


class TestParser(unittest.TestCase):
    """Lectura de los argumentos."""

    def test_toma_el_token_posicional(self):
        argumentos = construir_parser().parse_args(["abc123"])
        self.assertEqual(argumentos.token, "abc123")

    def test_sin_argumentos_el_token_es_nulo(self):
        self.assertIsNone(construir_parser().parse_args([]).token)

    def test_lee_el_oponente(self):
        argumentos = construir_parser().parse_args(["t", "--challenge", "ana"])
        self.assertEqual(argumentos.oponente, "ana")


class TestResolverToken(unittest.TestCase):
    """De donde sale el token."""

    def test_prioriza_el_argumento(self):
        argumentos = construir_parser().parse_args(["del-argumento"])
        token = resolver_token(argumentos, {"BOT_TOKEN": "del-entorno"})
        self.assertEqual(token, "del-argumento")

    def test_usa_la_variable_de_entorno(self):
        argumentos = construir_parser().parse_args([])
        token = resolver_token(argumentos, {"BOT_TOKEN": "del-entorno"})
        self.assertEqual(token, "del-entorno")

    def test_sin_ninguno_devuelve_none(self):
        argumentos = construir_parser().parse_args([])
        self.assertIsNone(resolver_token(argumentos, {}))

    def test_consulta_el_entorno_real_por_defecto(self):
        argumentos = construir_parser().parse_args([])
        resolver_token(argumentos)


class TestCrearCliente(unittest.TestCase):
    """Construccion del cliente desde la linea de comandos."""

    def test_devuelve_cliente_y_oponente(self):
        cliente, oponente = crear_cliente(["mi-token", "--challenge", "ana"], {})
        self.assertEqual(cliente.token, "mi-token")
        self.assertEqual(oponente, "ana")

    def test_sin_oponente_devuelve_none(self):
        _, oponente = crear_cliente(["mi-token"], {})
        self.assertIsNone(oponente)

    def test_token_desde_el_entorno(self):
        cliente, _ = crear_cliente([], {"BOT_TOKEN": "del-entorno"})
        self.assertEqual(cliente.token, "del-entorno")

    def test_sin_token_avisa(self):
        with self.assertRaises(ValueError):
            crear_cliente([], {})


if __name__ == "__main__":
    unittest.main()
