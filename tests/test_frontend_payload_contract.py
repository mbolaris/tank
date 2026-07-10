"""Guard the simulation wire schema against frontend TypeScript drift.

The backend owns the serialized payload. This test parses the exported frontend
interfaces and checks that every key emitted by the backend DTOs has a declared
frontend field. It deliberately checks field presence rather than duplicating
TypeScript's type checker; ``npm run build`` remains responsible for TS syntax
and assignability.
"""

from __future__ import annotations

import re
from dataclasses import fields
from pathlib import Path
from typing import Any

from backend.state_payloads import (
    AutoEvaluateStatsPayload,
    EntitySnapshot,
    MetricsHistoryPayload,
    MetricsPokerSamplePayload,
    MetricsSamplePayload,
    MetricsSoccerSamplePayload,
    PokerEventPayload,
    PokerLeaderboardEntryPayload,
    PokerStatsPayload,
    SoccerEventPayload,
    StatsPayload,
)


TYPE_SOURCES = (
    Path(__file__).resolve().parents[1] / "frontend" / "src" / "types" / "simulation.ts",
    Path(__file__).resolve().parents[1] / "frontend" / "src" / "types" / "payload.ts",
)


def _type_source() -> str:
    """Load the frontend's simulation and dedicated wire-payload contracts."""
    return "\n".join(path.read_text(encoding="utf-8") for path in TYPE_SOURCES)


def _interface_keys(source: str, interface_name: str) -> set[str]:
    """Return the direct property names declared by one TypeScript interface."""
    match = re.search(rf"export interface {re.escape(interface_name)}\s*{{", source)
    assert match is not None, f"Frontend interface '{interface_name}' is missing"

    depth = 0
    end = None
    for index in range(match.end() - 1, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                end = index
                break
    assert end is not None, f"Frontend interface '{interface_name}' is unterminated"

    body = source[match.end() : end]
    return set(re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\??\s*:", body, re.MULTILINE))


def _assert_declares(interface_name: str, backend_keys: set[str], source: str) -> None:
    missing = backend_keys - _interface_keys(source, interface_name)
    assert not missing, f"{interface_name} is missing backend payload keys: {sorted(missing)}"


def _dataclass_keys(payload_type: type[Any], excluded: set[str] | None = None) -> set[str]:
    excluded = excluded or set()
    return {field.name for field in fields(payload_type)} - excluded


def test_full_and_delta_payloads_match_named_frontend_snapshots() -> None:
    """Representative production payloads use only declared frontend keys."""
    from backend.simulation_runner import SimulationRunner

    source = _type_source()
    runner = SimulationRunner(world_type="tank", seed=42)
    runner.world.step()

    full_payload = runner.get_state(force_full=True).to_dict()
    _assert_declares("SimulationUpdate", set(full_payload), source)
    _assert_declares("FullStateSnapshot", set(full_payload["snapshot"]), source)

    for _ in range(5):
        runner.world.step()
    delta_payload = runner.get_state(force_full=False, allow_delta=True).to_dict()
    _assert_declares("DeltaUpdate", set(delta_payload), source)
    _assert_declares("DeltaStateSnapshot", set(delta_payload["snapshot"]), source)


def test_every_backend_dto_field_has_a_frontend_declaration() -> None:
    """DTO additions cannot silently bypass the web-client contract."""
    source = _type_source()

    contracts = {
        "EntityData": _dataclass_keys(EntitySnapshot),
        "DeltaEntityUpdate": set(EntitySnapshot(1, "fish", 0, 0, 1, 1).to_delta_dict()),
        "StatsData": _dataclass_keys(StatsPayload, {"meta_stats"}),
        "PokerStatsData": _dataclass_keys(PokerStatsPayload),
        "PokerEventData": _dataclass_keys(PokerEventPayload),
        "SoccerEventData": _dataclass_keys(SoccerEventPayload),
        "PokerLeaderboardEntry": _dataclass_keys(PokerLeaderboardEntryPayload),
        "AutoEvaluateStats": _dataclass_keys(AutoEvaluateStatsPayload),
        "MetricsPokerSample": _dataclass_keys(MetricsPokerSamplePayload),
        "MetricsSoccerSample": _dataclass_keys(MetricsSoccerSamplePayload),
        "MetricsSample": _dataclass_keys(MetricsSamplePayload),
        "MetricsHistory": _dataclass_keys(MetricsHistoryPayload),
    }

    for interface_name, backend_keys in contracts.items():
        _assert_declares(interface_name, backend_keys, source)
