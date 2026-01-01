"""In-process soccer training world.

This package provides a lightweight soccer simulation for training and evolution.
It is intentionally separate from the rcssserver adapter used for evaluation.
"""

from core.worlds.soccer_training.config import SoccerTrainingConfig
from core.worlds.soccer_training.interfaces import SoccerAction
from core.worlds.soccer_training.world import SoccerTrainingWorldBackendAdapter

__all__ = ["SoccerAction", "SoccerTrainingConfig", "SoccerTrainingWorldBackendAdapter"]
