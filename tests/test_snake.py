"""Tests de la clase Snake y del helper vecinos()."""

import unittest

from snake_bot.snake import Snake, vecinos


class TestVecinos(unittest.TestCase):
    """Celdas adyacentes."""

    def test_devuelve_cuatro(self):
        self.assertEqual(len(vecinos((5, 5))), 4)

    def test_son_las_esperadas(self):
        self.assertEqual(
            set(vecinos((2, 3))),
            {(1, 3), (3, 3), (2, 2), (2, 4)},
        )

    def test_admite_coordenadas_negativas(self):
        self.assertIn((-1, 0), vecinos((0, 0)))


class TestSnakeBasico(unittest.TestCase):
    """Propiedades elementales."""

    def setUp(self):
        # cabeza en (0,2), cuerpo hacia la izquierda
        self.snake = Snake((0, 2), {(0, 1), (0, 0)})

    def test_existe(self):
        self.assertTrue(self.snake.existe)

    def test_largo_cuenta_la_cabeza(self):
        self.assertEqual(self.snake.largo, 3)

    def test_celdas_incluye_la_cabeza(self):
        self.assertEqual(self.snake.celdas, {(0, 0), (0, 1), (0, 2)})

    def test_indices_desde_la_cabeza(self):
        self.assertEqual(self.snake.indices, {(0, 2): 0, (0, 1): 1, (0, 0): 2})

    def test_cola_es_la_celda_mas_lejana(self):
        self.assertEqual(self.snake.cola, (0, 0))


class TestSnakeCasosBorde(unittest.TestCase):
    """Situaciones raras que no deben romper el bot."""

    def test_sin_cabeza(self):
        snake = Snake(None, {(0, 0)})
        self.assertFalse(snake.existe)
        self.assertEqual(snake.largo, 1)
        self.assertEqual(snake.indices, {})
        self.assertIsNone(snake.cola)
        self.assertEqual(snake.celdas, {(0, 0)})

    def test_solo_cabeza_no_tiene_cola(self):
        snake = Snake((3, 3), set())
        self.assertEqual(snake.largo, 1)
        self.assertIsNone(snake.cola)

    def test_cuerpo_desconectado_se_ignora(self):
        # una celda suelta lejos de la cabeza no forma parte del recorrido
        snake = Snake((0, 0), {(0, 1), (9, 9)})
        self.assertNotIn((9, 9), snake.indices)
        self.assertEqual(snake.cola, (0, 1))


class TestLiberacion(unittest.TestCase):
    """Calendario de liberacion de celdas."""

    def setUp(self):
        self.snake = Snake((0, 2), {(0, 1), (0, 0)})

    def test_la_cola_se_libera_primero(self):
        calendario = self.snake.liberacion()
        self.assertEqual(calendario[(0, 0)], 1)
        self.assertEqual(calendario[(0, 1)], 2)
        self.assertEqual(calendario[(0, 2)], 3)

    def test_al_comer_todo_se_corre_un_turno(self):
        calendario = self.snake.liberacion(crece=True)
        self.assertEqual(calendario[(0, 0)], 2)
        self.assertEqual(calendario[(0, 2)], 4)

    def test_serpiente_ausente_no_libera_nada(self):
        self.assertEqual(Snake(None, set()).liberacion(), {})


if __name__ == "__main__":
    unittest.main()
