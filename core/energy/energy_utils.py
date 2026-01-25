"""Utilities for consistent energy adjustments."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class EnergyModifier(Protocol):
    """Minimal protocol for entities supporting energy mutations."""

    def modify_energy(self, amount: float, *, source: str = "unknown") -> float:
        """Apply an energy delta and return the actual change."""


def apply_energy_delta(
    entity: Any,
    delta: float,
    *,
    source: str = "unknown",
    allow_direct_assignment: bool = False,
) -> float:
    """Apply an energy delta using the entity's modify_energy interface when possible.

    Args:
        entity: The object whose energy should change.
        delta: The requested delta (positive for gain, negative for loss).
        source: Optional tag for metrics and reward bookkeeping.
        allow_direct_assignment: Permit attribute mutation fallback when the entity
            does not expose ``modify_energy``.

    Returns:
        The actual delta applied after clamping.
    """
    if delta == 0:
        return 0.0

    modify = getattr(entity, "modify_energy", None)
    if callable(modify):
        return modify(delta, source=source)

    if not allow_direct_assignment:
        raise AttributeError(
            "Entity does not expose modify_energy(); set allow_direct_assignment=True"
        )

    if not hasattr(entity, "energy"):
        raise AttributeError("Cannot apply energy delta without energy attribute.")

    old_energy = entity.energy
    max_energy = getattr(entity, "max_energy", None)
    new_energy = old_energy + delta
    if max_energy is not None:
        new_energy = max(0.0, min(new_energy, max_energy))
    else:
        new_energy = max(0.0, new_energy)

    entity.energy = new_energy
    return new_energy - old_energy
