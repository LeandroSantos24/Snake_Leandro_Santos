"""Tests de la estrategia: puntaje, orden y eleccion final."""

import unittest

from snake_bot.game_state import GameState
from snake_bot.moves import Move
from snake_bot.strategy import Pesos, Strategy

TABLERO = "\n".join([
    "|       |",
    "| aaA   |",
    "|    *  |",
    "|       |",
    "|   Bbb |",
    "|       |",
    "|       |",
])

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


def move(direccion="up", **cambios):
    """Crea un Move con metricas de base."""
    return Move(direccion, (0, 0), {**BASE, **cambios})


def turno(board=TABLERO, side="A"):
    """Arma un turn_data como el del servidor."""
    return {"board": board, "side": side}


class TestPuntaje(unittest.TestCase):
    """Funcion de puntaje."""

    def setUp(self):
        self.estrategia = Strategy()

    def test_mas_espacio_es_mejor(self):
        mucho = self.estrategia.puntaje(move(espacio=200, espacio_pesimista=200))
        poco = self.estrategia.puntaje(move(espacio=20, espacio_pesimista=20))
        self.assertGreater(mucho, poco)

    def test_mas_territorio_es_mejor(self):
        self.assertGreater(
            self.estrategia.puntaje(move(territorio=150)),
            self.estrategia.puntaje(move(territorio=50)),
        )

    def test_comida_cerca_es_mejor(self):
        self.assertGreater(
            self.estrategia.puntaje(move(distancia_comida=1)),
            self.estrategia.puntaje(move(distancia_comida=8)),
        )

    def test_la_amenaza_resta(self):
        self.assertLess(
            self.estrategia.puntaje(move(amenazado=True)),
            self.estrategia.puntaje(move(amenazado=False)),
        )

    def test_mas_libertad_es_mejor(self):
        self.assertGreater(
            self.estrategia.puntaje(move(libertad=4)),
            self.estrategia.puntaje(move(libertad=1)),
        )

    def test_la_distancia_tiene_tope(self):
        # pasado el tope, alejarse mas no cambia el puntaje
        lejos = self.estrategia.puntaje(move(distancia_comida=20))
        lejisimos = self.estrategia.puntaje(move(distancia_comida=99))
        self.assertEqual(lejos, lejisimos)


class TestOrden(unittest.TestCase):
    """La seguridad manda sobre el puntaje."""

    def setUp(self):
        self.estrategia = Strategy()

    def test_prefiere_lo_seguro_aunque_puntue_menos(self):
        seguro = move("up", distancia_comida=15)
        goloso = move("down", distancia_comida=0, espacio=4,
                      espacio_pesimista=4, territorio=4)
        orden = self.estrategia.ordenar([goloso, seguro])
        self.assertEqual(orden[0].direccion, "up")

    def test_entre_iguales_gana_el_puntaje(self):
        cerca = move("up", distancia_comida=1)
        lejos = move("down", distancia_comida=9)
        orden = self.estrategia.ordenar([lejos, cerca])
        self.assertEqual(orden[0].direccion, "up")

    def test_ordenar_lista_vacia(self):
        self.assertEqual(self.estrategia.ordenar([]), [])


class TestEleccion(unittest.TestCase):
    """Decision sobre estados reales."""

    def setUp(self):
        self.estrategia = Strategy()

    def test_devuelve_una_direccion_valida(self):
        eleccion = self.estrategia.decidir(turno())
        self.assertIn(eleccion, ("up", "down", "left", "right"))

    def test_nunca_choca_contra_su_cuerpo(self):
        self.assertNotEqual(self.estrategia.decidir(turno()), "left")

    def test_va_por_la_comida_si_esta_al_lado(self):
        tablero = "\n".join(["|aA*    |"] + ["|       |"] * 4)
        self.assertEqual(self.estrategia.decidir(turno(board=tablero)), "right")

    def test_esquiva_la_pared(self):
        tablero = "\n".join(["|A      |"] + ["|       |"] * 4)
        self.assertIn(self.estrategia.decidir(turno(board=tablero)),
                      ("down", "right"))

    def test_evaluar_devuelve_movimientos_ordenados(self):
        movimientos = self.estrategia.evaluar(GameState.desde_turno(turno()))
        self.assertEqual(len(movimientos), 3)


class TestUltimoRecurso(unittest.TestCase):
    """Situaciones sin salida: igual hay que mandar una jugada valida."""

    def test_encerrado_devuelve_algo_valido(self):
        # cabeza rodeada por su propio cuerpo en las cuatro direcciones
        tablero = "| a |\n|aAa|\n| a |"
        eleccion = Strategy().decidir(turno(board=tablero))
        self.assertIn(eleccion, ("up", "down", "left", "right"))

    def test_tablero_de_una_celda(self):
        # todas las direcciones caen fuera del tablero
        self.assertEqual(Strategy().decidir(turno(board="|A|")), "up")

    def test_sin_serpiente_devuelve_el_valor_por_defecto(self):
        self.assertEqual(Strategy().decidir(turno(board="|   |\n|   |")), "up")

    def test_tablero_vacio_no_rompe(self):
        self.assertEqual(Strategy().decidir({"board": ""}), "up")


class TestPesosPersonalizados(unittest.TestCase):
    """La estrategia acepta otros coeficientes."""

    def test_se_puede_cambiar_el_margen(self):
        estrategia = Strategy(margen=0)
        self.assertEqual(estrategia.margen, 0)

    def test_margen_por_defecto_sale_de_los_pesos(self):
        self.assertEqual(Strategy().margen, Pesos.MARGEN_SEGURIDAD)

    def test_ignorar_la_comida_cambia_el_puntaje(self):
        class SinComida(Pesos):
            COMIDA = 0.0

        candidato = move(distancia_comida=10)
        self.assertGreater(
            Strategy(pesos=SinComida).puntaje(candidato),
            Strategy().puntaje(candidato),
        )


if __name__ == "__main__":
    unittest.main()
