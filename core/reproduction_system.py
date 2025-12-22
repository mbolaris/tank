"""Reproduction system for the simulation.

This module handles fish reproduction logic, including asexual reproduction
triggered by genetic traits. The system extends BaseSystem for consistent
interface and lifecycle management.

Architecture Notes:
- Extends BaseSystem for uniform system management
- Runs in UpdatePhase.REPRODUCTION
- Tracks reproduction statistics for debugging
- Returns SystemResult for consistency with other systems
"""

import random
from typing import TYPE_CHECKING, Any, Dict

from core.systems.base import BaseSystem, SystemResult
from core.update_phases import UpdatePhase, runs_in_phase

if TYPE_CHECKING:
    from core.simulation_engine import SimulationEngine


@runs_in_phase(UpdatePhase.REPRODUCTION)
class ReproductionSystem(BaseSystem):
    """Handle fish reproduction logic using the engine context.

    This system runs in the REPRODUCTION phase and manages asexual
    reproduction based on genetic traits. Sexual reproduction is
    handled through the poker system.

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

    def _do_update(self, frame: int) -> SystemResult:
        """Check for asexual reproduction each frame.

        Args:
            frame: Current simulation frame number

        Returns:
            SystemResult with reproduction statistics
        """
        initial_triggered = self._asexual_triggered
        self._handle_asexual_reproduction()

        # Calculate how many reproductions occurred this frame
        triggered_this_frame = self._asexual_triggered - initial_triggered

        return SystemResult(
            entities_affected=triggered_this_frame,
            details={
                "asexual_triggered": triggered_this_frame,
            },
        )

    def _handle_asexual_reproduction(self) -> None:
        """Handle fish reproduction by checking for asexual reproduction."""
        from core.entities import Fish

        all_entities = self._engine.get_all_entities()
        fish_list = [e for e in all_entities if type(e) is Fish or isinstance(e, Fish)]

        if len(fish_list) < 1:
            return
        
        # Skip reproduction if at max population - don't waste energy on rejected babies
        ecosystem = self._engine.ecosystem
        if ecosystem is not None and len(fish_list) >= ecosystem.max_population:
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
                # Trigger instant asexual reproduction
                baby = fish._create_asexual_offspring()
                if baby is not None:
                    # Add baby to environment
                    environment = fish.environment
                    if environment is not None and hasattr(environment, "add_entity"):
                        environment.add_entity(baby)
                        baby.register_birth()
                    self._asexual_triggered += 1

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
