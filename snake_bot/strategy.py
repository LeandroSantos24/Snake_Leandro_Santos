"""Decision final del turno.

La estrategia toma los movimientos ya medidos por el evaluador, les pone un
puntaje y elige. El orden es siempre el mismo: primero el nivel de seguridad,
y solo entre movimientos igual de seguros se compara el puntaje.

Ese orden no es un detalle de implementacion, sale de la tabla de puntos del
juego: chocar son 500 puntos menos para mi y 1000 mas para el rival, contra
los 100 de una manzana. Por eso ninguna cantidad de comida justifica bajar
un escalon de seguridad.
"""

from .evaluator import MoveEvaluator
from .game_state import GameState
from .moves import DIRECCION_POR_DEFECTO, DIRECCIONES, celda_destino


class Pesos:
    """Coeficientes de la funcion de puntaje.

    Se ajustaron con una busqueda automatica sobre partidas simuladas,
    priorizando primero no chocar y despues ganar por puntos.
    """

    ESPACIO = 1.0
    TERRITORIO = 1.5
    LIBERTAD = 10.0
    COMIDA = 20.0
    AMENAZA = 30.0
    MARGEN_SEGURIDAD = 2
    TOPE_COMIDA = 20


class Strategy:
    """Elige la direccion de cada turno."""

    def __init__(self, pesos=Pesos, margen=None):
        """Permite cambiar los pesos sin tocar el codigo de la decision.

        Args:
            pesos: clase o instancia con los coeficientes.
            margen: celdas de seguridad extra; por defecto el de los pesos.
        """
        self.pesos = pesos
        self.margen = pesos.MARGEN_SEGURIDAD if margen is None else margen

    def _premio_espacio(self, move):
        """Aporte del espacio disponible, promediando optimista y pesimista."""
        promedio = (move.espacio + move.espacio_pesimista) / 2
        return self.pesos.ESPACIO * promedio

    def _premio_posicion(self, move):
        """Aporte del territorio controlado y de las salidas de la celda."""
        return (self.pesos.TERRITORIO * move.territorio
                + self.pesos.LIBERTAD * move.libertad)

    def _castigo(self, move):
        """Penalizacion por alejarse de la comida y por acercarse al rival."""
        distancia = min(move.distancia_comida, self.pesos.TOPE_COMIDA)
        amenaza = self.pesos.AMENAZA if move.amenazado else 0
        return self.pesos.COMIDA * distancia + amenaza

    def puntaje(self, move):
        """Puntaje total de un movimiento, ya evaluado.

        Args:
            move: instancia de :class:`~snake_bot.moves.Move`.

        Returns:
            float: cuanto mas alto, mejor.
        """
        return (self._premio_espacio(move)
                + self._premio_posicion(move)
                - self._castigo(move))

    def _orden(self, move):
        """Clave de ordenamiento: primero seguridad, despues puntaje."""
        return (move.nivel(self.margen), self.puntaje(move))

    def ordenar(self, movimientos):
        """Ordena los movimientos del mejor al peor.

        Args:
            movimientos: lista de :class:`~snake_bot.moves.Move`.

        Returns:
            list: la misma lista ordenada por seguridad y puntaje.
        """
        return sorted(movimientos, key=self._orden, reverse=True)

    def evaluar(self, estado):
        """Devuelve todos los movimientos del turno, ya ordenados.

        Sirve para depurar: muestra por que el bot eligio lo que eligio.
        """
        return self.ordenar(MoveEvaluator(estado).evaluar_todos())

    def elegir(self, estado):
        """Elige la mejor direccion para un estado dado.

        Args:
            estado: instancia de :class:`~snake_bot.game_state.GameState`.

        Returns:
            str: direccion elegida.
        """
        movimientos = self.evaluar(estado)
        if movimientos:
            return movimientos[0].direccion
        return self._ultimo_recurso(estado)

    @staticmethod
    def _ultimo_recurso(estado):
        """Direccion de emergencia cuando ningun movimiento es legal.

        La partida ya esta perdida, pero conviene mandar una jugada valida:
        un turno sin respuesta tambien esta penalizado por el servidor.
        """
        if not estado.yo.existe:
            return DIRECCION_POR_DEFECTO
        dentro = [nombre for nombre in DIRECCIONES
                  if estado.board.dentro(celda_destino(estado.yo.cabeza, nombre))]
        return dentro[0] if dentro else DIRECCION_POR_DEFECTO

    def decidir(self, turn_data):
        """Punto de entrada desde el cliente: recibe el JSON y devuelve la jugada.

        Args:
            turn_data: contenido del campo ``data`` del evento ``your_turn``.

        Returns:
            str: ``"up"``, ``"down"``, ``"left"`` o ``"right"``.
        """
        return self.elegir(GameState.desde_turno(turn_data))
