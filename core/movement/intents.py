"""Structured, inspectable movement decisions.

Movement controllers still arbitrate by priority, but they now communicate the
reason for a velocity through this small shared value object.  The object is
deliberately domain-neutral so graph, soccer, code-policy, and legacy behavior
controllers can coexist without a UI or caller needing to infer intent from a
bare velocity tuple.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

Velocity = tuple[float, float]


@dataclass(frozen=True)
class MovementIntent:
    """One controller's meaningful request to move.

    ``urgency`` and ``confidence`` are normalized descriptive signals.  They
    do not alter the existing priority arbitration in this first slice.
    """

    velocity: Velocity
    kind: str
    urgency: float
    confidence: float
    target_id: int | None
    source: str

    @classmethod
    def from_velocity(
        cls,
        velocity: Velocity | None,
        *,
        kind: str,
        source: str,
        urgency: float = 1.0,
        confidence: float = 1.0,
        target_id: int | None = None,
        allow_zero: bool = True,
    ) -> MovementIntent | None:
        """Adapt a legacy velocity result.

        Existing controllers may intentionally return ``(0, 0)``.  New graph
        controllers opt into ``allow_zero=False`` when zero means no drive.
        """
        if velocity is None:
            return None
        x, y = float(velocity[0]), float(velocity[1])
        if not math.isfinite(x) or not math.isfinite(y):
            return None
        if not allow_zero and math.hypot(x, y) <= 1e-9:
            return None
        return cls(
            velocity=(x, y),
            kind=kind,
            urgency=max(0.0, min(1.0, float(urgency))),
            confidence=max(0.0, min(1.0, float(confidence))),
            target_id=target_id,
            source=source,
        )


@dataclass(frozen=True)
class MovementArbitration:
    """The selected intent plus lower-priority sources not evaluated this tick."""

    selected: MovementIntent | None
    suppressed_sources: tuple[str, ...] = ()


__all__ = ["MovementArbitration", "MovementIntent", "Velocity"]
