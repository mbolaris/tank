"""Backend runner package.

This package provides modular components for the SimulationRunner:
- CommandHandlerMixin: Command handling logic (add_food, pause, poker, etc.)
"""

from backend.runner.command_handlers import CommandHandlerMixin

__all__ = ["CommandHandlerMixin"]
