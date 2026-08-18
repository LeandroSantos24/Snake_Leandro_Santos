"""Tests del evaluador de movimientos."""

import unittest

from snake_bot.evaluator import MoveEvaluator, celdas_vecinas_validas
from snake_bot.game_state import GameState

# 7x7, mi serpiente arriba a la izquierda, el rival abajo a la derecha
TABLERO = "\n".join([
    "|       |",
    "| aaA   |",
    "|    *  |",
    "|       |",
    "|   Bbb |",
    "|       |",
    "|       |",
])


def estado(board=TABLERO, side="A"):
    """Arma un GameState desde un tablero de texto."""
    return GameState.desde_turno({"board": board, "side": side})


class TestLegalidad(unittest.TestCase):
    """Direcciones que no llevan a un choque inmediato."""

    def setUp(self):
        self.evaluador = MoveEvaluator(estado())

    def test_no_puedo_volver_sobre_mi_cuerpo(self):
        self.assertNotIn("left", self.evaluador.direcciones_legales())

    def test_las_otras_tres_son_legales(self):
        self.assertEqual(
            set(self.evaluador.direcciones_legales()),
            {"up", "down", "right"},
        )

    def test_la_pared_no_es_legal(self):
        self.assertFalse(self.evaluador.es_legal((-1, 0)))

    def test_una_celda_libre_es_legal(self):
        self.assertTrue(self.evaluador.es_legal((0, 0)))

    def test_en_una_esquina_quedan_pocas_salidas(self):
        esquina = "\n".join(["|A      |"] + ["|       |"] * 6)
        evaluador = MoveEvaluator(estado(board=esquina))
        self.assertEqual(set(evaluador.direcciones_legales()), {"down", "right"})


class TestMetricas(unittest.TestCase):
    """Valores que calcula el evaluador."""

    def setUp(self):
        self.evaluador = MoveEvaluator(estado())

    def test_detecta_que_come(self):
        # la comida esta en (2,4); desde (1,3) bajar no llega, hay que ir a la derecha
        movimiento = self.evaluador.evaluar("down")
        self.assertFalse(movimiento.come)

    def test_espacio_positivo_en_tablero_abierto(self):
        self.assertGreater(self.evaluador.evaluar("up").espacio, 10)

    def test_pesimista_nunca_supera_al_optimista(self):
        movimiento = self.evaluador.evaluar("right")
        self.assertLessEqual(movimiento.espacio_pesimista, movimiento.espacio)

    def test_libertad_cuenta_salidas(self):
        self.assertGreaterEqual(self.evaluador.evaluar("up").libertad, 2)

    def test_largo_futuro_sin_comer(self):
        self.assertEqual(self.evaluador.evaluar("up").largo_futuro, 3)

    def test_evaluar_todos_devuelve_las_legales(self):
        self.assertEqual(len(self.evaluador.evaluar_todos()), 3)

    def test_sin_serpiente_no_hay_movimientos(self):
        vacio = estado(board="|   |\n|   |")
        self.assertEqual(MoveEvaluator(vacio).evaluar_todos(), [])


class TestComer(unittest.TestCase):
    """Deteccion de comida y su efecto en el largo."""

    def setUp(self):
        # cabeza en (0,1) con la comida justo a la derecha
        self.evaluador = MoveEvaluator(estado(board="|aA*  |\n|     |"))

    def test_marca_que_come(self):
        self.assertTrue(self.evaluador.evaluar("right").come)

    def test_al_comer_crece_el_largo_futuro(self):
        self.assertEqual(self.evaluador.evaluar("right").largo_futuro, 3)

    def test_comer_deja_la_distancia_en_cero(self):
        self.assertEqual(self.evaluador.evaluar("right").distancia_comida, 0)


class TestAmenazas(unittest.TestCase):
    """Celdas donde el rival puede llegar el proximo turno."""

    def test_marca_la_celda_amenazada(self):
        # mi cabeza en (0,1), la rival en (0,3): la celda (0,2) esta en disputa
        tablero = "|aA B |\n|     |\n|     |"
        evaluador = MoveEvaluator(estado(board=tablero))
        self.assertTrue(evaluador.evaluar("right").amenazado)

    def test_lejos_del_rival_no_hay_amenaza(self):
        evaluador = MoveEvaluator(estado())
        self.assertFalse(evaluador.evaluar("up").amenazado)


class TestSupervivencia(unittest.TestCase):
    """Comportamiento cuando no hay comida al alcance."""

    def test_sin_comida_usa_la_cola_como_destino(self):
        tablero = "\n".join(["| aaA   |"] + ["|       |"] * 4)
        evaluador = MoveEvaluator(estado(board=tablero))
        movimiento = evaluador.evaluar("down")
        self.assertLess(movimiento.distancia_comida, 20)

    def test_alcanzo_cola_es_verdadero_en_espacio_abierto(self):
        evaluador = MoveEvaluator(estado())
        self.assertTrue(evaluador.evaluar("up").alcanzo_cola)

    def test_serpiente_de_una_celda_no_tiene_cola(self):
        evaluador = MoveEvaluator(estado(board="|A    |\n|     |"))
        self.assertTrue(evaluador.evaluar("right").alcanzo_cola)


class TestHelper(unittest.TestCase):
    """Atajo publico de vecinos validos."""

    def test_devuelve_los_vecinos_del_tablero(self):
        board = estado().board
        self.assertEqual(len(celdas_vecinas_validas(board, (3, 3))), 4)


if __name__ == "__main__":
    unittest.main()
