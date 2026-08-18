"""Modelo de una serpiente.

Lo importante de esta clase no es solo saber que celdas ocupa la serpiente,
sino **cuando** las va a dejar libres. Una celda del cuerpo se libera cuando
la cola termina de pasar por ella, y eso depende de que tan lejos este de la
cabeza siguiendo el recorrido del cuerpo.

Ese dato es el que permite despues distinguir entre espacio que esta
"conectado" y espacio al que realmente se llega a tiempo.
"""

from collections import deque

VECINDAD = ((-1, 0), (1, 0), (0, -1), (0, 1))


def vecinos(celda):
    """Devuelve las cuatro celdas adyacentes (arriba, abajo, izq, der).

    Args:
        celda: tupla ``(fila, columna)``.

    Returns:
        tuple: las cuatro celdas vecinas.
    """
    fila, columna = celda
    return tuple((fila + df, columna + dc) for df, dc in VECINDAD)


class Snake:
    """Una serpiente del juego: su cabeza, su cuerpo y su recorrido."""

    def __init__(self, cabeza, cuerpo):
        """Crea la serpiente.

        Args:
            cabeza: celda de la cabeza, o None si no esta en el tablero.
            cuerpo: conjunto de celdas ocupadas por el cuerpo (sin la cabeza).
        """
        self.cabeza = cabeza
        self.cuerpo = set(cuerpo)
        self._indices = self._recorrer()

    @property
    def existe(self):
        """True si la serpiente esta presente en el tablero."""
        return self.cabeza is not None

    @property
    def largo(self):
        """Cantidad total de celdas que ocupa, contando la cabeza."""
        return len(self.cuerpo) + (1 if self.existe else 0)

    @property
    def celdas(self):
        """Conjunto con todas las celdas ocupadas, incluida la cabeza."""
        if not self.existe:
            return set(self.cuerpo)
        return self.cuerpo | {self.cabeza}

    @property
    def indices(self):
        """Diccionario ``{celda: distancia a la cabeza}``, con la cabeza en 0."""
        return dict(self._indices)

    @property
    def cola(self):
        """Celda mas alejada de la cabeza, o None si la serpiente es solo cabeza."""
        if len(self._indices) < 2:
            return None
        return max(self._indices, key=self._indices.get)

    def _recorrer(self):
        """Numera las celdas del cuerpo segun su distancia a la cabeza.

        Recorre la serpiente con un BFS restringido a sus propias celdas, que
        para un cuerpo continuo equivale a seguirlo de la cabeza a la cola.
        """
        if not self.existe:
            return {}
        indices = {self.cabeza: 0}
        pendientes = deque([self.cabeza])
        while pendientes:
            actual = pendientes.popleft()
            self._numerar_vecinos(actual, indices, pendientes)
        return indices

    def _numerar_vecinos(self, celda, indices, pendientes):
        """Asigna indice a los vecinos de `celda` que sean cuerpo sin numerar."""
        for vecino in vecinos(celda):
            if vecino in self.cuerpo and vecino not in indices:
                indices[vecino] = indices[celda] + 1
                pendientes.append(vecino)

    def liberacion(self, crece=False):
        """Calcula en cuantos turnos queda libre cada celda ocupada.

        Una celda con indice ``i`` (0 es la cabeza) queda libre cuando la cola
        la termina de pasar, es decir dentro de ``largo - i`` movimientos. Si la
        serpiente esta por comer no se acorta este turno, asi que todo se
        corre un lugar.

        Args:
            crece: True si la serpiente va a comer en este movimiento.

        Returns:
            dict: ``{celda: turnos que faltan para que quede libre}``.
        """
        extra = 1 if crece else 0
        return {celda: self.largo - indice + extra
                for celda, indice in self._indices.items()}
