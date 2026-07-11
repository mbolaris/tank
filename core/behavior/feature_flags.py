"""Feature-flag installation for experimental behavior graph populations."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.config.simulation_config import SimulationConfig
    from core.genetics.genome import Genome


def install_default_graph_if_enabled(genome: Genome, config: SimulationConfig | None) -> None:
    """Give founders a fixed graph only in explicitly enabled experiments.

    No random draws occur here, preserving the legacy replay/RNG schedule when
    the graph experiment is disabled.
    """
    if (
        config is not None
        and config.tank.graph_behavior_enabled
        and genome.behavioral.behavior_graph is None
    ):
        from core.behavior.tank_adapter import default_foraging_graph
        from core.genetics.trait import GeneticTrait

        genome.behavioral.behavior_graph = GeneticTrait(default_foraging_graph())


__all__ = ["install_default_graph_if_enabled"]
