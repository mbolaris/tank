"""World-specific feature hooks for the simulation runner.

This module re-exports from the hooks package for API stability.

The hooks are organized in separate modules:
- backend/runner/hooks/protocol.py: WorldHooks protocol
- backend/runner/hooks/noop_hooks.py: NoOpWorldHooks
- backend/runner/hooks/tank_hooks.py: TankWorldHooks
- backend/runner/hooks/petri_hooks.py: PetriWorldHooks
- backend/runner/hooks/registry.py: get_hooks_for_world factory

New code should import from backend.runner.hooks directly.
"""

# Re-export all public symbols for backwards compatibility
from backend.runner.hooks import (NoOpWorldHooks, PetriWorldHooks,
                                  TankWorldHooks, WorldHooks,
                                  get_hooks_for_world)

__all__ = [
    "NoOpWorldHooks",
    "PetriWorldHooks",
    "TankWorldHooks",
    "WorldHooks",
    "get_hooks_for_world",
]
