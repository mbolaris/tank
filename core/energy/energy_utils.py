"""Utilities for consistent energy adjustments."""

from __future__ import annotations

from typing import Protocol, cast, runtime_checkable


@runtime_checkable
class EnergyModifier(Protocol):
    """Minimal protocol for entities supporting energy mutations."""

    def modify_energy(self, amount: float, *, source: str = "unknown") -> float:
        """Apply an energy delta and return the actual change."""


class EnergyAttributeHolder(Protocol):
    """Object with mutable direct energy storage."""

    energy: float


class BoundedEnergyAttributeHolder(EnergyAttributeHolder, Protocol):
    """Object with direct energy storage and a maximum energy cap."""

    max_energy: float


def apply_energy_delta(
    entity: object,
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

    if isinstance(entity, EnergyModifier):
        return entity.modify_energy(delta, source=source)

    if not allow_direct_assignment:
        raise AttributeError(
            "Entity does not expose modify_energy(); set allow_direct_assignment=True"
        )

    if not hasattr(entity, "energy"):
        raise AttributeError("Cannot apply energy delta without energy attribute.")

    energy_holder = cast(EnergyAttributeHolder, entity)
    old_energy = float(energy_holder.energy)
    max_energy = (
        cast(BoundedEnergyAttributeHolder, entity).max_energy
        if hasattr(entity, "max_energy")
        else None
    )
    new_energy = old_energy + delta
    if max_energy is not None:
        new_energy = max(0.0, min(new_energy, float(max_energy)))
    else:
        new_energy = max(0.0, new_energy)

    energy_holder.energy = new_energy
    return float(new_energy - old_energy)
