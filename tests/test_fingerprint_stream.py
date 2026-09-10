import json
from pathlib import Path

from core.replay.fingerprint import fingerprint_snapshot
from core.replay.fingerprint_stream import FingerprintStreamRecorder, compare_fingerprint_streams
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


def test_taxonomy_presentation_metadata_does_not_change_a_replay_fingerprint():
    baseline = {"frame": 1, "entities": [{"id": 7, "type": "fish", "x": 3.0}]}
    taxonomy_enriched = {
        "frame": 1,
        "entities": [
            {
                "id": 7,
                "type": "fish",
                "x": 3.0,
                "taxon_id": "taxon_7",
                "common_name": "Azure Sailfin",
                "scientific_name": "Synpinna caeruleus",
                "species_confidence": "established",
            }
        ],
    }

    assert fingerprint_snapshot(baseline) == fingerprint_snapshot(taxonomy_enriched)


def test_compare_rejects_streams_without_checkpoints(tmp_path):
    left = tmp_path / "left.jsonl"
    right = tmp_path / "right.jsonl"
    left.write_text('{"type":"header"}\n')
    right.write_text('{"type":"header"}\n')

    comparison = compare_fingerprint_streams(left, right)

    assert comparison["exact"]["reason"] == "no_checkpoints"
    assert comparison["rounded"]["reason"] == "no_checkpoints"


# --- Real-engine guards -----------------------------------------------------
#
# The fake world above cannot catch the two ways this recorder could actually
# hurt: perturbing the simulation it measures, or attributing a phase wrongly.


def _tiny_world(seed=42):
    from core.worlds.registry import WorldRegistry

    config = {"initial_fish_count": 4}
    world = WorldRegistry.create_world("tank", seed=seed, config=config)
    world.reset(seed=seed, config=config)
    return world


def _run(world, frames, callback=None):
    for index in range(frames):
        world.step({"fast_step": True})
        if callback is not None:
            callback(world, index + 1)
    return fingerprint_snapshot(world.get_debug_snapshot())


def test_recording_does_not_perturb_the_simulation(tmp_path):
    """The recorder observes a trajectory; it must never be part of one.

    Reading state and RNG must not consume draws or mutate anything, or the
    fingerprints would describe a run that only happens while being watched.
    """
    unwatched = _run(_tiny_world(), 40)

    recorder = FingerprintStreamRecorder(
        tmp_path / "watched.jsonl", benchmark_id="test/tiny", seed=42, interval=5
    )
    world = _tiny_world()
    recorder.record(world, 0)
    watched = _run(world, 40, recorder.record)
    recorder.finish({"score": 0.0, "metadata": {}})

    assert watched == unwatched


def test_phase_attribution_names_the_step_that_introduced_the_difference(tmp_path):
    """End-to-end: perturb inside one known phase, expect that phase named.

    This is the claim the gate rests on, so it is tested against the real
    pipeline rather than hand-written phase rows.
    """

    def stream(path, perturb_phase=None):
        recorder = FingerprintStreamRecorder(path, benchmark_id="test/tiny", seed=42, interval=1)
        world = _tiny_world()
        if perturb_phase is not None:
            engine = world.engine
            original = getattr(engine, perturb_phase)

            def perturbed(*args, **kwargs):
                result = original(*args, **kwargs)
                if engine.frame_count == 3:
                    for entity in engine.entities_list:
                        if type(entity).__name__ == "Fish":
                            entity.energy += 0.5
                            break
                return result

            setattr(engine, perturb_phase, perturbed)
        recorder.record(world, 0)
        _run(world, 5, recorder.record)
        recorder.finish({"score": 0.0, "metadata": {}})

    left = tmp_path / "left.jsonl"
    right = tmp_path / "right.jsonl"
    stream(left)
    stream(right, perturb_phase="_phase_environment")

    divergence = compare_fingerprint_streams(left, right)["rounded"]

    assert divergence["frame"] == 3
    assert divergence["phase"] == "environment"
    assert divergence["phase_source"] == "step_digests"
    assert divergence["rng"]["verdict"] == "float_drift"
    assert divergence["fields"]["fish"] == ["energy"]


def test_checkpoints_carry_the_five_part_identification(tmp_path):
    path = tmp_path / "stream.jsonl"
    recorder = FingerprintStreamRecorder(path, benchmark_id="test/tiny", seed=42, interval=2)
    world = _tiny_world()
    recorder.record(world, 0)
    _run(world, 4, recorder.record)
    recorder.finish({"score": 0.0, "metadata": {}})

    records = [json.loads(line) for line in path.read_text().splitlines()]
    checkpoint = [record for record in records if record["type"] == "checkpoint"][-1]

    assert checkpoint["rng"]["world"]
    steps = [row["step"] for row in checkpoint["phases"]]
    assert next(iter(steps)) == "frame_entry"
    assert "frame_start" in steps
    assert checkpoint["exact"]["entities_by_id"]
    assert "energy" in checkpoint["exact"]["fields"]["fish"]


def test_shared_rng_streams_are_reported_once(tmp_path):
    """Tank hands one Random to backend, engine and environment.

    Listing it three times would imply independent streams that do not exist,
    and would make a desync look three times worse than it is.
    """
    path = tmp_path / "stream.jsonl"
    recorder = FingerprintStreamRecorder(path, benchmark_id="test/tiny", seed=42, interval=1)
    world = _tiny_world()
    recorder.record(world, 0)
    recorder.finish({"score": 0.0, "metadata": {}})

    records = [json.loads(line) for line in path.read_text().splitlines()]
    rng = next(record for record in records if record["type"] == "checkpoint")["rng"]

    aliases = [name for name, value in rng.items() if str(value).startswith("same_as:")]
    assert aliases, "expected the shared Random to be reported as an alias"
    assert len([value for value in rng.values() if not str(value).startswith("same_as:")]) == 1


def test_closing_the_recorder_stops_observing_the_pipeline(tmp_path):
    recorder = FingerprintStreamRecorder(
        tmp_path / "stream.jsonl", benchmark_id="test/tiny", seed=42, interval=1
    )
    world = _tiny_world()
    recorder.record(world, 0)
    assert world.engine.pipeline._step_observer is not None

    recorder.close()

    assert world.engine.pipeline._step_observer is None
