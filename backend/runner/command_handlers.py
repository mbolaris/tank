"""Command handlers for SimulationRunner.

This module composes domain-specific command handlers into a single mixin.
Logic has been extracted to backend/runner/commands/*.
"""

from backend.runner.commands.benchmark import BenchmarkCommands
from backend.runner.commands.control import ControlCommands
from backend.runner.commands.fish import FishCommands
from backend.runner.commands.food import FoodCommands
from backend.runner.commands.poker import PokerCommands
from backend.runner.commands.soccer import SoccerCommands


class CommandHandlerMixin(
    FoodCommands,
    FishCommands,
    ControlCommands,
    PokerCommands,
    SoccerCommands,
    BenchmarkCommands,
):
    """Mixin class composing all command handler methods for SimulationRunner.

    This class aggregates domain-specific command handlers to keep SimulationRunner
    clean while preserving the flattening mixin pattern interface.
    """

    pass
