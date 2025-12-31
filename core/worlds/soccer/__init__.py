"""Soccer world implementation for training and evaluation.

This package provides:
- SoccerTrainingWorld: Pure-python physics-based training environment
- SoccerWorldBackendAdapter: MultiAgentWorldBackend implementation
- SoccerWorldConfig: Configuration for soccer simulations
- (Future) RCSSServerAdapter: Adapter for real rcssserver evaluation
"""

from core.worlds.soccer.config import SoccerWorldConfig

__all__ = ["SoccerWorldConfig"]
