"""Estado de un turno de la partida.

Junta todo lo que el bot necesita saber para decidir: el tablero, las dos
serpientes y donde esta la comida. Se construye directamente a partir del
diccionario ``turn_data`` que manda el servidor en el evento ``your_turn``.

Los simbolos del tablero son: ``A``/``B`` para las cabezas, ``a``/``b`` para
los cuerpos y ``*`` para la comida.
"""

from .board import Board
from .snake import Snake

COMIDA = "*"
LADO_POR_DEFECTO = "A"
LADOS = ("A", "B")


class GameState:
    """Fotografia de la partida en un turno."""

    def __init__(self, board, side, remaining_moves=0):
        """Arma el estado a partir de un tablero ya parseado.

        Args:
            board: instancia de :class:`Board`.
            side: letra de nuestra serpiente, ``"A"`` o ``"B"``.
            remaining_moves: movimientos que quedan en la partida.
        """
        self.board = board
        self.side = side
        self.remaining_moves = remaining_moves
        self.comida = board.posiciones_de(COMIDA)
        self.yo = self._armar_snake(side)
        self.rival = self._armar_snake(self._lado_rival(side))

    @staticmethod
    def _lado_rival(side):
        """Devuelve la letra del oponente."""
        return LADOS[1] if side == LADOS[0] else LADOS[0]

    @staticmethod
    def _normalizar_lado(valor):
        """Convierte el campo ``side`` del servidor en una letra valida."""
        letra = (valor or "").strip().upper()
        return letra if letra in LADOS else LADO_POR_DEFECTO

    @staticmethod
    def _aplanar(turn_data):
        """Junta los datos del turno, vengan sueltos o dentro de ``turn_data``."""
        datos = dict(turn_data)
        anidado = datos.pop("turn_data", None)
        if isinstance(anidado, dict):
            return {**anidado, **datos}
        return datos

    def _armar_snake(self, letra):
        """Construye una serpiente buscando su cabeza y su cuerpo en el tablero."""
        cabezas = self.board.posiciones_de(letra)
        cuerpo = self.board.posiciones_de(letra.lower())
        cabeza = next(iter(cabezas), None)
        return Snake(cabeza, cuerpo)

    @classmethod
    def desde_turno(cls, turn_data):
        """Crea el estado a partir del diccionario que manda el servidor.

        Args:
            turn_data: contenido del campo ``data`` del evento ``your_turn``.

        Returns:
            GameState: estado listo para analizar.
        """
        datos = cls._aplanar(turn_data)
        board = Board.desde_texto(datos.get("board", ""))
        return cls(
            board,
            cls._normalizar_lado(datos.get("side")),
            datos.get("remaining_moves", 0),
        )

    @property
    def ocupadas(self):
        """Todas las celdas ocupadas por alguna de las dos serpientes."""
        return self.yo.celdas | self.rival.celdas

    @property
    def amenazas(self):
        """Celdas que el rival podria ocupar en su proximo movimiento.

        Sirve para no quedar pegado a la cabeza contraria: si las dos cabezas
        van a la misma celda, el choque nos cuesta 500 puntos.
        """
        if not self.rival.existe:
            return set()
        return {celda for celda in vecinos_validos(self.board, self.rival.cabeza)}

    def liberacion(self, crezco=False):
        """Combina el calendario de liberacion de ambas serpientes.

        Args:
            crezco: True si en este movimiento nuestra serpiente come.

        Returns:
            dict: ``{celda: turnos que faltan para que quede libre}``.
        """
        calendario = self.yo.liberacion(crece=crezco)
        calendario.update(self.rival.liberacion(crece=True))
        return calendario


def vecinos_validos(board, celda):
    """Devuelve los vecinos de una celda que caen dentro del tablero.

    Args:
        board: instancia de :class:`Board`.
        celda: tupla ``(fila, columna)``.

    Returns:
        set: celdas vecinas validas.
    """
    from .snake import vecinos
    return {vecino for vecino in vecinos(celda) if board.dentro(vecino)}
