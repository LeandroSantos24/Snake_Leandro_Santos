"""Tests de la clase GameState."""

import unittest

from snake_bot.board import Board
from snake_bot.game_state import GameState, vecinos_validos

TABLERO = "\n".join([
    "|       |",
    "| aaA   |",
    "|    *  |",
    "|  Bbb  |",
])


def turno(board=TABLERO, side="A", remaining=250):
    """Arma un turn_data como el que manda el servidor."""
    return {"board": board, "side": side, "remaining_moves": remaining}


class TestConstruccion(unittest.TestCase):
    """Lectura del turn_data."""

    def setUp(self):
        self.estado = GameState.desde_turno(turno())

    def test_identifica_mi_cabeza(self):
        self.assertEqual(self.estado.yo.cabeza, (1, 3))

    def test_identifica_mi_cuerpo(self):
        self.assertEqual(self.estado.yo.cuerpo, {(1, 1), (1, 2)})

    def test_identifica_al_rival(self):
        self.assertEqual(self.estado.rival.cabeza, (3, 2))
        self.assertEqual(self.estado.rival.cuerpo, {(3, 3), (3, 4)})

    def test_identifica_la_comida(self):
        self.assertEqual(self.estado.comida, {(2, 4)})

    def test_guarda_movimientos_restantes(self):
        self.assertEqual(self.estado.remaining_moves, 250)


class TestLados(unittest.TestCase):
    """Manejo del campo side."""

    def test_lado_b_invierte_los_roles(self):
        estado = GameState.desde_turno(turno(side="B"))
        self.assertEqual(estado.yo.cabeza, (3, 2))
        self.assertEqual(estado.rival.cabeza, (1, 3))

    def test_lado_en_minuscula(self):
        self.assertEqual(GameState.desde_turno(turno(side="b")).side, "B")

    def test_lado_con_espacios(self):
        self.assertEqual(GameState.desde_turno(turno(side=" A ")).side, "A")

    def test_lado_ausente_usa_a(self):
        estado = GameState.desde_turno({"board": TABLERO})
        self.assertEqual(estado.side, "A")

    def test_lado_invalido_usa_a(self):
        self.assertEqual(GameState.desde_turno(turno(side="Z")).side, "A")


class TestDatosAnidados(unittest.TestCase):
    """Compatibilidad con turn_data anidado."""

    def test_lee_los_datos_de_adentro(self):
        estado = GameState.desde_turno({"turn_data": {"board": TABLERO, "side": "B"}})
        self.assertEqual(estado.side, "B")

    def test_los_datos_de_afuera_tienen_prioridad(self):
        estado = GameState.desde_turno(
            {"turn_data": {"board": TABLERO, "side": "B"}, "side": "A"}
        )
        self.assertEqual(estado.side, "A")

    def test_turn_data_no_dict_se_ignora(self):
        estado = GameState.desde_turno({"board": TABLERO, "turn_data": "x"})
        self.assertEqual(estado.side, "A")


class TestConsultas(unittest.TestCase):
    """Derivados del estado."""

    def setUp(self):
        self.estado = GameState.desde_turno(turno())

    def test_ocupadas_junta_las_dos_serpientes(self):
        self.assertEqual(len(self.estado.ocupadas), 6)

    def test_amenazas_rodean_la_cabeza_rival(self):
        self.assertEqual(self.estado.amenazas, {(2, 2), (3, 1), (3, 3)})

    def test_sin_rival_no_hay_amenazas(self):
        estado = GameState.desde_turno(turno(board="|A  |\n|a  |"))
        self.assertEqual(estado.amenazas, set())

    def test_liberacion_incluye_ambas_serpientes(self):
        calendario = self.estado.liberacion()
        self.assertIn((1, 1), calendario)
        self.assertIn((3, 4), calendario)

    def test_liberacion_al_comer_corre_mis_celdas(self):
        normal = self.estado.liberacion()
        comiendo = self.estado.liberacion(crezco=True)
        self.assertEqual(comiendo[(1, 1)], normal[(1, 1)] + 1)


class TestVecinosValidos(unittest.TestCase):
    """Helper de vecinos limitados al tablero."""

    def test_en_el_medio_hay_cuatro(self):
        board = Board.desde_texto(TABLERO)
        self.assertEqual(len(vecinos_validos(board, (1, 3))), 4)

    def test_en_la_esquina_hay_dos(self):
        board = Board.desde_texto(TABLERO)
        self.assertEqual(vecinos_validos(board, (0, 0)), {(0, 1), (1, 0)})


if __name__ == "__main__":
    unittest.main()
