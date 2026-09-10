"""Record periodic, attributable fingerprints of a benchmark run.

A determinism gate that only reports "the digests differ" hands the next agent
a multi-day bisect (see docs/IMPROVEMENT_PROPOSALS.md 1.0, which cost exactly
that once). So each checkpoint carries enough structure to name *where* two
runs parted company:

* **frame** - the checkpoint's frame number.
* **phase** - a digest after every pipeline step, so the divergence lands on
  ``entity_act`` rather than merely "somewhere in frame 4200".
* **entity** - a digest per entity id, so the report names the fish.
* **state field** - a digest per (entity type, field), so it names ``energy``.
* **RNG stream** - a digest of each live ``random.Random`` state, which is the
  discriminator that matters most: identical RNG states with differing
  snapshots means float arithmetic drifted, while differing RNG states mean a
  decision changed and the draw schedules desynchronised.

Everything here is read-only with respect to the simulation. Recording runs
inside the loop it measures, so a recorder that consumed RNG or mutated state
would change the trajectory it exists to describe.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import random
import sys
from collections import defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TextIO, runtime_checkable

from core.replay.fingerprint import SnapshotFingerprinter
from core.replay.fingerprint_diff import compare_fingerprint_streams
from core.simulation.pipeline import FRAME_ENTRY_STEP

if TYPE_CHECKING:
    from core.simulation.engine import SimulationEngine

# v1 recorded only whole-snapshot, whole-world and per-entity-type digests.
# v2 adds per-entity, per-field, per-phase and RNG-state digests. The
# comparison layer reads both, so v1 artifacts from older CI runs stay usable.
FINGERPRINT_STREAM_VERSION = 2

# Detail maps carry one digest per entity and per field, so they dominate the
# artifact's size. Eight bytes is ample to tell two states apart at this
# cardinality (~10^4 entries per run) while halving the bytes on disk.
DETAIL_DIGEST_SIZE = 8

__all__ = [
    "DETAIL_DIGEST_SIZE",
    "FINGERPRINT_STREAM_VERSION",
    "FingerprintStreamRecorder",
    "compare_fingerprint_streams",
]


# The recorder is deliberately world-agnostic - tank, petri and the test
# doubles all pass through it - so what it needs is stated as protocols and
# checked with isinstance, rather than probed with getattr. Each one is the
# minimum surface for one question the checkpoint has to answer.


@runtime_checkable
class _SupportsDebugSnapshot(Protocol):
    def get_debug_snapshot(self) -> Mapping[str, object]: ...


@runtime_checkable
class _SupportsCurrentSnapshot(Protocol):
    def get_current_snapshot(self) -> Mapping[str, object]: ...


@runtime_checkable
class _HasRandom(Protocol):
    rng: random.Random


@runtime_checkable
class _HasEngine(Protocol):
    engine: object


@runtime_checkable
class _HasEnvironment(Protocol):
    environment: object


@runtime_checkable
class _HasPipeline(Protocol):
    pipeline: object


@runtime_checkable
class _ObservablePipeline(Protocol):
    def set_step_observer(self, observer: object) -> None: ...


def _snapshot_for_fingerprint(world: object) -> dict[str, object]:
    if isinstance(world, _SupportsDebugSnapshot):
        return dict(world.get_debug_snapshot())
    if isinstance(world, _SupportsCurrentSnapshot):
        return dict(world.get_current_snapshot())
    return {}


def _environment_manifest() -> dict[str, object]:
    environment_keys = (
        "GLIBC_TUNABLES",
        "GITHUB_RUN_ATTEMPT",
        "GITHUB_RUN_ID",
        "PYTHONHASHSEED",
        "RUNNER_ARCH",
        "RUNNER_NAME",
        "RUNNER_OS",
    )
    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "libc": platform.libc_ver(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "environment": {key: os.environ[key] for key in environment_keys if key in os.environ},
    }


def _entity_groups(snapshot: Mapping[str, object]) -> dict[str, list[object]]:
    groups: dict[str, list[object]] = defaultdict(list)
    entities = snapshot.get("entities", [])
    if not isinstance(entities, list):
        return {}
    for entity in entities:
        entity_type = "unknown"
        if isinstance(entity, Mapping):
            entity_type = str(entity.get("type", "unknown"))
        groups[entity_type].append(entity)
    return dict(sorted(groups.items()))


def _detail_fingerprinter(float_precision: int | None) -> SnapshotFingerprinter:
    return SnapshotFingerprinter(digest_size=DETAIL_DIGEST_SIZE, float_precision=float_precision)


def _entity_key(entity: Mapping[str, object], index: int) -> str:
    """Stable identity for one entity in the snapshot.

    Prefers the simulation's own id so the report names the fish a maintainer
    can look up. Entities without one fall back to a positional key, which is
    still comparable between two runs of the same seed.
    """
    entity_id = entity.get("id")
    if entity_id is None:
        return f"#{index}"
    return str(entity_id)


def _entity_digests(entities: list[object], fingerprinter: SnapshotFingerprinter) -> dict[str, str]:
    digests: dict[str, str] = {}
    for index, entity in enumerate(entities):
        if not isinstance(entity, Mapping):
            continue
        digests[_entity_key(entity, index)] = fingerprinter.fingerprint({"entity": entity})
    return digests


def _field_digests(
    entity_groups: dict[str, list[object]], fingerprinter: SnapshotFingerprinter
) -> dict[str, dict[str, str]]:
    """Digest each field across all entities of a type.

    Keyed by (type, field) rather than (entity, field): the cardinality stays
    proportional to the schema instead of the population, which is what keeps
    the artifact small enough to upload while still naming ``energy``.
    Non-deterministic keys are skipped because the canonicalizer drops them
    anyway - listing them would only ever be a false lead.
    """
    skip = fingerprinter.non_deterministic_keys
    fields: dict[str, dict[str, str]] = {}
    for entity_type, entities in entity_groups.items():
        names: set[str] = set()
        for entity in entities:
            if isinstance(entity, Mapping):
                names.update(str(name) for name in entity)
        per_field: dict[str, str] = {}
        for name in sorted(names - set(skip)):
            column = [
                {
                    "id": _entity_key(entity, index),
                    "value": entity.get(name),
                }
                for index, entity in enumerate(entities)
                if isinstance(entity, Mapping) and name in entity
            ]
            per_field[name] = fingerprinter.fingerprint({"column": column})
        fields[entity_type] = per_field
    return fields


def _digest_state(state: object) -> str:
    payload = repr(state).encode("utf-8")
    return hashlib.blake2b(payload, digest_size=DETAIL_DIGEST_SIZE).hexdigest()


def _rng_digests(world: object) -> dict[str, str]:
    """Digest every distinct ``random.Random`` the world exposes.

    Reads ``getstate()``, which does not advance the generator. Streams are
    de-duplicated by identity because the tank hands one Random to the backend,
    the engine and the environment - reporting it three times would imply
    independent streams that do not exist.
    """
    engine = world.engine if isinstance(world, _HasEngine) else None
    environment = engine.environment if isinstance(engine, _HasEnvironment) else None
    candidates = (
        ("world", world),
        ("engine", engine),
        ("environment", environment),
    )

    digests: dict[str, str] = {}
    seen: dict[int, str] = {}
    for name, holder in candidates:
        if holder is None:
            continue
        try:
            # isinstance against a data protocol reads the attribute, and a
            # world that exposes rng as a not-yet-initialised property raises
            # rather than returning None - so the check itself needs guarding.
            if not isinstance(holder, _HasRandom):
                continue
            rng = holder.rng
            state = rng.getstate()
        except Exception:  # a missing or exotic RNG must never break a run
            continue
        identity = id(rng)
        if identity in seen:
            digests[name] = f"same_as:{seen[identity]}"
            continue
        seen[identity] = name
        digests[name] = _digest_state(state)
    return digests


class FingerprintStreamRecorder:
    """Write periodic benchmark snapshot fingerprints for divergence bisection."""

    def __init__(
        self,
        path: str | Path,
        *,
        benchmark_id: str,
        seed: int,
        interval: int = 100,
        record_phases: bool = True,
    ) -> None:
        if interval < 1:
            raise ValueError("interval must be >= 1")

        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.interval = interval
        self.record_phases = record_phases
        self._exact = SnapshotFingerprinter(float_precision=None)
        self._rounded = SnapshotFingerprinter(float_precision=6)
        self._exact_detail = _detail_fingerprinter(None)
        self._rounded_detail = _detail_fingerprinter(6)
        # Per-step digests for the frame currently being observed. Only
        # checkpoint frames are observed, so this stays empty almost always.
        self._phase_frame: int | None = None
        self._phase_rows: list[dict[str, object]] = []
        self._observed_pipeline: object | None = None
        self._observed_world: object | None = None
        self._fh: TextIO = self.path.open("w", encoding="utf-8", newline="\n")
        self._write(
            {
                "type": "header",
                "version": FINGERPRINT_STREAM_VERSION,
                "benchmark_id": benchmark_id,
                "seed": seed,
                "interval": interval,
                "environment": _environment_manifest(),
                "fingerprints": {
                    "algorithm": self._exact.algorithm,
                    "digest_size": self._exact.digest_size,
                    "detail_digest_size": DETAIL_DIGEST_SIZE,
                    "exact_float_precision": None,
                    "rounded_float_precision": self._rounded.float_precision,
                },
                "records": {
                    "phases": record_phases,
                    "entities_by_id": True,
                    "fields": True,
                    "rng": True,
                },
            }
        )

    def record(self, world: object, frame: int) -> None:
        # Attaching here rather than in __init__ is deliberate: the recorder is
        # constructed before the benchmark builds its world, so this is the
        # first moment a pipeline exists to observe.
        if self.record_phases:
            self._attach_phase_observer(world)

        if frame != 0 and frame % self.interval != 0:
            return

        snapshot = _snapshot_for_fingerprint(world)
        entity_groups = _entity_groups(snapshot)
        self._write(
            {
                "type": "checkpoint",
                "frame": frame,
                "exact": self._fingerprint_parts(
                    snapshot, entity_groups, self._exact, self._exact_detail
                ),
                "rounded": self._fingerprint_parts(
                    snapshot, entity_groups, self._rounded, self._rounded_detail
                ),
                "entity_counts": {name: len(entities) for name, entities in entity_groups.items()},
                "rng": _rng_digests(world),
                "phases": self._phase_rows if self._phase_frame == frame else [],
            }
        )

    def _attach_phase_observer(self, world: object) -> None:
        """Subscribe to pipeline steps once the world has a pipeline."""
        engine = world.engine if isinstance(world, _HasEngine) else None
        pipeline = engine.pipeline if isinstance(engine, _HasPipeline) else None
        if pipeline is self._observed_pipeline or not isinstance(pipeline, _ObservablePipeline):
            return
        self._observed_pipeline = pipeline
        self._observed_world = world
        pipeline.set_step_observer(self._on_step)

    def _on_step(self, step_name: str, engine: SimulationEngine) -> None:
        """Record a digest after one pipeline step, on checkpoint frames only.

        Runs inside the simulation loop, so it reads and never writes. Frames
        that are not checkpoints cost one modulo.
        """
        # frame_entry fires before frame_start increments the counter, so at
        # that instant frame_count still names the frame that just finished.
        # The digest belongs to the frame about to run.
        frame = engine.frame_count + 1 if step_name == FRAME_ENTRY_STEP else engine.frame_count
        if frame % self.interval != 0:
            return
        if self._phase_frame != frame:
            self._phase_frame = frame
            self._phase_rows = []
        snapshot = _snapshot_for_fingerprint(self._observed_world)
        self._phase_rows.append(
            {
                "step": step_name,
                "exact": self._exact.fingerprint(snapshot),
                "rounded": self._rounded.fingerprint(snapshot),
            }
        )

    def finish(self, result: Mapping[str, object]) -> None:
        self._write(
            {
                "type": "result",
                "score": result.get("score"),
                "metadata": result.get("metadata", {}),
            }
        )
        self.close()

    def close(self) -> None:
        self._detach_phase_observer()
        if not self._fh.closed:
            self._fh.close()

    def _detach_phase_observer(self) -> None:
        if isinstance(self._observed_pipeline, _ObservablePipeline):
            self._observed_pipeline.set_step_observer(None)
        self._observed_pipeline = None

    def _fingerprint_parts(
        self,
        snapshot: Mapping[str, object],
        entity_groups: dict[str, list[object]],
        fingerprinter: SnapshotFingerprinter,
        detail: SnapshotFingerprinter,
    ) -> dict[str, object]:
        without_entities = {key: value for key, value in snapshot.items() if key != "entities"}
        raw_entities = snapshot.get("entities", [])
        entities_list = list(raw_entities) if isinstance(raw_entities, (list, tuple)) else []
        return {
            "snapshot": fingerprinter.fingerprint(snapshot),
            "world": fingerprinter.fingerprint(without_entities),
            "entities": fingerprinter.fingerprint({"entities": entities_list}),
            "entity_types": {
                name: fingerprinter.fingerprint({"entities": entities})
                for name, entities in entity_groups.items()
            },
            "entities_by_id": _entity_digests(entities_list, detail),
            "fields": _field_digests(entity_groups, detail),
        }

    def _write(self, record: Mapping[str, object]) -> None:
        self._fh.write(json.dumps(record, separators=(",", ":"), ensure_ascii=True))
        self._fh.write("\n")
        self._fh.flush()
