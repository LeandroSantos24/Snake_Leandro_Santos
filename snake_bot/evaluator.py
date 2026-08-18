"""Evaluacion de un movimiento candidato.

El evaluador toma el estado del turno y una direccion, y produce un
:class:`~snake_bot.moves.Move` con todas las metricas calculadas. Se separa
de la estrategia a proposito: aca se *mide*, en la estrategia se *decide*.

Las metricas son:

espacio
    celdas alcanzables a tiempo desde la celda destino.
espacio_pesimista
    lo mismo, pero suponiendo que el rival avanza y tapa una salida.
territorio
    celdas que alcanzo antes que el rival.
distancia_comida
    movimientos hasta la manzana mas cercana que este a mi alcance.
libertad
    salidas que tiene la celda destino.
"""

from .analysis import FloodFill, PathFinder, Territory
from .game_state import vecinos_validos
from .moves import Move, celda_destino
from .snake import vecinos

DISTANCIA_MAXIMA = 20


class MoveEvaluator:
    """Calcula las metricas de los movimientos posibles en un turno."""

    def __init__(self, estado):
        """Prepara las herramientas de analisis para este turno.

        Args:
            estado: instancia de :class:`~snake_bot.game_state.GameState`.
        """
        self.estado = estado
        self.buscador = PathFinder(estado.board)
        self.amenazas = estado.amenazas
        self.bloqueadas = estado.ocupadas
        self._distancias_rival = self._calcular_distancias_rival()

    def _calcular_distancias_rival(self):
        """Mide desde donde puede llegar el rival, para repartir el territorio."""
        libres = self.estado.ocupadas - {
            self.estado.rival.cabeza, self.estado.rival.cola}
        return self.buscador.distancias(self.estado.rival.cabeza, libres)

    def _sin_colas(self):
        """Celdas ocupadas sin contar las colas, que se van a mover igual."""
        return self.estado.ocupadas - {self.estado.yo.cola, self.estado.rival.cola}

    def es_legal(self, celda):
        """True si la celda esta en el tablero y no la ocupa ninguna serpiente."""
        return self.estado.board.dentro(celda) and celda not in self.bloqueadas

    def direcciones_legales(self):
        """Devuelve las direcciones que no llevan a un choque inmediato."""
        cabeza = self.estado.yo.cabeza
        return [nombre for nombre in ("up", "down", "left", "right")
                if self.es_legal(celda_destino(cabeza, nombre))]

    def _libertad(self, celda):
        """Cuenta las salidas disponibles desde una celda."""
        return sum(1 for vecino in vecinos(celda) if self.es_legal(vecino))

    def _espacios(self, celda, come):
        """Calcula el espacio optimista y el pesimista.

        El pesimista bloquea las celdas a las que el rival puede saltar el
        proximo turno. Sin esa cuenta el bot se mete en pasillos que el rival
        cierra enseguida.
        """
        relleno = FloodFill(self.estado.board, self.estado.liberacion(crezco=come))
        alcanzables = relleno.alcanzables(celda)
        pesimista = relleno.alcanzables(celda, self.amenazas - {celda})
        return alcanzables, len(pesimista)

    def _territorio(self, celda):
        """Cuenta las celdas que gano antes que el rival saliendo por `celda`."""
        mias = self.buscador.distancias(celda, self._sin_colas())
        return Territory(mias, self._distancias_rival).contar()

    def _objetivos(self, celda, alcanzables):
        """Comida que esta dentro de la region alcanzable, sin contar la actual."""
        return (self.estado.comida & alcanzables) - {celda}

    def _distancia_comida(self, celda, alcanzables, come):
        """Movimientos hasta la comida mas cercana, o hasta la propia cola.

        Si no hay comida al alcance el bot entra en modo supervivencia y usa
        su cola como destino: perseguirla siempre deja una salida abierta.
        """
        if come:
            return 0
        objetivos = self._objetivos(celda, alcanzables)
        distancia = self.buscador.distancia_a(celda, objetivos, self._sin_colas())
        if distancia is not None:
            return distancia
        return self._distancia_a_la_cola(celda)

    def _distancia_a_la_cola(self, celda):
        """Distancia a la propia cola, o el maximo si tampoco se llega."""
        cola = self.estado.yo.cola
        distancia = self.buscador.distancia_a(celda, {cola}, self._sin_colas())
        if distancia is None:
            return DISTANCIA_MAXIMA
        return distancia

    def _alcanzo_cola(self, alcanzables):
        """True si puedo volver a mi cola, la garantia de no quedar encerrado."""
        cola = self.estado.yo.cola
        return cola is None or cola in alcanzables

    def evaluar(self, direccion):
        """Analiza una direccion y devuelve el movimiento con sus metricas.

        Args:
            direccion: ``"up"``, ``"down"``, ``"left"`` o ``"right"``.

        Returns:
            Move: movimiento candidato ya medido.
        """
        celda = celda_destino(self.estado.yo.cabeza, direccion)
        come = celda in self.estado.comida
        alcanzables, pesimista = self._espacios(celda, come)
        metricas = {
            "espacio": len(alcanzables),
            "espacio_pesimista": pesimista,
            "territorio": self._territorio(celda),
            "distancia_comida": self._distancia_comida(celda, alcanzables, come),
            "libertad": self._libertad(celda),
            "amenazado": celda in self.amenazas,
            "come": come,
            "alcanzo_cola": self._alcanzo_cola(alcanzables),
            "largo_futuro": self.estado.yo.largo + (1 if come else 0),
        }
        return Move(direccion, celda, metricas)

    def evaluar_todos(self):
        """Evalua todas las direcciones legales del turno.

        Returns:
            list: movimientos candidatos, sin ordenar.
        """
        if not self.estado.yo.existe:
            return []
        return [self.evaluar(nombre) for nombre in self.direcciones_legales()]


def celdas_vecinas_validas(board, celda):
    """Atajo publico a los vecinos que caen dentro del tablero."""
    return vecinos_validos(board, celda)
