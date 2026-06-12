import json
from pathlib import Path

from core.replay.fingerprint_stream import (
    FingerprintStreamRecorder,
    compare_fingerprint_streams,
)
from tools.run_bench import second_fingerprint_path


class FakeWorld:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def get_debug_snapshot(self):
        return self.snapshot


def _write_stream(path, snapshots):
    recorder = FingerprintStreamRecorder(path, benchmark_id="test/fake", seed=42, interval=10)
    world = FakeWorld({})
    for frame, snapshot in snapshots:
        world.snapshot = snapshot
        recorder.record(world, frame)
    recorder.finish({"score": 1.0, "metadata": {}})


def test_fingerprint_stream_records_periodic_component_hashes(tmp_path):
    path = tmp_path / "nested" / "stream.jsonl"
    _write_stream(
        path,
        [
            (0, {"frame": 0, "entities": [{"type": "fish", "x": 1.0}]}),
            (1, {"frame": 1, "entities": [{"type": "fish", "x": 2.0}]}),
            (10, {"frame": 10, "entities": [{"type": "fish", "x": 3.0}]}),
        ],
    )

    records = [json.loads(line) for line in path.read_text().splitlines()]
    checkpoints = [record for record in records if record["type"] == "checkpoint"]

    assert [record["frame"] for record in checkpoints] == [0, 10]
    assert checkpoints[0]["entity_counts"] == {"fish": 1}
    assert "fish" in checkpoints[0]["exact"]["entity_types"]


def test_compare_reports_exact_jitter_before_rounded_divergence(tmp_path):
    left = tmp_path / "left.jsonl"
    right = tmp_path / "right.jsonl"
    _write_stream(
        left,
        [
            (0, {"frame": 0, "entities": [{"type": "fish", "x": 1.00000001}]}),
            (10, {"frame": 10, "entities": [{"type": "fish", "x": 2.0}]}),
        ],
    )
    _write_stream(
        right,
        [
            (0, {"frame": 0, "entities": [{"type": "fish", "x": 1.00000002}]}),
            (10, {"frame": 10, "entities": [{"type": "fish", "x": 3.0}]}),
        ],
    )

    comparison = compare_fingerprint_streams(left, right)

    assert comparison["exact"]["frame"] == 0
    assert comparison["rounded"]["frame"] == 10
    assert comparison["rounded"]["differing_entity_types"] == ["fish"]


def test_second_fingerprint_path_preserves_jsonl_suffix():
    assert Path(second_fingerprint_path("results/run.jsonl")) == Path("results/run.run2.jsonl")


def test_compare_rejects_streams_without_checkpoints(tmp_path):
    left = tmp_path / "left.jsonl"
    right = tmp_path / "right.jsonl"
    left.write_text('{"type":"header"}\n')
    right.write_text('{"type":"header"}\n')

    comparison = compare_fingerprint_streams(left, right)

    assert comparison["exact"]["reason"] == "no_checkpoints"
    assert comparison["rounded"]["reason"] == "no_checkpoints"
