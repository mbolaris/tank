from __future__ import annotations

import json
import os
import platform
import sys
from collections import defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TextIO

from core.replay.fingerprint import SnapshotFingerprinter

FINGERPRINT_STREAM_VERSION = 1


def _snapshot_for_fingerprint(world: Any) -> dict[str, Any]:
    debug_snapshot = getattr(world, "get_debug_snapshot", None)
    if callable(debug_snapshot):
        return dict(debug_snapshot())
    return dict(world.get_current_snapshot())


def _environment_manifest() -> dict[str, Any]:
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


def _entity_groups(snapshot: Mapping[str, Any]) -> dict[str, list[Any]]:
    groups: dict[str, list[Any]] = defaultdict(list)
    entities = snapshot.get("entities", [])
    if not isinstance(entities, list):
        return {}
    for entity in entities:
        entity_type = "unknown"
        if isinstance(entity, Mapping):
            entity_type = str(entity.get("type", "unknown"))
        groups[entity_type].append(entity)
    return dict(sorted(groups.items()))


class FingerprintStreamRecorder:
    """Write periodic benchmark snapshot fingerprints for divergence bisection."""

    def __init__(
        self,
        path: str | Path,
        *,
        benchmark_id: str,
        seed: int,
        interval: int = 100,
    ) -> None:
        if interval < 1:
            raise ValueError("interval must be >= 1")

        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.interval = interval
        self._exact = SnapshotFingerprinter(float_precision=None)
        self._rounded = SnapshotFingerprinter(float_precision=6)
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
                    "exact_float_precision": None,
                    "rounded_float_precision": self._rounded.float_precision,
                },
            }
        )

    def record(self, world: Any, frame: int) -> None:
        if frame != 0 and frame % self.interval != 0:
            return

        snapshot = _snapshot_for_fingerprint(world)
        entity_groups = _entity_groups(snapshot)
        self._write(
            {
                "type": "checkpoint",
                "frame": frame,
                "exact": self._fingerprint_parts(snapshot, entity_groups, self._exact),
                "rounded": self._fingerprint_parts(snapshot, entity_groups, self._rounded),
                "entity_counts": {name: len(entities) for name, entities in entity_groups.items()},
            }
        )

    def finish(self, result: Mapping[str, Any]) -> None:
        self._write(
            {
                "type": "result",
                "score": result.get("score"),
                "metadata": result.get("metadata", {}),
            }
        )
        self.close()

    def close(self) -> None:
        if not self._fh.closed:
            self._fh.close()

    def _fingerprint_parts(
        self,
        snapshot: dict[str, Any],
        entity_groups: dict[str, list[Any]],
        fingerprinter: SnapshotFingerprinter,
    ) -> dict[str, Any]:
        without_entities = {key: value for key, value in snapshot.items() if key != "entities"}
        return {
            "snapshot": fingerprinter.fingerprint(snapshot),
            "world": fingerprinter.fingerprint(without_entities),
            "entities": fingerprinter.fingerprint({"entities": snapshot.get("entities", [])}),
            "entity_types": {
                name: fingerprinter.fingerprint({"entities": entities})
                for name, entities in entity_groups.items()
            },
        }

    def _write(self, record: dict[str, Any]) -> None:
        self._fh.write(json.dumps(record, separators=(",", ":"), ensure_ascii=True))
        self._fh.write("\n")
        self._fh.flush()


def compare_fingerprint_streams(left_path: str | Path, right_path: str | Path) -> dict[str, Any]:
    """Return the first exact and rounded divergences between two streams."""

    left = _read_checkpoints(left_path)
    right = _read_checkpoints(right_path)
    frames = sorted(set(left) | set(right))
    return {
        "exact": _first_divergence(left, right, frames, "exact"),
        "rounded": _first_divergence(left, right, frames, "rounded"),
    }


def _read_checkpoints(path: str | Path) -> dict[int, dict[str, Any]]:
    checkpoints: dict[int, dict[str, Any]] = {}
    with Path(path).open(encoding="utf-8") as fh:
        for line in fh:
            record = json.loads(line)
            if record.get("type") == "checkpoint":
                checkpoints[int(record["frame"])] = record
    return checkpoints


def _first_divergence(
    left: dict[int, dict[str, Any]],
    right: dict[int, dict[str, Any]],
    frames: list[int],
    precision: str,
) -> dict[str, Any] | None:
    if not frames:
        return {"frame": None, "reason": "no_checkpoints"}

    for frame in frames:
        left_record = left.get(frame)
        right_record = right.get(frame)
        if left_record is None or right_record is None:
            return {"frame": frame, "reason": "missing_checkpoint"}

        left_parts = left_record[precision]
        right_parts = right_record[precision]
        if left_parts["snapshot"] == right_parts["snapshot"]:
            continue

        differing_entity_types = sorted(
            name
            for name in set(left_parts["entity_types"]) | set(right_parts["entity_types"])
            if left_parts["entity_types"].get(name) != right_parts["entity_types"].get(name)
        )
        differing_parts = [
            name for name in ("world", "entities") if left_parts.get(name) != right_parts.get(name)
        ]
        return {
            "frame": frame,
            "reason": "fingerprint_mismatch",
            "differing_parts": differing_parts,
            "differing_entity_types": differing_entity_types,
            "left_entity_counts": left_record.get("entity_counts", {}),
            "right_entity_counts": right_record.get("entity_counts", {}),
        }
    return None
