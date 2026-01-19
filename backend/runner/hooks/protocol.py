"""Protocol definition for world-specific hooks.

This module defines the WorldHooks protocol that all world hook implementations
must satisfy. It allows the SimulationRunner to be extended with world-specific
features without embedding assumptions into the core runner.
"""

from typing import Any, Optional, Protocol


class WorldHooks(Protocol):
    """Protocol for world-specific feature extensions.

    A world can optionally implement these hooks to add custom features
    to the runner without modifying the core runner logic.

    Each world type (tank, petri, soccer, etc.) can have its own hooks
    implementation that provides world-specific behavior.
    """

    def supports_command(self, command: str) -> bool:
        """Check if this world supports a specific command.

        Args:
            command: The command name to check

        Returns:
            True if the world can handle this command, False otherwise
        """
        ...

    def handle_command(self, runner: Any, command: str, data: dict) -> Optional[dict]:
        """Handle a world-specific command.

        Args:
            runner: The SimulationRunner instance
            command: The command name
            data: Command data/payload

        Returns:
            Response dict if handled, None to let runner handle it, or error dict
        """
        ...

    def build_world_extras(self, runner: Any) -> dict:
        """Build world-specific state extras (poker, leaderboards, etc).

        Args:
            runner: The SimulationRunner instance

        Returns:
            Dictionary of world-specific fields to merge into state payload
        """
        ...

    def warmup(self, runner: Any) -> None:
        """Optional warmup called once when runner starts.

        Args:
            runner: The SimulationRunner instance
        """
        ...

    def cleanup(self, runner: Any) -> None:
        """Optional cleanup called when runner stops.

        Args:
            runner: The SimulationRunner instance
        """
        ...

    def apply_physics_constraints(self, runner: Any) -> None:
        """Apply world-specific physics constraints (e.g. dish boundaries).

        Args:
            runner: The SimulationRunner instance
        """
        ...

    def cleanup_physics(self, runner: Any) -> None:
        """Clean up world-specific physics constraints.

        Args:
            runner: The SimulationRunner instance
        """
        ...

    def on_world_type_switch(self, runner: Any, old_type: str, new_type: str) -> None:
        """Called when world type switches.

        Args:
            runner: The SimulationRunner instance
            old_type: The previous world type
            new_type: The new world type
        """
        ...
