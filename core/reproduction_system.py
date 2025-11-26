"""Reproduction helpers for the simulation engine."""

from typing import TYPE_CHECKING

from core.constants import MATING_QUERY_RADIUS

if TYPE_CHECKING:
    from core.entities import Fish
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
            if not fish.can_reproduce():
                continue

            if environment is not None:
                nearby_fish = environment.nearby_agents_by_type(
                    fish, radius=MATING_QUERY_RADIUS, agent_class=Fish
                )
            else:
                nearby_fish = [f for f in fish_list if f is not fish]

            for potential_mate in nearby_fish:
                if potential_mate is fish:
                    continue

                if fish.try_mate(potential_mate):
                    break
