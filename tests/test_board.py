"""Tests de la clase Board."""

import unittest

from snake_bot.board import Board

TABLERO = "\n".join([
    "|     |",
    "| aaA |",
    "|  *  |",
])


class TestConstruccion(unittest.TestCase):
    """Parseo del texto que manda el servidor."""

    def test_dimensiones(self):
        board = Board.desde_texto(TABLERO)
        self.assertEqual(board.rows, 3)
        self.assertEqual(board.cols, 5)

    def test_conserva_espacios_interiores(self):
        board = Board.desde_texto(TABLERO)
        self.assertEqual(board.simbolo((1, 0)), " ")
        self.assertEqual(board.simbolo((1, 1)), "a")

    def test_ignora_lineas_vacias(self):
        board = Board.desde_texto("\n|ab|\n\n|cd|\n")
        self.assertEqual(board.rows, 2)

    def test_texto_vacio_da_tablero_vacio(self):
        board = Board.desde_texto("")
        self.assertTrue(board.vacio)
        self.assertEqual(board.rows, 0)
        self.assertEqual(board.cols, 0)

    def test_texto_none_no_rompe(self):
        self.assertTrue(Board.desde_texto(None).vacio)

    def test_linea_sin_barras(self):
        board = Board.desde_texto("abc")
        self.assertEqual(board.simbolo((0, 0)), "a")

    def test_barra_sola_no_se_recorta(self):
        board = Board.desde_texto("a|b")
        self.assertEqual(board.cols, 3)

    def test_filas_desparejas_se_rellenan(self):
        board = Board([" a", " "])
        self.assertEqual(board.cols, 2)
        self.assertEqual(board.simbolo((1, 1)), " ")


class TestConsultas(unittest.TestCase):
    """Consultas por coordenadas."""

    def setUp(self):
        self.board = Board.desde_texto(TABLERO)

    def test_dentro_reconoce_limites(self):
        self.assertTrue(self.board.dentro((0, 0)))
        self.assertTrue(self.board.dentro((2, 4)))

    def test_dentro_rechaza_afuera(self):
        self.assertFalse(self.board.dentro((-1, 0)))
        self.assertFalse(self.board.dentro((3, 0)))
        self.assertFalse(self.board.dentro((0, 5)))

    def test_simbolo_afuera_es_none(self):
        self.assertIsNone(self.board.simbolo((9, 9)))

    def test_posiciones_de_comida(self):
        self.assertEqual(self.board.posiciones_de("*"), {(2, 2)})

    def test_posiciones_de_cuerpo(self):
        self.assertEqual(self.board.posiciones_de("a"), {(1, 1), (1, 2)})

    def test_posiciones_de_simbolo_ausente(self):
        self.assertEqual(self.board.posiciones_de("Z"), set())

    def test_celdas_recorre_todo(self):
        self.assertEqual(len(list(self.board.celdas())), 15)

    def test_str_reconstruye_el_formato(self):
        self.assertEqual(str(Board.desde_texto(TABLERO)), TABLERO)


if __name__ == "__main__":
    unittest.main()
