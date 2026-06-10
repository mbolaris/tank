"""Mutation application - drains the queued entity mutations at commit points.

Extracted from SimulationEngine so the mutation commit step is an
individually testable unit. The executor owns no queue itself; it commits the
engine's MutationTransaction into the EntityManager, recording frame outputs
into the FrameAggregator using the identity provider for stable IDs.

The engine's ``_apply_entity_mutations()`` delegates here and remains the
single commit point between phases (tests monkeypatch that engine method, so
phase implementations must keep routing through the engine).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.simulation.entity_manager import EntityManager
    from core.simulation.frame_aggregator import FrameAggregator
    from core.simulation.mutation import MutationTransaction


class MutationExecutor:
    """Applies queued spawns/removals at safe points in the frame."""

    def __init__(
        self,
        transaction: MutationTransaction,
        entity_manager: EntityManager,
        aggregator: FrameAggregator,
        pre_add_callback: Callable[[Any], Any] | None = None,
    ) -> None:
        """Initialize the executor.

        Args:
            transaction: The mutation queue facade to commit from.
            entity_manager: The manager mutations are applied to.
            aggregator: Frame output buffers for recording spawn/removal requests.
            pre_add_callback: Optional callback(entity) run before adding an
                entity to the manager (used for legacy add_internal support).
        """
        self._transaction = transaction
        self._entity_manager = entity_manager
        self._aggregator = aggregator
        self._pre_add_callback = pre_add_callback

    @property
    def transaction(self) -> MutationTransaction:
        """The underlying mutation transaction (queue facade)."""
        return self._transaction

    def apply(
        self,
        stage: str,
        *,
        identity_provider: Any | None,
        record_outputs: bool = True,
    ) -> None:
        """Commit pending mutations, optionally recording frame outputs.

        Args:
            stage: Label of the commit point (e.g. "collision", "frame_start").
            identity_provider: Provider used to resolve stable entity IDs.
            record_outputs: When True, record SpawnRequest/RemovalRequest
                entries into the frame aggregator buffers.
        """
        self._transaction.commit(
            self._entity_manager,
            self._aggregator.spawns if record_outputs else None,
            self._aggregator.removals if record_outputs else None,
            identity_provider,
            pre_add_callback=self._pre_add_callback,
        )
