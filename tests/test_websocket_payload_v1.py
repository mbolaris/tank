"""Guardrail tests for WorldUpdateV1 payload schema.

These tests ensure:
1. All world types return payloads with required V1 keys
2. Frontend types don't regress to legacy patterns
3. Payload structure is consistent across tank/petri
"""

import json
from pathlib import Path


def test_no_legacy_comments_in_frontend_types():
    """Ensure frontend types don't have 'Legacy fields' comments."""
    root_dir = Path(__file__).parent.parent
    types_file = root_dir / "frontend" / "src" / "types" / "simulation.ts"

    if not types_file.exists():
        # Skip if frontend not present (CI may not have it)
        return

    content = types_file.read_text(encoding="utf-8")

    forbidden_patterns = [
        "// Legacy fields",
        "// legacy fields",
        "Legacy fields (optional)",
    ]

    violations = []
    for pattern in forbidden_patterns:
        if pattern in content:
            violations.append(f"Found '{pattern}' in simulation.ts")

    assert not violations, "Legacy patterns found in frontend types:\n" + "\n".join(violations)


def test_tank_payload_has_required_v1_keys():
    """Tank world payload should have required V1 schema keys."""
    from backend.simulation_runner import SimulationRunner

    runner = SimulationRunner(world_type="tank", seed=42)
    runner.world.step()

    state = runner.get_state(force_full=True)
    payload = state.to_dict()

    # V1 required top-level keys
    assert "type" in payload, "Payload must have 'type' key"
    assert payload["type"] == "update", "Full state must have type='update'"
    assert "snapshot" in payload, "Payload must have 'snapshot' key"

    # V1 required snapshot keys
    snapshot = payload["snapshot"]
    assert "frame" in snapshot, "Snapshot must have 'frame'"
    assert "elapsed_time" in snapshot, "Snapshot must have 'elapsed_time'"
    assert "entities" in snapshot, "Snapshot must have 'entities'"
    assert "stats" in snapshot, "Snapshot must have 'stats'"
    assert "soccer_events" in snapshot, "Snapshot must have 'soccer_events'"
    assert "soccer_league_live" in snapshot, "Snapshot must have 'soccer_league_live'"


def test_petri_payload_has_required_v1_keys():
    """Petri world payload should have required V1 schema keys."""
    from backend.simulation_runner import SimulationRunner

    runner = SimulationRunner(world_type="petri", seed=42)
    runner.world.step()

    state = runner.get_state(force_full=True)
    payload = state.to_dict()

    # V1 required keys
    assert "type" in payload
    assert "snapshot" in payload
    assert payload["snapshot"]["frame"] == 1


def test_delta_payload_has_required_v1_keys():
    """Delta payload should have required V1 schema keys."""
    from backend.simulation_runner import SimulationRunner

    runner = SimulationRunner(world_type="tank", seed=42)

    # Get full state first
    runner.world.step()
    runner.get_state(force_full=True)

    # Advance past delta sync interval and get delta
    for _ in range(5):
        runner.world.step()

    delta = runner.get_state(force_full=False, allow_delta=True)
    payload = delta.to_dict()

    # Delta V1 required keys
    assert "type" in payload
    assert payload["type"] == "delta"
    assert "snapshot" in payload

    snapshot = payload["snapshot"]
    assert "frame" in snapshot
    assert "updates" in snapshot
    assert "added" in snapshot
    assert "removed" in snapshot


def test_payload_serialization_produces_valid_json():
    """Payload to_json should produce valid JSON."""
    from backend.simulation_runner import SimulationRunner

    runner = SimulationRunner(world_type="tank", seed=42)
    runner.world.step()

    state = runner.get_state(force_full=True)
    json_str = state.to_json()

    # Should be valid JSON
    parsed = json.loads(json_str)
    assert "snapshot" in parsed
    assert isinstance(parsed["snapshot"]["entities"], list)
