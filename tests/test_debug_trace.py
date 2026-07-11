"""Tests for opt-in headless debug tracing."""

from __future__ import annotations

import json
from pathlib import Path

from core.simulation.debug_trace import DebugTraceCollector
from core.worlds.contracts import EnergyDeltaRecord, RemovalRequest, SpawnRequest
from core.worlds.interfaces import StepResult


def _step(frame: int) -> StepResult:
    return StepResult(
        snapshot={
            "frame": frame,
            "entities": [{"id": 7, "type": "fish", "x": 1.0, "y": 2.0}],
        },
        info={"frame": frame},
        energy_deltas=[
            EnergyDeltaRecord(
                entity_id="7", stable_id="7", entity_type="fish", delta=-1.5, source="metabolism"
            ),
            EnergyDeltaRecord(
                entity_id="8", stable_id="8", entity_type="fish", delta=4.0, source="food"
            ),
        ],
        spawns=[SpawnRequest(entity_type="fish", entity_id="7", reason="test")],
        removals=[RemovalRequest(entity_type="fish", entity_id="8", reason="test")],
        events=[
            {"type": "poker", "frame": frame, "data": {"frame": frame, "winner_id": 7}},
            {"type": "poker", "frame": frame - 1, "data": {"frame": frame - 1, "winner_id": 7}},
        ],
    )


def test_debug_trace_selects_frame_and_entity() -> None:
    tracer = DebugTraceCollector(seed=42, max_frames=3, debug_frame=2, debug_entity="7")
    tracer.record(_step(1))
    tracer.record(_step(2))
    tracer.record(_step(3))

    document = tracer.to_dict()
    assert document["summary"] == {
        "frames_recorded": 1,
        "energy_deltas": 1,
        "spawns": 1,
        "removals": 0,
        "events": 1,
    }
    assert document["frames"][0]["frame"] == 2
    assert document["frames"][0]["entities"] == [{"id": 7, "type": "fish", "x": 1.0, "y": 2.0}]


def test_debug_trace_writes_json(tmp_path: Path) -> None:
    output = tmp_path / "trace.json"
    tracer = DebugTraceCollector(seed=42, max_frames=1)
    tracer.record(_step(1))
    tracer.write(output)

    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["seed"] == 42
    assert document["frames"][0]["energy_deltas"][0]["entity_id"] == "7"
