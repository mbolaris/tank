"""Atomic, idempotent post-match reconciliation.

The match produces a settlement keyed by ``(fish_id, tank_id)`` provenance.
The resolver is supplied by the world/transfer layer and may locate a fish in
its current tank. A missing result is unresolved identity, not death.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class SourceIdentity:
    fish_id: int
    tank_id: str | None = None


@dataclass(frozen=True)
class SoccerSettlement:
    reconciliation_id: str
    match_id: str
    entry_fees: dict[SourceIdentity, float] = field(default_factory=dict)
    energy_deltas: dict[SourceIdentity, float] = field(default_factory=dict)
    repro_credit_deltas: dict[SourceIdentity, float] = field(default_factory=dict)
    statistics: dict[SourceIdentity, dict[str, int | float | str]] = field(default_factory=dict)
    energy_source: str = "soccer_reconciliation"

    @classmethod
    def for_match(
        cls,
        match_id: str,
        *,
        entry_fees: Mapping[SourceIdentity, float] | None = None,
        energy_deltas: Mapping[SourceIdentity, float] | None = None,
        repro_credit_deltas: Mapping[SourceIdentity, float] | None = None,
        statistics: Mapping[SourceIdentity, Mapping[str, int | float | str]] | None = None,
        energy_source: str = "soccer_reconciliation",
    ) -> SoccerSettlement:
        body = {
            "match_id": match_id,
            "entry_fees": sorted(
                (i.fish_id, i.tank_id, float(v)) for i, v in (entry_fees or {}).items()
            ),
            "energy_deltas": sorted(
                (i.fish_id, i.tank_id, float(v)) for i, v in (energy_deltas or {}).items()
            ),
            "repro_credit_deltas": sorted(
                (i.fish_id, i.tank_id, float(v)) for i, v in (repro_credit_deltas or {}).items()
            ),
            "statistics": sorted(
                (i.fish_id, i.tank_id, sorted(values.items()))
                for i, values in (statistics or {}).items()
            ),
        }
        digest = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:24]
        return cls(
            reconciliation_id=f"{match_id}:reconcile:{digest}",
            match_id=match_id,
            entry_fees=dict(entry_fees or {}),
            energy_deltas=dict(energy_deltas or {}),
            repro_credit_deltas={**(repro_credit_deltas or {})},
            statistics={identity: dict(values) for identity, values in (statistics or {}).items()},
            energy_source=energy_source,
        )


class ReconciliationStore(Protocol):
    def get(self, reconciliation_id: str) -> ReconciliationResult | None: ...

    def put(self, reconciliation_id: str, result: ReconciliationResult) -> None: ...


class InMemoryReconciliationStore:
    """Small store useful for a world event manager or deterministic tests."""

    def __init__(self) -> None:
        self._results: dict[str, ReconciliationResult] = {}

    def get(self, reconciliation_id: str) -> ReconciliationResult | None:
        return self._results.get(reconciliation_id)

    def put(self, reconciliation_id: str, result: ReconciliationResult) -> None:
        self._results[reconciliation_id] = result


_DEFAULT_STORE = InMemoryReconciliationStore()


class SourceResolutionUnavailableError(RuntimeError):
    """The world could not resolve stable fish identity across tanks."""


# Compatibility spelling for callers that imported the contract name before
# the project lint convention required ``Error`` suffixes.
SourceResolutionUnavailable = SourceResolutionUnavailableError


@dataclass(frozen=True)
class ReconciliationResult:
    reconciliation_id: str
    applied: bool
    applied_energy_deltas: dict[SourceIdentity, float]
    applied_repro_credit_deltas: dict[SourceIdentity, float]
    retained_statistics: dict[SourceIdentity, dict[str, int | float | str]]
    dropped_dead_deltas: tuple[SourceIdentity, ...] = ()


def _resolve(resolver: Any, identity: SourceIdentity) -> Any:
    if resolver is None:
        raise SourceResolutionUnavailableError(
            "soccer reconciliation requires a stable cross-world source resolver; "
            "fish_id/tank_id alone cannot identify a live object"
        )
    if callable(resolver):
        return resolver(identity.fish_id, identity.tank_id)
    for name in ("resolve_fish", "resolve_source", "find_fish_by_identity", "get_fish_by_identity"):
        method = getattr(resolver, name, None)
        if callable(method):
            return method(identity.fish_id, identity.tank_id)
    if isinstance(resolver, Mapping):
        return resolver.get((identity.fish_id, identity.tank_id))
    raise SourceResolutionUnavailableError(
        "resolver does not expose stable cross-world fish lookup"
    )


def _is_dead(entity: Any) -> bool:
    method = getattr(entity, "is_dead", None)
    if callable(method):
        return bool(method())
    if hasattr(entity, "dead"):
        return bool(entity.dead)
    if hasattr(entity, "alive"):
        return not bool(entity.alive)
    return False


def _repro_component(entity: Any) -> Any | None:
    return getattr(entity, "reproduction_component", None) or getattr(
        entity, "_reproduction_component", None
    )


def reconcile_match(
    settlement: SoccerSettlement,
    resolver: Any,
    *,
    store: ReconciliationStore | None = None,
) -> ReconciliationResult:
    """Apply one complete settlement batch exactly once.

    All identities are resolved and capabilities checked before the first
    mutation. A rollback is attempted if a mutation unexpectedly fails.
    """
    # The default is process-persistent; production worlds can inject a
    # durable store, while retries in one process remain idempotent too.
    store = store or _DEFAULT_STORE
    previous = store.get(settlement.reconciliation_id)
    if previous is not None:
        return previous

    identities = (
        set(settlement.energy_deltas)
        | set(settlement.repro_credit_deltas)
        | set(settlement.statistics)
    )
    resolved = {identity: _resolve(resolver, identity) for identity in identities}
    if any(entity is None for entity in resolved.values()):
        missing = next(identity for identity, entity in resolved.items() if entity is None)
        raise SourceResolutionUnavailableError(
            f"could not resolve fish {missing.fish_id!r} after selection; transfer is not death"
        )

    # Validate all mutation capabilities before changing any entity.
    for identity, delta in settlement.energy_deltas.items():
        if (
            not _is_dead(resolved[identity])
            and delta
            and not hasattr(resolved[identity], "modify_energy")
        ):
            raise SourceResolutionUnavailableError(
                f"resolved fish {identity!r} cannot accept energy settlement"
            )
    for identity, delta in settlement.repro_credit_deltas.items():
        if not _is_dead(resolved[identity]) and delta:
            component = _repro_component(resolved[identity])
            if component is None or not hasattr(component, "add_repro_credits"):
                raise SourceResolutionUnavailableError(
                    f"resolved fish {identity!r} cannot accept reproduction credits"
                )

    applied_energy: dict[SourceIdentity, float] = {}
    applied_repro: dict[SourceIdentity, float] = {}
    dropped: list[SourceIdentity] = []
    undo: list[tuple[Any, float, str]] = []
    try:
        for identity, delta in settlement.energy_deltas.items():
            entity = resolved[identity]
            if _is_dead(entity):
                dropped.append(identity)
                continue
            amount = float(entity.modify_energy(delta, source=settlement.energy_source))
            applied_energy[identity] = amount
            undo.append((entity, amount, "soccer_reconciliation_rollback"))
        for identity, delta in settlement.repro_credit_deltas.items():
            entity = resolved[identity]
            if _is_dead(entity):
                if identity not in dropped:
                    dropped.append(identity)
                continue
            component = _repro_component(entity)
            if component is None:
                raise SourceResolutionUnavailableError(
                    f"resolved fish {identity!r} cannot accept reproduction credits"
                )
            amount = float(component.add_repro_credits(delta))
            applied_repro[identity] = amount
    except Exception:
        for entity, amount, source in reversed(undo):
            try:
                entity.modify_energy(-amount, source=source)
            except Exception:
                pass
        raise

    result = ReconciliationResult(
        reconciliation_id=settlement.reconciliation_id,
        applied=True,
        applied_energy_deltas=applied_energy,
        applied_repro_credit_deltas=applied_repro,
        retained_statistics={
            identity: dict(values) for identity, values in settlement.statistics.items()
        },
        dropped_dead_deltas=tuple(dropped),
    )
    store.put(settlement.reconciliation_id, result)
    return result
