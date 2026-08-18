"""Tests de la clase Move y de los helpers de direcciones."""

import unittest

from snake_bot.moves import DIRECCIONES, Move, Seguridad, celda_destino

BASE = {
    "espacio": 100,
    "espacio_pesimista": 100,
    "territorio": 100,
    "distancia_comida": 3,
    "libertad": 3,
    "amenazado": False,
    "come": False,
    "alcanzo_cola": True,
    "largo_futuro": 5,
}


def move(**cambios):
    """Crea un Move comodo con las metricas de base y los cambios pedidos."""
    return Move("up", (0, 0), {**BASE, **cambios})


class TestCeldaDestino(unittest.TestCase):
    """Traduccion de direccion a coordenadas."""

    def test_up_resta_una_fila(self):
        self.assertEqual(celda_destino((5, 5), "up"), (4, 5))

    def test_down_suma_una_fila(self):
        self.assertEqual(celda_destino((5, 5), "down"), (6, 5))

    def test_left_resta_una_columna(self):
        self.assertEqual(celda_destino((5, 5), "left"), (5, 4))

    def test_right_suma_una_columna(self):
        self.assertEqual(celda_destino((5, 5), "right"), (5, 6))

    def test_hay_cuatro_direcciones(self):
        self.assertEqual(len(DIRECCIONES), 4)


class TestMoveAtributos(unittest.TestCase):
    """Acceso a las metricas."""

    def test_expone_las_metricas_como_atributos(self):
        self.assertEqual(move().espacio, 100)
        self.assertTrue(move().alcanzo_cola)

    def test_metrica_inexistente_da_atributeerror(self):
        with self.assertRaises(AttributeError):
            move().inventada

    def test_guarda_direccion_y_celda(self):
        candidato = Move("left", (2, 3), BASE)
        self.assertEqual(candidato.direccion, "left")
        self.assertEqual(candidato.celda, (2, 3))

    def test_repr_menciona_la_direccion(self):
        self.assertIn("up", repr(move()))


class TestUmbral(unittest.TestCase):
    """Espacio minimo exigido."""

    def test_suma_el_margen_al_largo(self):
        self.assertEqual(move(largo_futuro=5).umbral(2), 7)

    def test_margen_cero(self):
        self.assertEqual(move(largo_futuro=5).umbral(0), 5)


class TestNivelSeguridad(unittest.TestCase):
    """Clasificacion en comodo, justo y peligroso."""

    def test_todo_bien_es_comodo(self):
        self.assertEqual(move().nivel(2), Seguridad.COMODO)

    def test_sin_cola_baja_a_justo(self):
        candidato = move(alcanzo_cola=False)
        self.assertEqual(candidato.nivel(2), Seguridad.JUSTO)

    def test_poco_territorio_baja_a_justo(self):
        candidato = move(territorio=1)
        self.assertEqual(candidato.nivel(2), Seguridad.JUSTO)

    def test_sin_espacio_es_peligroso(self):
        candidato = move(espacio=2)
        self.assertEqual(candidato.nivel(2), Seguridad.PELIGROSO)

    def test_sin_cola_ni_pesimista_es_peligroso(self):
        candidato = move(alcanzo_cola=False, espacio_pesimista=1)
        self.assertEqual(candidato.nivel(2), Seguridad.PELIGROSO)

    def test_espacio_justo_en_el_limite_alcanza(self):
        # largo 5 + margen 2 = 7, tener exactamente 7 es suficiente
        candidato = move(espacio=7, espacio_pesimista=7, territorio=7)
        self.assertEqual(candidato.nivel(2), Seguridad.COMODO)

    def test_una_celda_menos_ya_no_alcanza(self):
        candidato = move(espacio=6, espacio_pesimista=6, territorio=6)
        self.assertNotEqual(candidato.nivel(2), Seguridad.COMODO)

    def test_al_comer_sube_el_umbral(self):
        candidato = move(espacio=7, espacio_pesimista=7, territorio=7,
                         largo_futuro=6, come=True)
        self.assertNotEqual(candidato.nivel(2), Seguridad.COMODO)


if __name__ == "__main__":
    unittest.main()
