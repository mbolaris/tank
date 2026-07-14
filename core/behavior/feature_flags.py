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


def install_default_pursuit_module_if_enabled(
    genome: Genome, config: SimulationConfig | None
) -> None:
    """Give founders a shared pursuit module only in explicitly enabled experiments.

    Independently opt-in from the foraging graph itself. This supports clean
    graph/module ablations and lets the module be evaluated by soccer without
    installing the foraging controller. No random draws occur here.
    """
    if (
        config is not None
        and config.tank.target_pursuit_module_enabled
        and genome.behavioral.target_pursuit_module is None
    ):
        from core.behavior.pursuit_nodes import default_pursuit_module_graph
        from core.genetics.trait import GeneticTrait

        genome.behavioral.target_pursuit_module = GeneticTrait(default_pursuit_module_graph())


def install_default_target_memory_if_enabled(
    genome: Genome, config: SimulationConfig | None
) -> None:
    """Give founders default Target Memory parameters only when opted in.

    Independently opt-in from the graph and pursuit-module features. No
    random draws occur here - every founder starts from the same fixed
    defaults and diverges only through subsequent mutation, mirroring
    install_default_pursuit_module_if_enabled.
    """
    if (
        config is not None
        and config.tank.target_memory_enabled
        and genome.behavioral.target_memory is None
    ):
        from core.behavior.target_memory import TargetMemoryParams
        from core.genetics.trait import GeneticTrait

        genome.behavioral.target_memory = GeneticTrait(TargetMemoryParams())


def install_default_behavior_graph_features(
    genome: Genome, config: SimulationConfig | None
) -> None:
    """Install every opt-in graph-experiment founder default in one call."""
    install_default_graph_if_enabled(genome, config)
    install_default_pursuit_module_if_enabled(genome, config)
    install_default_target_memory_if_enabled(genome, config)


__all__ = [
    "install_default_behavior_graph_features",
    "install_default_graph_if_enabled",
    "install_default_pursuit_module_if_enabled",
    "install_default_target_memory_if_enabled",
]
