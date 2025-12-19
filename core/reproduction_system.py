"""Reproduction system for the simulation.

This module handles fish reproduction logic, including asexual reproduction
triggered by genetic traits. The system extends BaseSystem for consistent
interface and lifecycle management.

Architecture Notes:
- Extends BaseSystem for uniform system management
- Called via update(frame) in the system registry
- Tracks reproduction statistics for debugging
"""

import random
from typing import TYPE_CHECKING, Any, Dict

from core.systems.base import BaseSystem

if TYPE_CHECKING:
    from core.simulation_engine import SimulationEngine


class ReproductionSystem(BaseSystem):
    """Handle fish reproduction logic using the engine context.

    This system manages asexual reproduction based on genetic traits.
    Sexual reproduction is handled through the poker system.

    Attributes:
        _asexual_checks: Number of fish checked for asexual reproduction
        _asexual_triggered: Number of asexual reproductions triggered
    """

    def __init__(self, engine: "SimulationEngine") -> None:
        """Initialize the reproduction system.

        Args:
            engine: The simulation engine
        """
        super().__init__(engine, "Reproduction")
        self._asexual_checks: int = 0
        self._asexual_triggered: int = 0

    def _do_update(self, frame: int) -> None:
        """Check for asexual reproduction each frame.

        Args:
            frame: Current simulation frame number
        """
        self._handle_asexual_reproduction()

    def _handle_asexual_reproduction(self) -> None:
        """Handle fish reproduction by checking for asexual reproduction."""
        from core.entities import Fish

        all_entities = self._engine.get_all_entities()
        fish_list = [e for e in all_entities if type(e) is Fish or isinstance(e, Fish)]

        if len(fish_list) < 1:
            return

        for fish in fish_list:
            if not fish._reproduction_component.can_asexually_reproduce(
                fish.life_stage, fish.energy, fish.max_energy
            ):
                continue

            self._asexual_checks += 1

            # Access the trait correctly: genome.behavioral.asexual_reproduction_chance.value
            asexual_trait = fish.genome.behavioral.asexual_reproduction_chance.value
            if random.random() < asexual_trait:
                fish._reproduction_component.start_asexual_pregnancy()
                self._asexual_triggered += 1

    def handle_reproduction(self) -> None:
        """Legacy method for backward compatibility.

        This method is called directly by SimulationEngine for now.
        Will be removed once full system registry integration is complete.
        """
        self._handle_asexual_reproduction()

    def get_debug_info(self) -> Dict[str, Any]:
        """Return reproduction statistics for debugging.

        Returns:
            Dictionary containing system state and statistics
        """
        return {
            **super().get_debug_info(),
            "asexual_checks": self._asexual_checks,
            "asexual_triggered": self._asexual_triggered,
            "trigger_rate": (
                self._asexual_triggered / self._asexual_checks
                if self._asexual_checks > 0
                else 0.0
            ),
        }
