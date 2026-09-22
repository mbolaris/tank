#!/usr/bin/env python3
"""Is this change faster, and did it leave every trajectory exactly as it was?

A performance PR makes two claims: the engine got faster, and the simulation
still does precisely what it did before. The second is the one that matters -
a "speedup" that nudges a single float changes every champion trajectory
downstream of it - and it is the one people check by hand, if at all.

This runs one benchmark on a base git ref (checked out into a temporary
worktree) and on the working tree, interleaved so machine drift lands on both
sides, and answers both claims at once:

    base 110aaaf   62.04s  12.41 ms/frame
    head (tree)    55.10s  11.02 ms/frame   -11.2% runtime, 1.13x faster
    trajectory: IDENTICAL - score 818.434878 on both sides, 21 fingerprint
                checkpoints match exactly

When the trajectories differ it prints the five-part divergence report from
``tools/compare_fingerprint_streams.py`` (frame, phase, entity, RNG stream,
state field) and exits 1: the change is a behavior change, not an
optimization, and needs the champion-validation path instead. Pass
``--allow-behavior-change`` when that is intended and only the timing is wanted.

Wall-clock timings are noisy; the trajectory verdict is not. Use ``--repeats``
for a steadier runtime (each side reports its fastest run), and never quote a
single-digit-percent speedup from one run.

Examples::

    python tools/perf_check.py                              # vs HEAD, survival_5k
    python tools/perf_check.py --base origin/master --repeats 3
    python tools/perf_check.py --benchmark benchmarks/tank/ecosystem_health_10k.py
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_BENCHMARK = "benchmarks/tank/survival_5k.py"
DEFAULT_FINGERPRINT_EVERY = 250


@dataclass
class SideResult:
    """Every run of one side (base or head) of the comparison."""

    label: str
    runtimes: list[float] = field(default_factory=list)
    score: float | None = None
    frames: int | None = None
    fingerprint_path: Path | None = None

    @property
    def best_runtime(self) -> float | None:
        return min(self.runtimes) if self.runtimes else None

    @property
    def ms_per_frame(self) -> float | None:
        best = self.best_runtime
        if best is None or not self.frames:
            return None
        return 1000.0 * best / self.frames


def speedup_summary(base_seconds: float, head_seconds: float) -> str:
    """Describe head's runtime relative to base, e.g. ``-11.2% runtime, 1.13x faster``."""
    if base_seconds <= 0 or head_seconds <= 0:
        return "runtime unavailable"
    change = 100.0 * (head_seconds - base_seconds) / base_seconds
    ratio = base_seconds / head_seconds
    direction = "faster" if ratio >= 1.0 else "slower"
    factor = ratio if ratio >= 1.0 else 1.0 / ratio
    return f"{change:+.1f}% runtime, {factor:.2f}x {direction}"


def trajectory_verdict(
    base_score: float | None,
    head_score: float | None,
    comparison: dict[str, Any],
    checkpoints: int,
) -> tuple[bool, str]:
    """Return (identical, one-line verdict) from the scores and a stream comparison.

    Identical means bit-identical: equal scores *and* no exact divergence at any
    fingerprint checkpoint. A rounded-only match is still a behavior change for
    this purpose - an optimization must not move a single float.
    """
    if comparison.get("exact") is None and comparison.get("rounded") is None:
        if base_score == head_score:
            return True, (
                f"IDENTICAL - score {head_score} on both sides, "
                f"{checkpoints} fingerprint checkpoints match exactly"
            )
        return False, (
            f"DIFFERENT - fingerprints match but score moved {base_score} -> {head_score}"
        )
    return False, f"DIFFERENT - score {base_score} -> {head_score}"


def _run_side(
    tree: Path,
    benchmark: str,
    seed: int,
    fingerprint_every: int | None,
    out_dir: Path,
    tag: str,
) -> dict[str, Any]:
    """Run one benchmark in ``tree`` via that tree's own run_bench.py.

    ``fingerprint_every=None`` skips fingerprint recording (a timing run).
    """
    out_json = out_dir / f"{tag}.json"
    out_stream = out_dir / f"{tag}.jsonl"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(tree)
    cmd = [
        sys.executable,
        str(tree / "tools" / "run_bench.py"),
        str(tree / benchmark),
        "--seed",
        str(seed),
        "--out",
        str(out_json),
    ]
    if fingerprint_every is not None:
        cmd += [
            "--fingerprint-out",
            str(out_stream),
            "--fingerprint-every",
            str(fingerprint_every),
        ]
    proc = subprocess.run(cmd, cwd=tree, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"{tag}: run_bench failed ({proc.returncode})\n{proc.stdout[-2000:]}\n"
            f"{proc.stderr[-2000:]}"
        )
    result: dict[str, Any] = json.loads(out_json.read_text())
    if fingerprint_every is not None:
        result["_fingerprint_path"] = str(out_stream)
    return result


def _record(side: SideResult, result: dict[str, Any], *, timed: bool) -> None:
    runtime = result.get("runtime_seconds")
    if timed and isinstance(runtime, (int, float)):
        side.runtimes.append(float(runtime))
    if side.score is None:
        side.score = result.get("score")
    elif result.get("score") != side.score:
        # Same code, same seed, different score: the run itself is not
        # deterministic, so no verdict drawn from it can be trusted.
        raise RuntimeError(f"{side.label}: score changed between repeats of identical code")
    frames = (result.get("metadata") or {}).get("frames")
    side.frames = int(frames) if isinstance(frames, (int, float)) else side.frames
    if "_fingerprint_path" in result:
        side.fingerprint_path = Path(result["_fingerprint_path"])


def count_checkpoints(stream: Path) -> int:
    """Number of fingerprint checkpoint records in a JSONL stream."""
    count = 0
    with stream.open() as handle:
        for line in handle:
            line = line.strip()
            if line and json.loads(line).get("type") == "checkpoint":
                count += 1
    return count


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--base", default="HEAD", help="Git ref to compare against")
    parser.add_argument("--benchmark", default=DEFAULT_BENCHMARK)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--repeats",
        type=int,
        default=1,
        help="Unfingerprinted timing runs per side (0: time the verdict run itself)",
    )
    parser.add_argument("--fingerprint-every", type=int, default=DEFAULT_FINGERPRINT_EVERY)
    parser.add_argument(
        "--allow-behavior-change",
        action="store_true",
        help="Exit 0 even when trajectories differ (timing-only comparison)",
    )
    parser.add_argument("--json", action="store_true", help="Emit a JSON summary")
    args = parser.parse_args(argv)

    from core.replay.fingerprint_diff import compare_fingerprint_streams, format_divergence_report

    base_sha = _git("rev-parse", "--short", args.base)
    work_dir = Path(tempfile.mkdtemp(prefix="perf_check_"))
    base_tree = work_dir / "base"
    _git("worktree", "add", "--detach", str(base_tree), base_sha)
    base = SideResult(label=f"base {base_sha}")
    head = SideResult(label="head (tree)")
    try:
        # Pass 0 records fingerprints for the verdict; recording is not free, so
        # timing comes from the unfingerprinted passes after it (or from pass 0
        # when --repeats 0 asks for the verdict alone).
        for i in range(max(0, args.repeats) + 1):
            every = args.fingerprint_every if i == 0 else None
            for side, tree in ((base, base_tree), (head, ROOT)):
                tag = f"{'base' if side is base else 'head'}{i}"
                print(f"perf_check: running {tag} ...", file=sys.stderr)
                result = _run_side(tree, args.benchmark, args.seed, every, work_dir, tag)
                _record(side, result, timed=i > 0 or args.repeats <= 0)

        assert base.fingerprint_path is not None and head.fingerprint_path is not None
        comparison = compare_fingerprint_streams(base.fingerprint_path, head.fingerprint_path)
        identical, verdict = trajectory_verdict(
            base.score, head.score, comparison, count_checkpoints(head.fingerprint_path)
        )
        speed = (
            speedup_summary(base.best_runtime, head.best_runtime)
            if base.best_runtime and head.best_runtime
            else "runtime unavailable"
        )

        if args.json:
            print(
                json.dumps(
                    {
                        "benchmark": args.benchmark,
                        "seed": args.seed,
                        "base_ref": base_sha,
                        "base_runtimes": base.runtimes,
                        "head_runtimes": head.runtimes,
                        "base_ms_per_frame": base.ms_per_frame,
                        "head_ms_per_frame": head.ms_per_frame,
                        "speedup": speed,
                        "trajectory_identical": identical,
                        "verdict": verdict,
                    },
                    indent=2,
                )
            )
        else:
            print(
                f"perf_check: {args.benchmark} seed {args.seed}, "
                f"{len(head.runtimes)} timed run(s) per side"
            )
            for side in (base, head):
                ms = f"{side.ms_per_frame:.2f} ms/frame" if side.ms_per_frame else ""
                print(f"  {side.label:<14} {side.best_runtime or 0:7.2f}s  {ms}")
            print(f"  change: {speed}")
            print(f"  trajectory: {verdict}")
            if not identical and (comparison.get("exact") or comparison.get("rounded")):
                print(format_divergence_report(comparison))
            if not identical:
                print(
                    "  -> a behavior change, not a pure optimization: validate it against "
                    "champions/ like any Layer 1 change."
                )
        return 0 if identical or args.allow_behavior_change else 1
    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(base_tree)],
            cwd=ROOT,
            capture_output=True,
        )
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
