"""Tests de FloodFill, PathFinder y Territory."""

import unittest

from snake_bot.analysis import FloodFill, PathFinder, Territory
from snake_bot.board import Board

# tablero de 5x5 totalmente vacio
VACIO = Board([" " * 5 for _ in range(5)])

# pasillo: la fila del medio esta tapada salvo una puerta en la columna 4
#  .....
#  .....
#  ####.
#  .....
#  .....
MURO = {(2, 0), (2, 1), (2, 2), (2, 3)}


class TestFloodFillBasico(unittest.TestCase):
    """Recorrido sin serpientes en el medio."""

    def test_tablero_vacio_alcanza_todo(self):
        relleno = FloodFill(VACIO)
        self.assertEqual(relleno.espacio((0, 0)), 25)

    def test_incluye_la_celda_inicial(self):
        self.assertIn((2, 2), FloodFill(VACIO).alcanzables((2, 2)))

    def test_inicio_fuera_del_tablero(self):
        self.assertEqual(FloodFill(VACIO).alcanzables((9, 9)), set())

    def test_board_vacio_no_alcanza_nada(self):
        self.assertEqual(FloodFill(Board([])).espacio((0, 0)), 0)


class TestFloodFillBloqueos(unittest.TestCase):
    """Celdas prohibidas sin importar el tiempo."""

    def test_muro_permanente_reduce_el_espacio(self):
        # con el muro bloqueado queda la puerta en (2,4), asi que igual pasa
        relleno = FloodFill(VACIO)
        self.assertEqual(relleno.espacio((0, 0), bloqueadas=MURO), 21)

    def test_muro_completo_aisla_la_mitad(self):
        completo = MURO | {(2, 4)}
        relleno = FloodFill(VACIO)
        self.assertEqual(relleno.espacio((0, 0), bloqueadas=completo), 10)

    def test_encierro_total(self):
        jaula = {(0, 1), (1, 0)}
        self.assertEqual(FloodFill(VACIO).espacio((0, 0), bloqueadas=jaula), 1)


class TestFloodFillTemporal(unittest.TestCase):
    """La parte que distingue esta clase de un flood fill comun."""

    def test_celda_que_se_libera_pronto_se_atraviesa(self):
        # el muro se libera en 1 turno: cuando llego ya no esta
        libre_en = {celda: 1 for celda in MURO | {(2, 4)}}
        relleno = FloodFill(VACIO, libre_en)
        self.assertEqual(relleno.espacio((0, 0)), 25)

    def test_celda_que_tarda_mucho_corta_el_paso(self):
        # el muro tarda 50 turnos: nunca llego a cruzarlo
        libre_en = {celda: 50 for celda in MURO | {(2, 4)}}
        relleno = FloodFill(VACIO, libre_en)
        self.assertEqual(relleno.espacio((0, 0)), 10)

    def test_el_tiempo_depende_de_la_distancia(self):
        # la puerta se libera en 4 turnos; desde (0,4) llego en 2 -> no paso
        libre_en = {celda: 99 for celda in MURO}
        libre_en[(2, 4)] = 4
        cerca = FloodFill(VACIO, libre_en).espacio((0, 4))
        # desde (0,0) tardo mas, asi que llego cuando ya se libero
        lejos = FloodFill(VACIO, libre_en).espacio((0, 0))
        self.assertLess(cerca, lejos)

    def test_sin_calendario_todo_esta_libre(self):
        self.assertEqual(FloodFill(VACIO, None).espacio((0, 0)), 25)


class TestPathFinder(unittest.TestCase):
    """Distancias en cantidad de movimientos."""

    def setUp(self):
        self.buscador = PathFinder(VACIO)

    def test_distancia_a_si_mismo_es_cero(self):
        self.assertEqual(self.buscador.distancias((0, 0))[(0, 0)], 0)

    def test_distancia_manhattan_en_tablero_vacio(self):
        self.assertEqual(self.buscador.distancias((0, 0))[(2, 3)], 5)

    def test_inicio_invalido_devuelve_vacio(self):
        self.assertEqual(self.buscador.distancias((9, 9)), {})
        self.assertEqual(self.buscador.distancias(None), {})

    def test_rodea_los_obstaculos(self):
        distancias = self.buscador.distancias((0, 0), bloqueadas=MURO)
        # para llegar abajo hay que dar la vuelta por la puerta (2,4)
        self.assertEqual(distancias[(4, 0)], 12)

    def test_zona_aislada_no_aparece(self):
        completo = MURO | {(2, 4)}
        distancias = self.buscador.distancias((0, 0), bloqueadas=completo)
        self.assertNotIn((4, 0), distancias)


class TestDistanciaA(unittest.TestCase):
    """Busqueda del objetivo mas cercano."""

    def setUp(self):
        self.buscador = PathFinder(VACIO)

    def test_elige_el_objetivo_mas_cercano(self):
        distancia = self.buscador.distancia_a((0, 0), {(0, 4), (0, 1)})
        self.assertEqual(distancia, 1)

    def test_sin_objetivos_devuelve_none(self):
        self.assertIsNone(self.buscador.distancia_a((0, 0), set()))

    def test_descarta_objetivos_nulos(self):
        self.assertIsNone(self.buscador.distancia_a((0, 0), {None}))

    def test_objetivo_inalcanzable_devuelve_none(self):
        completo = MURO | {(2, 4)}
        self.assertIsNone(
            self.buscador.distancia_a((0, 0), {(4, 4)}, bloqueadas=completo)
        )

    def test_el_objetivo_nunca_esta_bloqueado(self):
        # (0,1) figura como bloqueada pero es el objetivo: igual se alcanza
        distancia = self.buscador.distancia_a((0, 0), {(0, 1)}, bloqueadas={(0, 1)})
        self.assertEqual(distancia, 1)


class TestTerritory(unittest.TestCase):
    """Reparto del tablero entre las dos serpientes."""

    def test_gano_las_celdas_donde_llego_antes(self):
        territorio = Territory({(0, 0): 1, (0, 1): 5}, {(0, 0): 3, (0, 1): 2})
        self.assertEqual(territorio.celdas_propias(), {(0, 0)})
        self.assertEqual(territorio.contar(), 1)

    def test_el_empate_no_cuenta_como_mio(self):
        territorio = Territory({(0, 0): 2}, {(0, 0): 2})
        self.assertEqual(territorio.contar(), 0)

    def test_celda_inalcanzable_para_el_rival_es_mia(self):
        territorio = Territory({(3, 3): 9}, {})
        self.assertEqual(territorio.contar(), 1)

    def test_sin_celdas_propias_no_hay_territorio(self):
        self.assertEqual(Territory({}, {(0, 0): 1}).contar(), 0)


if __name__ == "__main__":
    unittest.main()
