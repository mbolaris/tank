"""Atomic, idempotent post-match reconciliation.

The match produces a settlement keyed by ``(fish_id, tank_id)`` provenance.
The resolver is supplied by the world/transfer layer and may locate a fish in
its current tank. A missing result is unresolved identity, not death.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Mapping, Sequence
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

    def __init__(self, results: Mapping[str, ReconciliationResult] | None = None) -> None:
        self._results: dict[str, ReconciliationResult] = dict(results or {})

    def get(self, reconciliation_id: str) -> ReconciliationResult | None:
        return self._results.get(reconciliation_id)

    def put(self, reconciliation_id: str, result: ReconciliationResult) -> None:
        self._results[reconciliation_id] = result

    def to_dict(self) -> dict[str, Any]:
        """Serialize applied IDs and results for world persistence."""
        return {
            "results": [
                {
                    "reconciliation_id": result.reconciliation_id,
                    "applied": result.applied,
                    "applied_energy_deltas": [
                        _identity_value(identity, amount)
                        for identity, amount in result.applied_energy_deltas.items()
                    ],
                    "applied_repro_credit_deltas": [
                        _identity_value(identity, amount)
                        for identity, amount in result.applied_repro_credit_deltas.items()
                    ],
                    "retained_statistics": [
                        {
                            "identity": _identity_dict(identity),
                            "values": dict(values),
                        }
                        for identity, values in result.retained_statistics.items()
                    ],
                    "dropped_dead_deltas": [
                        _identity_dict(identity) for identity in result.dropped_dead_deltas
                    ],
                }
                for result in self._results.values()
            ]
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> InMemoryReconciliationStore:
        results: dict[str, ReconciliationResult] = {}
        for item in (data or {}).get("results", []):
            if not isinstance(item, Mapping):
                continue
            energy = dict(_read_identity_values(item.get("applied_energy_deltas")))
            repro = dict(_read_identity_values(item.get("applied_repro_credit_deltas")))
            stats: dict[SourceIdentity, dict[str, int | float | str]] = {}
            for record in item.get("retained_statistics", []):
                if not isinstance(record, Mapping):
                    continue
                identity = _read_identity(record.get("identity"))
                values = record.get("values", {})
                if identity is not None and isinstance(values, Mapping):
                    stats[identity] = dict(values)
            dropped = tuple(
                identity
                for raw in item.get("dropped_dead_deltas", [])
                if (identity := _read_identity(raw)) is not None
            )
            reconciliation_id = str(item.get("reconciliation_id", ""))
            if reconciliation_id:
                results[reconciliation_id] = ReconciliationResult(
                    reconciliation_id=reconciliation_id,
                    applied=bool(item.get("applied", True)),
                    applied_energy_deltas=energy,
                    applied_repro_credit_deltas=repro,
                    retained_statistics=stats,
                    dropped_dead_deltas=dropped,
                )
        return cls(results)


def _identity_dict(identity: SourceIdentity) -> dict[str, Any]:
    return {"fish_id": identity.fish_id, "tank_id": identity.tank_id}


def _identity_value(identity: SourceIdentity, value: float) -> dict[str, Any]:
    return {"identity": _identity_dict(identity), "value": float(value)}


def _read_identity(value: Any) -> SourceIdentity | None:
    if not isinstance(value, Mapping) or "fish_id" not in value:
        return None
    return SourceIdentity(int(value["fish_id"]), value.get("tank_id"))


def _read_identity_values(value: Any) -> list[tuple[SourceIdentity, float]]:
    result: list[tuple[SourceIdentity, float]] = []
    for item in value or []:
        if not isinstance(item, Mapping):
            continue
        identity = _read_identity(item.get("identity"))
        if identity is not None:
            result.append((identity, float(item.get("value", 0.0))))
    return result


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


class EntityCollectionResolver:
    """Resolve current source entities from world-owned providers.

    Providers are callables that fetch fresh entities at reconciliation time;
    this resolver never stores fish objects or a selection-time map.
    """

    def __init__(self, providers: Sequence[Callable[[], Iterable[Any]]]) -> None:
        self._providers = tuple(providers)

    def resolve_fish(self, fish_id: int, tank_id: str | None = None) -> Any | None:
        matches: list[Any] = []
        for provider in self._providers:
            for entity in provider():
                if getattr(entity, "fish_id", None) != fish_id:
                    continue
                origin_tank_id = getattr(entity, "origin_tank_id", None)
                current_tank_id = getattr(entity, "tank_id", None)
                if tank_id is None or tank_id in (origin_tank_id, current_tank_id):
                    matches.append(entity)
        if not matches:
            return None
        if len(matches) == 1:
            return matches[0]
        exact_origin = [
            entity for entity in matches if getattr(entity, "origin_tank_id", None) == tank_id
        ]
        if len(exact_origin) == 1:
            return exact_origin[0]
        raise SourceResolutionUnavailableError(
            f"ambiguous live resolution for fish {fish_id!r} from tank {tank_id!r}"
        )


def build_world_source_resolver(world_state: Any) -> EntityCollectionResolver:
    """Build a fresh-entity resolver owned by the world orchestration layer.

    The returned object stores providers, never selection-time fish references.
    Each provider reads the current entity manager when reconciliation runs, so
    transfers between match start and full time remain resolvable.
    """

    environment = getattr(world_state, "environment", None)
    world_manager = getattr(environment, "world_manager", None)
    current_world_id = getattr(environment, "world_id", None)
    providers: list[Callable[[], Iterable[Any]]] = []

    def provider_for(instance: Any, is_current: bool) -> Iterable[Any]:
        runner = getattr(instance, "runner", None)
        engine = getattr(runner, "engine", None) if runner is not None else None
        if engine is None:
            engine = instance
        entity_manager = getattr(engine, "entity_manager", None)
        if entity_manager is None:
            entity_manager = getattr(engine, "_entity_manager", None)
        get_fish = getattr(entity_manager, "get_fish", None)
        if not callable(get_fish):
            return ()
        if is_current:
            return list(get_fish())
        lock = getattr(runner, "lock", None)
        if lock is None or not lock.acquire(blocking=False):
            return ()
        try:
            return list(get_fish())
        finally:
            lock.release()

    if world_manager is not None:
        for world_id, instance in world_manager.get_all_worlds().items():

            def read_world(
                instance: Any = instance,
                world_id: str = str(world_id),
            ) -> Iterable[Any]:
                return provider_for(instance, world_id == current_world_id)

            providers.append(read_world)
    else:
        providers.append(lambda: provider_for(world_state, True))
    return EntityCollectionResolver(providers)


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


def resolve_source(resolver: Any, identity: SourceIdentity) -> Any:
    """Resolve one identity for orchestration before reward calculation."""
    entity = _resolve(resolver, identity)
    if entity is None:
        raise SourceResolutionUnavailableError(
            f"could not resolve fish {identity.fish_id!r} after selection; transfer is not death"
        )
    return entity


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
    repro_undo: list[tuple[Any, float]] = []
    for identity, delta in settlement.repro_credit_deltas.items():
        entity = resolved[identity]
        if _is_dead(entity) or not delta:
            continue
        component = _repro_component(entity)
        original = getattr(component, "repro_credits", None) if component is not None else None
        if not isinstance(original, (int, float)):
            raise SourceResolutionUnavailableError(
                f"resolved fish {identity!r} has no rollback-capable reproduction credits"
            )
        repro_undo.append((component, float(original)))
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
        for component, original in reversed(repro_undo):
            try:
                component.repro_credits = original
            except Exception:
                pass
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
