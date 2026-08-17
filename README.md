# Bot de Snake — The Code Challenge

Bot autónomo que se conecta por websocket al servidor del Code Challenge y juega
al Snake por turnos.

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `bot.py` | Cliente websocket: conecta, acepta desafíos, juega y loguea. **No hace falta tocarlo.** |
| `strategy.py` | **Acá vive tu estrategia.** Parseo del tablero + decisión de la jugada. |
| `simulador.py` | Motor de Snake local para probar la estrategia sin servidor ni rivales. |
| `tunear.py` | Busca automáticamente los mejores pesos de la estrategia. |

## Instalación

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Correr el bot

```bash
python bot.py <TU_TOKEN>              # queda esperando desafíos
python bot.py <TU_TOKEN> --debug      # además muestra por qué eligió cada jugada
python bot.py <TU_TOKEN> --challenge rival@mail.com   # desafía apenas se conecte
```

Mejor todavía, para no dejar el token escrito en ningún lado:

```bash
export BOT_TOKEN="..."   # en Windows: set BOT_TOKEN=...
python bot.py
```

Cada partida deja un `game_<id>.log` con todos los eventos y acciones.

## Probar sin servidor

```bash
python simulador.py --partidas 100          # estadísticas contra un bot glotón
python simulador.py --ver                   # ver una partida animada
python simulador.py --rival yo              # tu bot contra sí mismo
python tunear.py                            # buscar mejores pesos
```

Resultados actuales (v2):

| Rival | Partidas | Ganadas | Choques propios |
|---|---|---|---|
| Glotón | 250 | 84% | 0.4% |
| Random | 100 | 100% | 0% |
| Versión v1 | 150 | 56% | 4% |

En 21 partidas reales contra otro competidor la v1 había chocado 2 veces (-500
cada una). El replay de esos logs confirma que la v2 elige distinto justo en el
turno en que la v1 entraba en la trampa.

## Cómo decide la jugada

El orden de prioridades sale de las reglas del juego: chocar cuesta **-500 y le
regala +1000 al rival** (1500 de diferencia), mientras que una manzana da **+100**.
O sea: sobrevivir vale muchísimo más que comer.

Para cada una de las 4 direcciones posibles:

1. **¿Es legal?** No es pared ni cuerpo (mío o del rival). Si no, se descarta.
2. **¿Cuánto espacio me queda, contando el tiempo?** *Flood fill temporal*: no
   alcanza con que una celda esté conectada, hay que llegar a tiempo. Las celdas
   de un cuerpo se liberan recién cuando pasa la cola, así que se modela **cuándo**
   queda libre cada una.
3. **¿Cuánto territorio controlo?** Diagrama de Voronoi: solo cuentan las celdas a
   las que llego **antes** que el rival. Es lo que evita meterse en pasillos que el
   rival cierra unos turnos después.
4. **¿Llego a mi propia cola?** Si puedo alcanzarla, siempre me queda el recurso de
   perseguirla y nunca me encierro.
5. **¿Y si el rival avanza?** Flood fill *pesimista* que bloquea las celdas vecinas
   a la cabeza rival.
6. **¿Qué tan cerca queda la comida?** BFS a la manzana más cercana alcanzable.
   Si no hay ninguna, modo supervivencia: persigo mi cola.

Las opciones se agrupan en **niveles de seguridad** (2 = cómodo, 1 = justo,
0 = peligroso) y dentro de cada nivel se ordenan por puntaje. Nunca elige un nivel
más bajo si hay uno más alto disponible.

## Pesos que podés tunear

En `strategy.py`:

```python
PESO_ESPACIO = 1.0       # espacio alcanzable a tiempo
PESO_TERRITORIO = 1.5    # celdas que gano yo antes que el rival
PESO_LIBERTAD = 10.0     # salidas de la celda destino
PESO_COMIDA = 20.0       # acercarse a la comida
PESO_RIESGO = 30.0       # castigo por quedar pegado a la cabeza rival
MARGEN_SEGURIDAD = 2     # celdas libres extra que exijo además de mi largo
```

## Si algo sale raro en la primera partida

- **Se mueve al revés en vertical**: poné `INVERTIR_VERTICAL = True` en `strategy.py`.
  (Ya verificado contra el servidor real: `up` sube, no hace falta invertir.)
- **El servidor rechaza la jugada**: revisá el `game_<id>.log`, ahí queda el JSON
  exacto que mandaste.

## Seguridad

Nunca subas el token al repo. Está en `.gitignore` por si acaso, pero lo más prolijo
es pasarlo siempre por variable de entorno.
