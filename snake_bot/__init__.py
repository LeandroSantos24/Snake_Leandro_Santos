"""Bot autonomo para el juego Snake de la plataforma CodeChallenge."""

from .analysis import FloodFill, PathFinder, Territory
from .board import Board
from .client import SnakeClient
from .evaluator import MoveEvaluator
from .game_state import GameState
from .logger import MatchLogger
from .moves import Move, Seguridad
from .snake import Snake
from .strategy import Pesos, Strategy

__all__ = [
    "Board",
    "FloodFill",
    "GameState",
    "MatchLogger",
    "Move",
    "MoveEvaluator",
    "PathFinder",
    "Pesos",
    "Seguridad",
    "Snake",
    "SnakeClient",
    "Strategy",
    "Territory",
]
