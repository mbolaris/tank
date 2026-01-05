"""Backend runner package.

This package provides modular components for the SimulationRunner:
- CommandHandlerMixin: Command handling logic (add_food, pause, poker, etc.)
- state_builders: State payload construction helpers
- RunnerProtocol: Unified interface for all runner types
"""

from backend.runner.command_handlers import CommandHandlerMixin
from backend.runner.runner_protocol import RunnerProtocol

__all__ = ["CommandHandlerMixin", "RunnerProtocol"]
