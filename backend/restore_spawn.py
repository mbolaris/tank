"""How the restore path admits entities into a live engine.

Restoration does not run in lockstep with the simulation loop, so a restore can
land in the middle of a frame. The engine's privileged, immediate `add_entity`
refuses that outright - "Unsafe call to add_entity during phase ... Use
request_spawn() instead" - and a caller that treats the refusal as a warning
loses the entity for good.

That is what was happening to the tank's soccer objects. A restored world came
back with every other entity intact and no ball and no goal zones at all: the
engine refused those three spawns, `_bootstrap_transient_elements` logged the
refusal and moved on, and nothing retried. They stayed missing for the life of
the world, and flipping the ball/goals toggle did not bring them back - so on
any long-lived tank the arch, the hoop and the ball were simply never there.
"""

from __future__ import annotations

from typing import Any


def spawn_restored_entity(engine: Any, entity: Any) -> None:
    """Add `entity` to `engine`, immediately if that is allowed and queued if not.

    The order matters and is not merely caution. `_validate_restored_world`
    checks for the castle synchronously, right after `_bootstrap_static_elements`
    runs, so an unconditionally deferred spawn would read as a missing castle and
    fail the entire restore. Immediate is the default; deferring is the fallback
    for the one case where the engine will not take it.
    """
    try:
        engine.add_entity(entity)
    except RuntimeError:
        # Mid-frame. Queue for the next safe point rather than losing the entity.
        request_spawn = getattr(engine, "request_spawn", None)
        if not callable(request_spawn):
            raise
        request_spawn(entity, reason="world_restore")
