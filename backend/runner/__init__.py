"""Backend runner package.

This package provides modular components for the SimulationRunner:
- CommandHandlerMixin: Command handling logic (add_food, pause, poker, etc.)
- state_builders: State payload construction helpers
"""

from backend.runner.command_handlers import CommandHandlerMixin

__all__ = ["CommandHandlerMixin"]
