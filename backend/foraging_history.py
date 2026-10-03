"""Bounded, persisted live foraging evidence, segmented by measurement identity."""

from __future__ import annotations

import hashlib
import json
import math
from collections import deque
from dataclasses import asdict, is_dataclass
from functools import lru_cache
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

MAX_OBSERVATIONS = 60
IDENTITY_KEYS = ("world_id", "run_id", "evaluator_identity", "config_identity", "benchmark_hash")
RECORD_KEYS = (
    *IDENTITY_KEYS,
    "status",
    "evaluated_at_frame",
    "evaluated_at_generation",
    "tank_average",
    "wandering_mean",
    "perfect_mean",
)


@lru_cache(maxsize=1)
def evaluator_identity() -> str:
    """Content identity of the evaluator and its production controller dependencies."""
    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    paths = [*root.joinpath("core").rglob("*.py"), *root.joinpath("benchmarks").rglob("*.py")]
    paths += list(root.joinpath("backend").glob("skill_observatory*.py"))
    for path in sorted(paths):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def config_identity(config: Any) -> str:
    if config is None:
        return "unknown"
    if is_dataclass(config) and not isinstance(config, type):
        config = asdict(config)
    elif hasattr(config, "to_dict"):
        config = config.to_dict()
    try:
        return hashlib.sha256(
            json.dumps(config, sort_keys=True, allow_nan=False).encode()
        ).hexdigest()
    except (ValueError, TypeError):
        return "unknown"


def effective_config(world: Any) -> Any:
    """Resolve configuration through both legacy worlds and current adapters."""
    for attr in ("simulation_config", "config"):
        config = getattr(world, attr, None)
        if config is not None and (is_dataclass(config) or isinstance(config, dict)):
            return config
    config = getattr(getattr(world, "engine", None), "config", None)
    return config if is_dataclass(config) or isinstance(config, dict) else None


def identity(result: dict) -> tuple:
    return tuple(result.get(key, "unknown") for key in IDENTITY_KEYS)


def valid_result(result: Any) -> bool:
    if not isinstance(result, dict) or result.get("status") != "success":
        return False
    if any(
        not isinstance(result.get(key), str) or result[key] in ("", "unknown")
        for key in IDENTITY_KEYS
    ):
        return False
    try:
        return (
            all(
                math.isfinite(float(result[key]))
                for key in ("tank_average", "wandering_mean", "perfect_mean")
            )
            and float(result["perfect_mean"]) > float(result["wandering_mean"])
            and int(result["evaluated_at_frame"]) >= 0
            and int(result["evaluated_at_generation"]) >= 0
        )
    except (KeyError, ValueError, TypeError, OverflowError):
        return False


class ForagingHistory:
    def __init__(self, world_id: str) -> None:
        self._lock = RLock()
        self.world_id = world_id
        self.run_id = uuid4().hex  # telemetry identity; never consumes simulation RNG
        self._records: deque[dict] = deque(maxlen=MAX_OBSERVATIONS)
        self.unknown_records = 0

    @property
    def records(self) -> list[dict]:
        with self._lock:
            return [dict(row) for row in self._records]

    def start_run(self) -> None:
        with self._lock:
            self.run_id = uuid4().hex

    def record(self, result: dict) -> None:
        with self._lock:
            if (
                not valid_result(result)
                or result["world_id"] != self.world_id
                or result["run_id"] != self.run_id
            ):
                return
            if any(
                identity(row) == identity(result)
                and row["evaluated_at_frame"] == result["evaluated_at_frame"]
                for row in self._records
            ):
                return
            # A late completion cannot move the active segment backwards.
            if (
                self._records
                and identity(self._records[-1]) == identity(result)
                and result["evaluated_at_frame"] < self._records[-1]["evaluated_at_frame"]
            ):
                return
            self._records.append({key: result[key] for key in RECORD_KEYS})

    def comparable(self) -> list[dict]:
        with self._lock:
            if not self._records or self._records[-1]["run_id"] != self.run_id:
                return []
            latest = identity(self._records[-1])
            if self._records[-1]["evaluator_identity"] != evaluator_identity():
                return []
            segment = []
            for row in reversed(self._records):
                if identity(row) != latest:
                    break
                segment.append(dict(row))
            return list(reversed(segment))

    def to_payload(self) -> dict:
        with self._lock:
            return {
                "schema_version": 1,
                "run_id": self.run_id,
                "records": self.records,
                "unknown_records": self.unknown_records,
            }

    def load(self, payload: Any) -> None:
        with self._lock:
            self._records.clear()
            if (
                not isinstance(payload, dict)
                or payload.get("schema_version") != 1
                or not isinstance(payload.get("run_id"), str)
            ):
                self.unknown_records = 1
                return
            self.run_id = payload["run_id"]
            rows = payload.get("records", [])
            if not isinstance(rows, list):
                self.unknown_records = 1
                return
            unknown = payload.get("unknown_records", 0)
            self.unknown_records = (
                min(MAX_OBSERVATIONS, max(0, unknown)) if isinstance(unknown, int) else 1
            )
            for row in rows[-MAX_OBSERVATIONS:]:
                if valid_result(row) and row["world_id"] == self.world_id:
                    if not any(
                        identity(existing) == identity(row)
                        and existing["evaluated_at_frame"] == row["evaluated_at_frame"]
                        for existing in self._records
                    ):
                        self._records.append({key: row[key] for key in RECORD_KEYS})
                else:
                    self.unknown_records += 1
