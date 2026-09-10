"""The determinism gate must name where two runs parted company.

docs/IMPROVEMENT_PROPOSALS.md 1.0 sets the bar: earliest divergent frame,
phase, entity, RNG stream and state field. A gate that only says "the digests
differ" costs the next agent a multi-day bisect, so each of those five is
pinned here against a divergence whose cause is known by construction.
"""

import copy
import json

from core.replay.fingerprint_diff import compare_fingerprint_streams, format_divergence_report
from core.simulation.pipeline import FRAME_ENTRY_STEP


def _checkpoint(frame, *, entities, rng, phases=None):
    """Build one checkpoint record by hand, digests included.

    Written literally rather than through the recorder so a test failure points
    at the comparison logic instead of at whatever the simulation did today.
    """

    def digest(value):
        return f"d{abs(hash(json.dumps(value, sort_keys=True))) % 10**12:012d}"

    types = sorted({entity["type"] for entity in entities})
    parts = {
        "snapshot": digest(entities),
        "world": digest("world"),
        "entities": digest(entities),
        "entity_types": {
            name: digest([e for e in entities if e["type"] == name]) for name in types
        },
        "entities_by_id": {str(entity["id"]): digest(entity) for entity in entities},
        "fields": {
            name: {
                field: digest([e.get(field) for e in entities if e["type"] == name])
                for field in sorted({k for e in entities if e["type"] == name for k in e})
            }
            for name in types
        },
    }
    record = {
        "type": "checkpoint",
        "frame": frame,
        # Separate copies: the two precisions are independently editable in
        # these tests, and sharing one dict would make a delete hit both.
        "exact": copy.deepcopy(parts),
        "rounded": copy.deepcopy(parts),
        "entity_counts": {name: sum(e["type"] == name for e in entities) for name in types},
        "rng": rng,
    }
    if phases is not None:
        record["phases"] = phases
    return record


def _write(path, records, environment=None):
    header = {
        "type": "header",
        "version": 2,
        "benchmark_id": "test/fake",
        "seed": 42,
        "interval": 1,
        "environment": environment or {"machine": "x86_64"},
    }
    lines = [json.dumps(header)] + [json.dumps(record) for record in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


FISH_A = {"id": 1, "type": "fish", "energy": 10.0, "x": 5.0}
FISH_B = {"id": 2, "type": "fish", "energy": 20.0, "x": 6.0}


def test_report_names_the_entity_and_field_that_changed(tmp_path):
    left, right = tmp_path / "l.jsonl", tmp_path / "r.jsonl"
    rng = {"world": "aaaa"}
    _write(left, [_checkpoint(10, entities=[FISH_A, FISH_B], rng=rng)])
    _write(
        right,
        [_checkpoint(10, entities=[FISH_A, {**FISH_B, "energy": 20.5}], rng=rng)],
    )

    divergence = compare_fingerprint_streams(left, right)["rounded"]

    assert divergence["frame"] == 10
    assert divergence["entities_detail"]["changed"] == ["2"]
    assert divergence["fields"]["fish"] == ["energy"]


def test_matching_rng_states_are_reported_as_float_drift(tmp_path):
    """Same draws, different numbers: an arithmetic problem, not a logic one."""
    left, right = tmp_path / "l.jsonl", tmp_path / "r.jsonl"
    rng = {"world": "aaaa"}
    _write(left, [_checkpoint(10, entities=[FISH_A], rng=rng)])
    _write(right, [_checkpoint(10, entities=[{**FISH_A, "x": 5.5}], rng=rng)])

    divergence = compare_fingerprint_streams(left, right)["rounded"]

    assert divergence["rng"]["verdict"] == "float_drift"
    assert divergence["rng"]["diverged"] == []


def test_differing_rng_states_are_reported_as_desync(tmp_path):
    """Different draws: a branch went the other way; float noise is a red herring."""
    left, right = tmp_path / "l.jsonl", tmp_path / "r.jsonl"
    _write(left, [_checkpoint(10, entities=[FISH_A], rng={"world": "aaaa"})])
    _write(right, [_checkpoint(10, entities=[{**FISH_A, "x": 5.5}], rng={"world": "bbbb"})])

    comparison = compare_fingerprint_streams(left, right)

    assert comparison["rounded"]["rng"]["verdict"] == "rng_desync"
    assert comparison["rounded"]["rng"]["diverged"] == ["world"]
    assert comparison["first_rng_divergence_frame"] == 10


def test_rng_divergence_earlier_than_the_snapshot_is_surfaced(tmp_path):
    """The RNG can desync before the effect reaches the snapshot - say so."""
    left, right = tmp_path / "l.jsonl", tmp_path / "r.jsonl"
    _write(
        left,
        [
            _checkpoint(10, entities=[FISH_A], rng={"world": "aaaa"}),
            _checkpoint(20, entities=[FISH_A], rng={"world": "aaaa"}),
        ],
    )
    _write(
        right,
        [
            _checkpoint(10, entities=[FISH_A], rng={"world": "bbbb"}),
            _checkpoint(20, entities=[{**FISH_A, "x": 9.0}], rng={"world": "bbbb"}),
        ],
    )

    comparison = compare_fingerprint_streams(left, right)

    assert comparison["first_rng_divergence_frame"] == 10
    divergence = comparison["rounded"]
    assert divergence["frame"] == 20
    assert divergence["rng"]["first_rng_divergence_frame"] == 10
    assert "frame 10" in divergence["rng"]["note"]


def test_phase_is_named_when_a_step_introduces_the_difference(tmp_path):
    left, right = tmp_path / "l.jsonl", tmp_path / "r.jsonl"
    rng = {"world": "aaaa"}
    shared = [
        {"step": FRAME_ENTRY_STEP, "exact": "same", "rounded": "same"},
        {"step": "frame_start", "exact": "same", "rounded": "same"},
    ]
    _write(
        left,
        [
            _checkpoint(
                10,
                entities=[FISH_A],
                rng=rng,
                phases=[*shared, {"step": "entity_act", "exact": "L", "rounded": "L"}],
            )
        ],
    )
    _write(
        right,
        [
            _checkpoint(
                10,
                entities=[{**FISH_A, "x": 5.5}],
                rng=rng,
                phases=[*shared, {"step": "entity_act", "exact": "R", "rounded": "R"}],
            )
        ],
    )

    divergence = compare_fingerprint_streams(left, right)["rounded"]

    assert divergence["phase"] == "entity_act"
    assert divergence["phase_source"] == "step_digests"


def test_a_difference_present_at_frame_entry_is_not_blamed_on_a_phase(tmp_path):
    """Otherwise the first step is always the suspect and never the culprit."""
    left, right = tmp_path / "l.jsonl", tmp_path / "r.jsonl"
    rng = {"world": "aaaa"}
    _write(
        left,
        [
            _checkpoint(
                10,
                entities=[FISH_A],
                rng=rng,
                phases=[{"step": FRAME_ENTRY_STEP, "exact": "L", "rounded": "L"}],
            )
        ],
    )
    _write(
        right,
        [
            _checkpoint(
                10,
                entities=[{**FISH_A, "x": 5.5}],
                rng=rng,
                phases=[{"step": FRAME_ENTRY_STEP, "exact": "R", "rounded": "R"}],
            )
        ],
    )

    divergence = compare_fingerprint_streams(left, right)["rounded"]

    assert divergence["phase"] is None
    assert divergence["phase_source"] == "carried_in_from_earlier_frame"
    assert "--fingerprint-every 1" in divergence["phase_hint"]


def test_version_1_streams_still_compare(tmp_path):
    """Old CI artifacts predate these fields; degrade rather than crash."""
    left, right = tmp_path / "l.jsonl", tmp_path / "r.jsonl"
    for path, entities in ((left, [FISH_A]), (right, [{**FISH_A, "x": 5.5}])):
        record = _checkpoint(10, entities=entities, rng={})
        del record["rng"]
        for precision in ("exact", "rounded"):
            del record[precision]["entities_by_id"]
            del record[precision]["fields"]
        _write(path, [record])

    divergence = compare_fingerprint_streams(left, right)["rounded"]

    assert divergence["frame"] == 10
    assert divergence["rng"]["verdict"] == "unknown"
    assert divergence["phase_source"] == "unavailable"
    assert "entities_detail" not in divergence
    assert "fields" not in divergence


def test_environment_differences_are_reported(tmp_path):
    left, right = tmp_path / "l.jsonl", tmp_path / "r.jsonl"
    rng = {"world": "aaaa"}
    _write(left, [_checkpoint(10, entities=[FISH_A], rng=rng)], environment={"machine": "x86_64"})
    _write(right, [_checkpoint(10, entities=[FISH_A], rng=rng)], environment={"machine": "arm64"})

    comparison = compare_fingerprint_streams(left, right)

    assert comparison["environment_delta"]["machine"] == {"left": "x86_64", "right": "arm64"}
    assert "arm64" in format_divergence_report(comparison)


def test_identical_streams_report_no_divergence(tmp_path):
    left, right = tmp_path / "l.jsonl", tmp_path / "r.jsonl"
    rng = {"world": "aaaa"}
    for path in (left, right):
        _write(path, [_checkpoint(10, entities=[FISH_A, FISH_B], rng=rng)])

    comparison = compare_fingerprint_streams(left, right)

    assert comparison["exact"] is None
    assert comparison["rounded"] is None
    assert "identical" in format_divergence_report(comparison)
