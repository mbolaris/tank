#!/usr/bin/env python3
"""Validate champion provenance without running simulations."""

from __future__ import annotations

import argparse
import ast
import json
import math
import re
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHAMPIONS = ROOT / "champions"
BENCHMARKS = ROOT / "benchmarks"
CONFIG_HASH_RE = re.compile(r"^[0-9a-f]{16}$")
EARLIEST_REASONABLE_TIMESTAMP = 1_577_836_800  # 2020-01-01 UTC
MAX_FUTURE_SECONDS = 7 * 24 * 60 * 60
HISTORY_TIMESTAMP_SLOP = 24 * 60 * 60


def _record_errors(record: dict[str, Any], label: str, require_config_hash: bool) -> list[str]:
    errors: list[str] = []
    if not isinstance(record.get("seed"), int) or isinstance(record.get("seed"), bool):
        errors.append(f"{label}: seed must be an integer")
    score = record.get("score")
    if not isinstance(score, (int, float)) or isinstance(score, bool) or not math.isfinite(score):
        errors.append(f"{label}: score must be a finite number")
    timestamp = record.get("timestamp")
    if not isinstance(timestamp, (int, float)):
        errors.append(f"{label}: timestamp must be numeric")
    elif timestamp < EARLIEST_REASONABLE_TIMESTAMP or timestamp > time.time() + MAX_FUTURE_SECONDS:
        errors.append(f"{label}: timestamp is outside the reasonable history window")
    config_hash = record.get("config_hash")
    if require_config_hash and not CONFIG_HASH_RE.fullmatch(str(config_hash or "")):
        errors.append(f"{label}: active champion needs a 16-character config_hash")
    return errors


def _tank_metadata_errors(benchmark_id: str, record: dict[str, Any], label: str) -> list[str]:
    if not benchmark_id.startswith("tank/"):
        return []
    metadata = record.get("metadata")
    if not isinstance(metadata, dict):
        return [f"{label}: tank champion metadata must be an object"]

    errors: list[str] = []
    if metadata.get("population_scope") != "fish":
        errors.append(f"{label}: tank metadata must declare population_scope='fish'")
    if (
        "final_total_entities" in metadata
        and metadata.get("final_total_entities_role") != "diagnostic_only"
    ):
        errors.append(
            f"{label}: final_total_entities must be labeled with "
            "final_total_entities_role='diagnostic_only'"
        )
    return errors


def _declared_benchmark_id(path: Path) -> str | None:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return None
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(
            isinstance(target, ast.Name) and target.id == "BENCHMARK_ID" for target in node.targets
        ):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                return node.value.value
    return None


def validate_file(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{path}: invalid JSON: {exc}"]

    try:
        champions_index = path.parts.index("champions")
        relative = Path(*path.parts[champions_index + 1 :]).with_suffix("").as_posix()
    except ValueError:
        return [f"{path}: champion path must be under a champions directory"]
    benchmark_id = data.get("benchmark_id")
    if benchmark_id != relative:
        errors.append(f"{path}: benchmark_id must be {relative!r}, got {benchmark_id!r}")
    benchmark_path = BENCHMARKS / f"{benchmark_id}.py"
    if not isinstance(benchmark_id, str) or not benchmark_path.is_file():
        errors.append(f"{path}: benchmark_id does not reference a benchmark module")
    elif _declared_benchmark_id(benchmark_path) != benchmark_id:
        errors.append(f"{path}: benchmark module BENCHMARK_ID does not match {benchmark_id!r}")

    active = data.get("champion", data)
    if not isinstance(active, dict):
        return errors + [f"{path}: active champion record must be an object"]
    errors.extend(_record_errors(active, f"{path}: active champion", require_config_hash=True))
    errors.extend(_tank_metadata_errors(str(benchmark_id), active, f"{path}: active champion"))

    if "champion" not in data:
        if "history" in data or "version" in data:
            errors.append(f"{path}: flat champion format cannot contain version/history")
        return errors

    version = data.get("version")
    history = data.get("history")
    if not isinstance(version, int) or version < 1:
        errors.append(f"{path}: version must be a positive integer")
        return errors
    if not isinstance(history, list):
        errors.append(f"{path}: history must be a list")
        return errors

    expected_versions = list(range(version - 1, 0, -1))
    actual_versions = [entry.get("version") for entry in history if isinstance(entry, dict)]
    if actual_versions != expected_versions:
        errors.append(
            f"{path}: retired versions must be ordered newest-first as {expected_versions}, "
            f"got {actual_versions}"
        )

    successor_timestamp = active.get("timestamp")
    for index, entry in enumerate(history):
        label = f"{path}: history[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label}: retired entry must be an object")
            continue
        errors.extend(_record_errors(entry, label, require_config_hash=False))
        if entry.get("benchmark_id") != benchmark_id:
            errors.append(f"{label}: benchmark_id must match {benchmark_id!r}")
        retired_at = entry.get("retired_at")
        if not isinstance(retired_at, (int, float)):
            errors.append(f"{label}: retired_at must be numeric")
        else:
            timestamp = entry.get("timestamp")
            if isinstance(timestamp, (int, float)) and retired_at < timestamp:
                errors.append(f"{label}: retired_at cannot precede timestamp")
            if (
                isinstance(successor_timestamp, (int, float))
                and retired_at > successor_timestamp + HISTORY_TIMESTAMP_SLOP
            ):
                errors.append(
                    f"{label}: retired_at is more than one day after its successor timestamp"
                )
        if not isinstance(entry.get("retired_reason"), str) or not entry["retired_reason"].strip():
            errors.append(f"{label}: retired_reason must be a non-empty string")
        successor_timestamp = entry.get("timestamp")
    return errors


def validate_all(champions_dir: Path = CHAMPIONS) -> list[str]:
    files = sorted(champions_dir.glob("**/*.json"))
    if not files:
        return [f"{champions_dir}: no champion files found"]
    errors: list[str] = []
    for path in files:
        errors.extend(validate_file(path))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--champions-dir", type=Path, default=CHAMPIONS)
    args = parser.parse_args()

    errors = validate_all(args.champions_dir)
    if errors:
        print("Champion provenance validation FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1
    count = len(list(args.champions_dir.glob("**/*.json")))
    print(f"Champion provenance validation passed for {count} files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
