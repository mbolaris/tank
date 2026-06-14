"""Frame output aggregation - collects per-frame spawn/removal/energy records.

Extracted from SimulationEngine so the per-frame delta tracking is an
individually testable unit. The engine exposes the aggregator's buffers via
thin compatibility properties (``_frame_spawns`` etc.) and delegates
``drain_frame_outputs()`` here.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.worlds.contracts import EnergyDeltaRecord, RemovalRequest, SpawnRequest


@dataclass(frozen=True)
class FrameOutputs:
    spawns: list[SpawnRequest]
    removals: list[RemovalRequest]
    energy_deltas: list[EnergyDeltaRecord]


class FrameAggregator:
    """Collects spawn/removal/energy-delta records emitted during a frame.

    Buffers are cleared at FRAME_START and drained by world backends after
    each update via :meth:`drain`.
    """

    def __init__(self) -> None:
        self.spawns: list[SpawnRequest] = []
        self.removals: list[RemovalRequest] = []
        self.energy_deltas: list[EnergyDeltaRecord] = []

    def clear(self) -> None:
        """Reset all per-frame buffers (called at FRAME_START)."""
        self.spawns.clear()
        self.removals.clear()
        self.energy_deltas.clear()

    def drain(self) -> FrameOutputs:
        """Return this frame's outputs and clear internal buffers."""
        outputs = FrameOutputs(
            spawns=list(self.spawns),
            removals=list(self.removals),
            energy_deltas=list(self.energy_deltas),
        )
        self.clear()
        return outputs

    def create_energy_recorder(
        self,
        get_identity: Callable[[Any], tuple[str, str]],
    ) -> Callable[[Any, float, str, dict[str, Any]], None]:
        """Create a recorder callback for energy delta tracking.

        Returns a function that can be passed to
        environment.set_energy_delta_recorder(). The recorder forwards energy
        deltas into this aggregator, resolving stable IDs via ``get_identity``.
        """
        # Deferred (load-bearing): importing core.worlds runs the registry's
        # eager mode registration, which pulls world backends -> core.simulation.
        # Keep this inside the function to avoid that import-time cycle (ADR-008).
        from core.worlds.contracts import EnergyDeltaRecord

        def recorder(entity: Any, delta: float, source: str, meta: dict[str, Any]) -> None:
            entity_type, stable_id = get_identity(entity)
            record = EnergyDeltaRecord(
                entity_id=stable_id,
                stable_id=stable_id,
                entity_type=entity_type,
                delta=delta,
                source=source,
                metadata=meta or {},
            )
            self.energy_deltas.append(record)

        return recorder
