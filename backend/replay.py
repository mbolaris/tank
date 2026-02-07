from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from core.replay.fingerprint import SnapshotFingerprinter
from core.replay.jsonl import (JsonlReplayReader, JsonlReplayWriter,
                               ReplayFormatError)


class ReplayMismatchError(AssertionError):
    pass


def _get_snapshot_for_fingerprint(world: Any) -> dict[str, Any]:
    debug = getattr(world, "get_debug_snapshot", None)
    if callable(debug):
        snapshot = debug()
        return cast(dict[str, Any], snapshot)
    snapshot = world.get_current_snapshot()
    return cast(dict[str, Any], snapshot)


def _create_runner(*, world_type: str, seed: int, config: dict[str, Any] | None) -> Any:
    mod = importlib.import_module("backend.simulation_runner")
    runner_cls = mod.SimulationRunner
    return runner_cls(world_type=world_type, seed=seed, config=config)


@dataclass(frozen=True)
class ReplayPlan:
    """Optional mode switch plan for recordings."""

    switch_at_frame: dict[int, str]


def record_file(
    path: str | Path,
    *,
    seed: int | None,
    initial_mode: str,
    steps: int,
    record_every: int = 1,
    config: dict[str, Any] | None = None,
    plan: ReplayPlan | None = None,
    digest_size: int = 16,
    float_precision: int = 6,
) -> Path:
    if seed is None:
        raise ValueError("seed is required for replay recording")
    if record_every < 1:
        raise ValueError("record_every must be >= 1")

    fingerprinter = SnapshotFingerprinter(digest_size=digest_size, float_precision=float_precision)
    runner = _create_runner(world_type=initial_mode, seed=seed, config=config)

    with JsonlReplayWriter(path) as writer:
        writer.write_header(
            seed=seed,
            initial_mode=initial_mode,
            config=dict(config or {}),
            fingerprint={
                "algorithm": fingerprinter.algorithm,
                "digest_size": fingerprinter.digest_size,
                "float_precision": fingerprinter.float_precision,
            },
        )

        init_snapshot = _get_snapshot_for_fingerprint(runner.world)
        init_frame = int(init_snapshot.get("frame", 0))
        writer.write_event(
            {
                "type": "op",
                "op": "init",
                "frame": init_frame,
                "fingerprint": fingerprinter.fingerprint(init_snapshot),
            }
        )

        switch_at = dict(plan.switch_at_frame) if plan else {}
        last_record_frame = init_frame

        for _ in range(steps):
            runner.world.step()
            frame = int(getattr(runner.world, "frame_count", 0))

            should_record_step = (frame % record_every == 0) or (frame in switch_at)
            if should_record_step:
                snapshot = _get_snapshot_for_fingerprint(runner.world)
                delta = int(snapshot.get("frame", frame)) - last_record_frame
                if delta < 1:
                    delta = 1
                writer.write_event(
                    {
                        "type": "op",
                        "op": "step",
                        "n": int(delta),
                        "frame": int(snapshot.get("frame", frame)),
                        "fingerprint": fingerprinter.fingerprint(snapshot),
                    }
                )
                last_record_frame = int(snapshot.get("frame", frame))

            target_mode = switch_at.get(frame)
            if target_mode:
                runner.switch_world_type(target_mode)
                snapshot = _get_snapshot_for_fingerprint(runner.world)
                writer.write_event(
                    {
                        "type": "op",
                        "op": "switch_mode",
                        "mode": str(target_mode),
                        "frame": int(snapshot.get("frame", frame)),
                        "fingerprint": fingerprinter.fingerprint(snapshot),
                    }
                )

    return Path(path)


def replay_file(path: str | Path) -> None:
    reader = JsonlReplayReader(path)
    header = reader.read_header()
    if header.version != 1:
        raise ReplayFormatError(f"Unsupported replay version: {header.version}")
    seed = int(header.seed)
    initial_mode = str(header.initial_mode)
    config = dict(header.config or {})

    fp_cfg = dict(header.fingerprint or {})
    digest_size = int(fp_cfg.get("digest_size", 16))
    algorithm = str(fp_cfg.get("algorithm", "blake2b"))
    float_precision = fp_cfg.get("float_precision", 6)
    try:
        float_precision = int(float_precision) if float_precision is not None else None
    except Exception:
        float_precision = 6
    fingerprinter = SnapshotFingerprinter(
        digest_size=digest_size, algorithm=algorithm, float_precision=float_precision
    )

    runner = _create_runner(world_type=initial_mode, seed=seed, config=config)

    first_event_seen = False
    for event in reader.iter_events():
        if event.get("type") != "op":
            continue
        op = event.get("op")
        expected_fp = event.get("fingerprint")
        expected_frame = event.get("frame")

        if op == "init":
            first_event_seen = True
            snapshot = _get_snapshot_for_fingerprint(runner.world)
        elif op == "step":
            first_event_seen = True
            n = int(event.get("n", 1))
            if n < 1:
                raise ReplayFormatError("step op requires n >= 1")
            for _ in range(n):
                runner.world.step()
            snapshot = _get_snapshot_for_fingerprint(runner.world)
        elif op == "switch_mode":
            first_event_seen = True
            mode = event.get("mode")
            if not mode:
                raise ReplayFormatError("switch_mode op requires mode")
            runner.switch_world_type(str(mode))
            snapshot = _get_snapshot_for_fingerprint(runner.world)
        else:
            continue

        actual_fp = fingerprinter.fingerprint(snapshot)
        actual_frame = int(snapshot.get("frame", getattr(runner.world, "frame_count", 0)))

        if expected_frame is not None and int(expected_frame) != actual_frame:
            raise ReplayMismatchError(
                f"Frame mismatch for op={op}: expected={int(expected_frame)} actual={actual_frame}"
            )

        if expected_fp != actual_fp:
            raise ReplayMismatchError(
                f"Fingerprint mismatch at frame={actual_frame} op={op}: expected={expected_fp} actual={actual_fp}"
            )

    if not first_event_seen:
        raise ReplayFormatError("Replay contained no events")
