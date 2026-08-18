"""Tests del cliente websocket.

La conexion real se reemplaza por :class:`ConexionFalsa`, que guarda lo que
el bot manda en vez de enviarlo por la red. Asi se puede verificar todo el
protocolo sin servidor.
"""

import asyncio
import json
import unittest

from snake_bot.client import SnakeClient
from snake_bot.logger import MatchLogger

TABLERO = "\n".join([
    "|       |",
    "| aaA   |",
    "|    *  |",
    "|       |",
    "|   Bbb |",
    "|       |",
    "|       |",
])


class ConexionFalsa:
    """Reemplaza al websocket: en vez de enviar, guarda."""

    def __init__(self):
        self.enviados = []

    async def send(self, crudo):
        """Guarda el mensaje que el bot queria mandar."""
        self.enviados.append(json.loads(crudo))

    @property
    def acciones(self):
        """Nombres de las acciones enviadas, en orden."""
        return [mensaje["action"] for mensaje in self.enviados]


def correr(corrutina):
    """Ejecuta una corrutina en los tests."""
    return asyncio.run(corrutina)


def cliente():
    """Cliente con el log desactivado, para no escribir archivos."""
    return SnakeClient("token-de-prueba", logger=MatchLogger(habilitado=False))


def evento_turno(**extra):
    """Arma un evento your_turn como el del servidor."""
    datos = {
        "board": TABLERO,
        "side": "A",
        "game_id": "g_1",
        "turn_token": "t_1",
        "remaining_moves": 200,
    }
    datos.update(extra)
    return {"event": "your_turn", "data": datos}


class TestConfiguracion(unittest.TestCase):
    """Armado del cliente."""

    def test_url_incluye_el_token(self):
        self.assertIn("token=token-de-prueba", cliente().url)

    def test_url_usa_el_servidor_por_defecto(self):
        self.assertTrue(cliente().url.startswith("wss://"))

    def test_servidor_configurable(self):
        bot = SnakeClient("t", servidor="wss://otro/ws")
        self.assertEqual(bot.url, "wss://otro/ws?token=t")

    def test_trae_estrategia_por_defecto(self):
        self.assertIsNotNone(cliente().estrategia)


class TestDesafios(unittest.TestCase):
    """Aceptar y enviar desafios."""

    def setUp(self):
        self.bot = cliente()
        self.conexion = ConexionFalsa()

    def test_acepta_el_desafio_recibido(self):
        evento = {"event": "challenge",
                  "data": {"opponent": "ana", "challenge_id": "c_9"}}
        correr(self.bot.manejar(self.conexion, evento))
        self.assertEqual(self.conexion.acciones, ["accept_challenge"])

    def test_devuelve_el_challenge_id(self):
        evento = {"event": "challenge", "data": {"challenge_id": "c_9"}}
        correr(self.bot.manejar(self.conexion, evento))
        self.assertEqual(self.conexion.enviados[0]["data"]["challenge_id"], "c_9")

    def test_puede_desafiar_a_otro(self):
        correr(self.bot.desafiar(self.conexion, "beto@x.com"))
        enviado = self.conexion.enviados[0]
        self.assertEqual(enviado["action"], "challenge")
        self.assertEqual(enviado["data"]["opponent"], "beto@x.com")
        self.assertEqual(enviado["data"]["game"], "snake")

    def test_puede_pedir_la_lista(self):
        correr(self.bot.listar_usuarios(self.conexion))
        self.assertEqual(self.conexion.acciones, ["list_users"])


class TestTurno(unittest.TestCase):
    """Respuesta a your_turn."""

    def setUp(self):
        self.bot = cliente()
        self.conexion = ConexionFalsa()
        correr(self.bot.manejar(self.conexion, evento_turno()))
        self.enviado = self.conexion.enviados[0]

    def test_responde_con_move(self):
        self.assertEqual(self.enviado["action"], "move")

    def test_devuelve_una_direccion_valida(self):
        self.assertIn(self.enviado["data"]["direction"],
                      ("up", "down", "left", "right"))

    def test_repite_el_turn_token(self):
        self.assertEqual(self.enviado["data"]["turn_token"], "t_1")

    def test_repite_el_game_id(self):
        self.assertEqual(self.enviado["data"]["game_id"], "g_1")

    def test_cuenta_los_turnos(self):
        self.assertEqual(self.bot.turnos, 1)


class TestEventosVarios(unittest.TestCase):
    """list_users, game_over, error y eventos desconocidos."""

    def setUp(self):
        self.bot = cliente()
        self.conexion = ConexionFalsa()

    def test_guarda_los_usuarios_conectados(self):
        evento = {"event": "list_users", "data": {"users": ["ana", "beto"]}}
        correr(self.bot.manejar(self.conexion, evento))
        self.assertEqual(self.bot.usuarios, ["ana", "beto"])

    def test_game_over_guarda_el_resultado(self):
        evento = {"event": "game_over",
                  "data": {"winner": "yo", "game_id": "g_1"}}
        correr(self.bot.manejar(self.conexion, evento))
        self.assertEqual(self.bot.ultimo_resultado["winner"], "yo")

    def test_game_over_reinicia_el_contador(self):
        correr(self.bot.manejar(self.conexion, evento_turno()))
        correr(self.bot.manejar(self.conexion,
                                {"event": "game_over", "data": {}}))
        self.assertEqual(self.bot.turnos, 0)

    def test_error_del_servidor_se_guarda(self):
        evento = {"event": "error", "data": {"Error": "token invalido"}}
        correr(self.bot.manejar(self.conexion, evento))
        self.assertEqual(self.bot.errores["Error"], "token invalido")

    def test_evento_desconocido_no_rompe(self):
        atendido = correr(self.bot.manejar(self.conexion, {"event": "raro"}))
        self.assertFalse(atendido)
        self.assertEqual(self.conexion.enviados, [])

    def test_evento_sin_data(self):
        atendido = correr(self.bot.manejar(self.conexion,
                                           {"event": "list_users"}))
        self.assertTrue(atendido)


class TestRecepcion(unittest.TestCase):
    """Conversion del texto crudo que llega por el socket."""

    def setUp(self):
        self.bot = cliente()
        self.conexion = ConexionFalsa()

    def test_procesa_json_valido(self):
        crudo = json.dumps(evento_turno())
        self.assertTrue(correr(self.bot.recibir(self.conexion, crudo)))

    def test_texto_invalido_se_ignora(self):
        self.assertFalse(correr(self.bot.recibir(self.conexion, "no soy json")))

    def test_valor_nulo_se_ignora(self):
        self.assertFalse(correr(self.bot.recibir(self.conexion, None)))

    def test_una_partida_completa(self):
        mensajes = [
            {"event": "list_users", "data": {"users": ["ana"]}},
            {"event": "challenge", "data": {"challenge_id": "c_1"}},
            evento_turno(),
            evento_turno(turn_token="t_2"),
            {"event": "game_over", "data": {"winner": "yo", "game_id": "g_1"}},
        ]
        for mensaje in mensajes:
            correr(self.bot.recibir(self.conexion, json.dumps(mensaje)))
        self.assertEqual(self.conexion.acciones,
                         ["accept_challenge", "move", "move"])


if __name__ == "__main__":
    unittest.main()
