"""Reproduction helpers for the simulation engine."""

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.simulation_engine import SimulationEngine


class ReproductionSystem:
    """Handle fish reproduction logic using the engine context."""

    def __init__(self, engine: "SimulationEngine") -> None:
        self.engine = engine

    def handle_reproduction(self) -> None:
        """Handle fish reproduction by finding mates."""
        from core.entities import Fish

        all_entities = self.engine.get_all_entities()
        fish_list = [e for e in all_entities if type(e) is Fish or isinstance(e, Fish)]

        if len(fish_list) < 2:
            return

        environment = self.engine.environment

        for fish in fish_list:
            if not fish._reproduction_component.can_asexually_reproduce(
                fish.life_stage, fish.energy, fish.max_energy
            ):
                continue

            asexual_trait = getattr(fish.genome, "asexual_reproduction_chance", 0.0)
            if random.random() < asexual_trait:
                fish._reproduction_component.start_asexual_pregnancy()
