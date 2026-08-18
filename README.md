# Bot de Snake — CodeChallenge

[![CI](https://github.com/LeandroSantos24/Snake_Leandro_Santos/actions/workflows/ci.yml/badge.svg)](https://github.com/LeandroSantos24/Snake_Leandro_Santos/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/LeandroSantos24/Snake_Leandro_Santos/python-coverage-comment-action-data/endpoint.json)](https://github.com/LeandroSantos24/Snake_Leandro_Santos/actions/workflows/ci.yml)
[![Complejidad](https://img.shields.io/badge/complejidad-A-brightgreen)](https://github.com/rubik/xenon)
[![Lint](https://img.shields.io/badge/flake8-passing-brightgreen)](https://flake8.pycqa.org/)

Bot autónomo que juega al Snake por turnos contra otros bots en la plataforma
[CodeChallenge](https://codechallenge.net.ar). Se conecta por websocket, recibe
el tablero en cada turno y responde con una dirección.

Autor: Leandro Gastón Santos — Computación II, 2026.

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Ejecución

```bash
export BOT_TOKEN="tu-token"     # se obtiene en My Bots
python run.py
```

También acepta el token como argumento y puede desafiar a alguien al conectarse:

```bash
python run.py <TOKEN>
python run.py <TOKEN> --challenge rival@mail.com
```

Usar `BOT_TOKEN` es preferible: así el token no queda en el historial de la
terminal ni se puede subir al repositorio por error.

Cada partida deja un archivo `game_<id>.log` con todos los eventos recibidos
(`<`) y las acciones enviadas (`>`).

## Verificación de calidad

```bash
flake8 .                                                    # linter
coverage run -m unittest discover                           # tests
coverage report --fail-under=90                             # cobertura
xenon --max-absolute A --max-modules A --max-average A snake_bot/
```

Los cuatro comandos se ejecutan automáticamente en GitHub Actions ante cada
push a `main` y cada pull request.

## Estructura

```
snake_bot/
├── board.py       Tablero: parseo del texto del servidor y consultas por celda
├── snake.py       Serpiente: cuerpo, cola y cuándo se libera cada celda
├── game_state.py  Estado del turno: tablero + ambas serpientes + comida
├── analysis.py    FloodFill temporal, PathFinder (BFS) y Territory (Voronoi)
├── moves.py       Move: un movimiento candidato y su nivel de seguridad
├── evaluator.py   MoveEvaluator: calcula las métricas de cada dirección
├── strategy.py    Strategy: puntúa los movimientos y elige
├── client.py      SnakeClient: protocolo websocket
├── logger.py      MatchLogger: registro de partidas
└── cli.py         Argumentos de la línea de comandos
tests/             Un archivo de tests por módulo
run.py             Punto de entrada
```

La separación sigue una regla simple: `analysis` **mide** el tablero,
`evaluator` **calcula** las métricas de cada opción y `strategy` **decide**.
Cada capa se prueba por separado, y la conexión se inyecta desde afuera, así
que el cliente se testea completo sin levantar un servidor.

## Cómo decide la jugada

El orden de prioridades sale de la tabla de puntos del juego: chocar cuesta
**-500** y le da **+1000** al rival (1500 de diferencia), mientras que una
manzana da **+100**. Sobrevivir vale quince manzanas, así que ninguna cantidad
de comida justifica un movimiento riesgoso.

Para cada una de las cuatro direcciones:

1. **¿Es legal?** No es pared ni cuerpo. Si no, se descarta.
2. **¿Cuánto espacio queda, contando el tiempo?** Un *flood fill* común cuenta
   celdas conectadas, y ese número engaña: no sirve un hueco de 200 celdas si
   para entrar hay que atravesar un cuerpo que recién se mueve dentro de quince
   turnos. `FloodFill` avanza turno a turno y solo pisa una celda si ya se
   liberó cuando llega.
3. **¿Cuánto territorio se controla?** `Territory` arma un diagrama de Voronoi:
   solo cuentan las celdas que se alcanzan **antes** que el rival. Es lo que
   detecta a tiempo los pasillos que el rival está por cerrar.
4. **¿Se puede volver a la propia cola?** Si se puede, siempre queda el recurso
   de perseguirla y nunca hay encierro.
5. **¿Y si el rival avanza?** Un segundo flood fill pesimista bloquea las celdas
   vecinas a la cabeza contraria.
6. **¿Qué tan cerca está la comida?** BFS a la manzana más cercana alcanzable.
   Si no hay ninguna, modo supervivencia: perseguir la cola.

Con esas métricas cada movimiento recibe un **nivel de seguridad** (cómodo,
justo o peligroso) y un puntaje. El orden es primero por nivel y solo después
por puntaje, de modo que un movimiento peligroso nunca le gana a uno seguro.

## Resultados

| Escenario | Partidas | Ganadas | Choques propios |
|---|---|---|---|
| Torneo y desafíos reales | 28 | 22 | 2 |
| Simulador vs. rival glotón | 250 | 84% | 0.4% |
| Simulador vs. rival aleatorio | 100 | 100% | 0% |

Los dos choques reales corresponden a la primera versión de la estrategia, que
no modelaba el tiempo en el flood fill. Al reproducir esas partidas contra la
versión actual, la decisión cambia justo en el turno en que la versión anterior
entraba en la trampa. Desde esa corrección no volvió a chocar en partidas reales.

Cada decisión tarda unos pocos milisegundos, muy por debajo del límite de
tiempo por movimiento que impone el servidor.
