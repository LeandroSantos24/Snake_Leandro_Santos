"""Movimientos candidatos y su valoracion.

Cada turno el bot tiene como mucho cuatro opciones. Este modulo representa
una de esas opciones ya analizada: a que celda lleva, cuanto espacio deja,
cuanto territorio gana y, sobre todo, que tan segura es.

La escala de seguridad es lo primero que se mira al ordenar. Las reglas del
juego lo justifican: chocar cuesta 500 puntos y le regala 1000 al rival,
mientras que una manzana da 100. Sobrevivir vale quince manzanas, asi que
ninguna cantidad de comida compensa un movimiento peligroso.
"""

# Vectores (delta_fila, delta_columna). La fila 0 es la de arriba, por eso
# "up" resta. Verificado contra el servidor real.
DIRECCIONES = {
    "up": (-1, 0),
    "down": (1, 0),
    "left": (0, -1),
    "right": (0, 1),
}

DIRECCION_POR_DEFECTO = "up"


class Seguridad:
    """Niveles de seguridad de un movimiento, de mejor a peor."""

    COMODO = 2
    JUSTO = 1
    PELIGROSO = 0


def celda_destino(origen, direccion):
    """Calcula a que celda lleva moverse en una direccion.

    Args:
        origen: celda actual de la cabeza.
        direccion: ``"up"``, ``"down"``, ``"left"`` o ``"right"``.

    Returns:
        tuple: celda destino.
    """
    fila, columna = origen
    delta_fila, delta_columna = DIRECCIONES[direccion]
    return (fila + delta_fila, columna + delta_columna)


class Move:
    """Un movimiento candidato con todas sus metricas ya calculadas."""

    def __init__(self, direccion, celda, metricas):
        """Guarda el resultado del analisis de una direccion.

        Args:
            direccion: nombre de la direccion.
            celda: celda a la que lleva el movimiento.
            metricas: diccionario con espacio, espacio_pesimista, territorio,
                distancia_comida, libertad, amenazado, come, alcanzo_cola y
                largo_futuro.
        """
        self.direccion = direccion
        self.celda = celda
        self.metricas = dict(metricas)

    def __getattr__(self, nombre):
        """Permite leer las metricas como si fueran atributos."""
        try:
            return self.metricas[nombre]
        except KeyError:
            raise AttributeError(nombre) from None

    def umbral(self, margen):
        """Espacio minimo que se considera aceptable para este movimiento."""
        return self.largo_futuro + margen

    def _condiciones(self, margen):
        """Las cuatro condiciones de seguridad, como lista de booleanos."""
        minimo = self.umbral(margen)
        return [
            self.alcanzo_cola,
            self.espacio >= minimo,
            self.espacio_pesimista >= minimo,
            self.territorio >= minimo,
        ]

    def nivel(self, margen):
        """Clasifica el movimiento en la escala de :class:`Seguridad`.

        Comodo exige las cuatro condiciones. Justo se conforma con tener
        espacio suficiente mas alguna garantia adicional: poder volver a la
        cola o aguantar el avance del rival.

        Args:
            margen: celdas libres extra que se exigen ademas del largo.

        Returns:
            int: uno de los valores de :class:`Seguridad`.
        """
        cola, espacio, pesimista, territorio = self._condiciones(margen)
        if all((cola, espacio, pesimista, territorio)):
            return Seguridad.COMODO
        if espacio and (cola or pesimista):
            return Seguridad.JUSTO
        return Seguridad.PELIGROSO

    def __repr__(self):
        """Representacion corta, util al depurar una partida."""
        return "<Move {} espacio={} territorio={}>".format(
            self.direccion, self.espacio, self.territorio)
