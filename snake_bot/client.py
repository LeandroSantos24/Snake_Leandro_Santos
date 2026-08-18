"""Cliente websocket del bot.

Traduce entre el servidor y la estrategia: recibe eventos JSON, y cuando le
toca jugar le pide la direccion a :class:`~snake_bot.strategy.Strategy` y
responde con la accion correspondiente.

El manejo de eventos usa una tabla de despacho en vez de una cadena de ``if``.
Ademas de bajar la complejidad, deja el codigo abierto a eventos nuevos: si
la catedra agrega uno, se suma una entrada al diccionario y su metodo.

La conexion se recibe desde afuera (:meth:`SnakeClient.manejar` trabaja sobre
cualquier objeto con ``send``), asi que toda la logica se puede probar sin
levantar un servidor de verdad.
"""

import json

from .logger import ENTRADA, SALIDA, MatchLogger
from .strategy import Strategy

SERVIDOR = "wss://server.codechallenge.net.ar/ws"
JUEGO = "snake"


class SnakeClient:
    """Bot conectado al servidor de CodeChallenge."""

    def __init__(self, token, estrategia=None, logger=None, servidor=SERVIDOR):
        """Arma el cliente.

        Args:
            token: token del bot, obtenido en la seccion My Bots.
            estrategia: instancia de :class:`~snake_bot.strategy.Strategy`.
            logger: instancia de :class:`~snake_bot.logger.MatchLogger`.
            servidor: URL base del websocket.
        """
        self.token = token
        self.estrategia = estrategia or Strategy()
        self.logger = logger or MatchLogger()
        self.servidor = servidor
        self.usuarios = []
        self.turnos = 0
        self.ultimo_resultado = None
        self._handlers = {
            "list_users": self._al_listar_usuarios,
            "challenge": self._al_ser_desafiado,
            "your_turn": self._al_jugar_turno,
            "game_over": self._al_terminar,
            "error": self._al_fallar,
        }

    @property
    def url(self):
        """URL completa de conexion, con el token como parametro."""
        return "{}?token={}".format(self.servidor, self.token)

    # -- envio y recepcion -------------------------------------------------

    async def enviar(self, conexion, accion, datos, game_id=None):
        """Manda una accion al servidor y la deja registrada.

        Args:
            conexion: objeto con un metodo asincronico ``send``.
            accion: nombre de la accion, por ejemplo ``"move"``.
            datos: contenido del campo ``data``.
            game_id: partida a la que corresponde, para el log.
        """
        mensaje = {"action": accion, "data": datos}
        await conexion.send(json.dumps(mensaje))
        self.logger.registrar(game_id, SALIDA, mensaje)

    async def manejar(self, conexion, mensaje):
        """Procesa un evento del servidor.

        Args:
            conexion: conexion por la que responder.
            mensaje: evento ya convertido a diccionario.

        Returns:
            bool: True si el evento era conocido.
        """
        evento = mensaje.get("event")
        datos = mensaje.get("data") or {}
        self.logger.registrar(datos.get("game_id"), ENTRADA, mensaje)
        handler = self._handlers.get(evento)
        if handler is None:
            return False
        await handler(conexion, datos)
        return True

    async def recibir(self, conexion, crudo):
        """Convierte el texto recibido en evento y lo procesa.

        Un mensaje que no sea JSON valido se ignora en lugar de cortar la
        partida: perder un turno es mejor que perder el juego entero.
        """
        try:
            mensaje = json.loads(crudo)
        except (ValueError, TypeError):
            return False
        return await self.manejar(conexion, mensaje)

    # -- manejadores de eventos --------------------------------------------

    async def _al_listar_usuarios(self, conexion, datos):
        """Guarda quien esta conectado."""
        del conexion
        self.usuarios = datos.get("users", [])

    async def _al_ser_desafiado(self, conexion, datos):
        """Acepta automaticamente cualquier desafio entrante."""
        await self.enviar(conexion, "accept_challenge",
                          {"challenge_id": datos.get("challenge_id")})

    async def _al_jugar_turno(self, conexion, datos):
        """Pide la jugada a la estrategia y la envia.

        El ``turn_token`` y el ``game_id`` se devuelven tal cual: si no
        coinciden, el servidor penaliza el turno.
        """
        self.turnos += 1
        direccion = self.estrategia.decidir(datos)
        await self.enviar(
            conexion, "move",
            {
                "game_id": datos.get("game_id"),
                "turn_token": datos.get("turn_token"),
                "direction": direccion,
            },
            game_id=datos.get("game_id"),
        )

    async def _al_terminar(self, conexion, datos):
        """Cierra el log de la partida y guarda el resultado."""
        del conexion
        self.ultimo_resultado = datos
        self.turnos = 0
        self.logger.cerrar(datos.get("game_id"))

    async def _al_fallar(self, conexion, datos):
        """Registra un error informado por el servidor."""
        del conexion
        self.ultimo_resultado = None
        self.errores = datos

    # -- acciones que puede iniciar el bot ---------------------------------

    async def desafiar(self, conexion, oponente):
        """Desafia a otro bot que este conectado."""
        await self.enviar(conexion, "challenge",
                          {"opponent": oponente, "game": JUEGO})

    async def listar_usuarios(self, conexion):
        """Pide al servidor la lista de bots conectados."""
        await self.enviar(conexion, "list_users", {})
