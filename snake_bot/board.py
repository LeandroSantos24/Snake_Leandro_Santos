"""Representacion del tablero de juego.

El servidor manda el tablero como un unico string: cada fila envuelta en
barras verticales y las filas unidas por saltos de linea. Por ejemplo::

    |               |
    |  aaA          |
    |      *        |

Esta clase se encarga de convertir ese texto en algo consultable por
coordenadas ``(fila, columna)``, con la fila 0 arriba de todo.
"""


class Board:
    """Tablero de Snake en forma de grilla de caracteres.

    Se construye normalmente con :meth:`desde_texto`, que parsea el string
    que envia el servidor. El constructor recibe las filas ya limpias para
    que sea facil crear tableros a mano en los tests.
    """

    def __init__(self, filas):
        """Guarda las filas y las rellena para que todas midan lo mismo.

        Args:
            filas: lista de strings, una por fila del tablero.
        """
        self._filas = self._emparejar(filas)

    @staticmethod
    def _emparejar(filas):
        """Rellena las filas con espacios hasta igualar la mas larga."""
        if not filas:
            return []
        ancho = max(len(fila) for fila in filas)
        return [fila.ljust(ancho) for fila in filas]

    @staticmethod
    def _quitar_barras(linea):
        """Devuelve el contenido entre la primera y la ultima barra.

        Si la linea no tiene barras se devuelve tal cual. No se usa strip()
        porque los espacios de adentro son celdas vacias y hay que conservarlos.
        """
        inicio = linea.find("|")
        fin = linea.rfind("|")
        if inicio == -1 or fin <= inicio:
            return linea
        return linea[inicio + 1:fin]

    @classmethod
    def _lineas_utiles(cls, texto):
        """Separa el texto en lineas y descarta las que estan vacias."""
        lineas = texto.split("\n")
        return [linea.rstrip("\r") for linea in lineas if linea.strip()]

    @classmethod
    def desde_texto(cls, texto):
        """Construye un Board a partir del string que manda el servidor.

        Args:
            texto: tablero completo como string.

        Returns:
            Board: tablero listo para consultar.
        """
        lineas = cls._lineas_utiles(texto or "")
        return cls([cls._quitar_barras(linea) for linea in lineas])

    @property
    def rows(self):
        """Cantidad de filas del tablero."""
        return len(self._filas)

    @property
    def cols(self):
        """Cantidad de columnas del tablero."""
        if not self._filas:
            return 0
        return len(self._filas[0])

    @property
    def vacio(self):
        """True si el tablero no tiene ninguna celda."""
        return self.rows == 0 or self.cols == 0

    def dentro(self, celda):
        """Indica si la celda cae dentro de los limites del tablero.

        Args:
            celda: tupla ``(fila, columna)``.

        Returns:
            bool: True si la celda existe en el tablero.
        """
        fila, columna = celda
        return 0 <= fila < self.rows and 0 <= columna < self.cols

    def simbolo(self, celda):
        """Devuelve el caracter que hay en una celda, o None si esta afuera."""
        if not self.dentro(celda):
            return None
        fila, columna = celda
        return self._filas[fila][columna]

    def celdas(self):
        """Itera todas las celdas del tablero como pares ``(posicion, simbolo)``."""
        for fila, contenido in enumerate(self._filas):
            for columna, simbolo in enumerate(contenido):
                yield (fila, columna), simbolo

    def posiciones_de(self, simbolo):
        """Devuelve el conjunto de celdas que contienen un simbolo dado.

        Args:
            simbolo: caracter a buscar, por ejemplo ``"*"`` para la comida.

        Returns:
            set: celdas donde aparece ese simbolo.
        """
        return {pos for pos, valor in self.celdas() if valor == simbolo}

    def __str__(self):
        """Reconstruye el tablero en el mismo formato que manda el servidor."""
        return "\n".join("|" + fila + "|" for fila in self._filas)
