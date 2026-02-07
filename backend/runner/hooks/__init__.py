"""World hooks package for simulation runner.

This package provides pluggable world-specific hooks that allow the SimulationRunner
to be extended with world-specific features without embedding assumptions into
the core runner logic.

The package is organized as:
- protocol.py: WorldHooks protocol definition
- noop_hooks.py: Default no-op implementation
- tank_hooks.py: Tank world hooks (poker, benchmarks, etc.)
- petri_hooks.py: Petri dish world hooks (circular physics)
- soccer_mixin.py: Soccer event collection mixin
- poker_mixin.py: Poker event/leaderboard collection mixin
- benchmark_mixin.py: Evolution benchmark tracking mixin
- registry.py: Hooks registry and factory function

Usage:
    from backend.runner.hooks import get_hooks_for_world, WorldHooks

    hooks = get_hooks_for_world("tank")  # Returns TankWorldHooks
    hooks = get_hooks_for_world("petri")  # Returns PetriWorldHooks
    hooks = get_hooks_for_world("unknown")  # Returns NoOpWorldHooks
"""

from backend.runner.hooks.noop_hooks import NoOpWorldHooks
from backend.runner.hooks.petri_hooks import PetriWorldHooks
from backend.runner.hooks.protocol import WorldHooks
from backend.runner.hooks.registry import (
    get_hooks_for_world,
    get_registered_world_types,
    register_hooks,
    unregister_hooks,
)
from backend.runner.hooks.tank_hooks import TankWorldHooks

__all__ = [
    # Protocol
    "WorldHooks",
    # Implementations
    "NoOpWorldHooks",
    "TankWorldHooks",
    "PetriWorldHooks",
    # Registry functions
    "get_hooks_for_world",
    "register_hooks",
    "unregister_hooks",
    "get_registered_world_types",
]
