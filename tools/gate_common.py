"""Shared helpers for named validation gates."""

from __future__ import annotations

import os
import re
import signal
import subprocess
import sys
import threading
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Process-group isolation and reaping are POSIX-only; on other platforms the
# gates simply run steps the plain way.
_POSIX = os.name == "posix"

# How long after a step's leader process exits to wait for its output pipe to
# reach EOF before force-killing the step's process group.
_STRAGGLER_GRACE_SECONDS = 5.0

_BANNER_RE = re.compile(r"^=+\s*(.*?)\s*=+$")
_COLLECTED_RE = re.compile(
    r"^(?:(?P<selected>\d+)/(?P<total>\d+) tests collected \((?P<deselected>\d+) deselected\)"
    r"|(?P<total_only>\d+) tests? collected) in [\d.]+s$"
)
_DURATION_RE = re.compile(r"^(\d+\.\d+)s\s+(?:setup|call|teardown)\s+(\S+)$")


def print_gate_header(name: str, target: str, includes: str, excludes: str) -> None:
    print("=" * 72, flush=True)
    print(f"Tank World validation tier: {name}", flush=True)
    print(f"Target runtime: {target}", flush=True)
    print(f"Includes: {includes}", flush=True)
    print(f"Excludes: {excludes}", flush=True)
    print("=" * 72, flush=True)


def parse_banner_line(line: str) -> str | None:
    """Extract the inner text of a pytest `===== ... =====` banner line, if any."""
    match = _BANNER_RE.match(line.strip())
    return match.group(1) if match else None


def parse_collected_counts(banner_text: str) -> tuple[int, int, int] | None:
    """Parse a `--collect-only` summary banner into (total, selected, deselected)."""
    match = _COLLECTED_RE.match(banner_text)
    if not match:
        return None
    if match.group("deselected") is not None:
        return (
            int(match.group("total")),
            int(match.group("selected")),
            int(match.group("deselected")),
        )
    total = int(match.group("total_only"))
    return total, total, 0


def parse_duration_line(line: str) -> tuple[float, str] | None:
    """Parse a `--durations` report line into (seconds, module_path)."""
    match = _DURATION_RE.match(line.strip())
    if not match:
        return None
    seconds, nodeid = match.groups()
    return float(seconds), nodeid.split("::", 1)[0]


def summarize_pytest_lines(lines: Sequence[str]) -> tuple[str | None, dict[str, float]]:
    """Reduce captured pytest stdout lines to a final result banner plus per-module
    aggregate durations (summed from the `--durations` report, when present).
    """
    result_line: str | None = None
    module_durations: dict[str, float] = {}
    for line in lines:
        banner = parse_banner_line(line)
        if banner and " in " in banner and parse_collected_counts(banner) is None:
            result_line = banner
            continue
        parsed_duration = parse_duration_line(line)
        if parsed_duration is not None:
            seconds, module = parsed_duration
            module_durations[module] = module_durations.get(module, 0.0) + seconds
    return result_line, module_durations


def _kill_step_process_group(pgid: int) -> None:
    """Best-effort SIGKILL of a finished step's whole process group.

    Each gate step runs as its own session leader, so once the leader has
    exited, anything still alive in its group is an orphaned grandchild (for
    example a stuck worker from a formatter's process pool in a sandboxed
    environment). Orphans inherit the gate's output pipes, and any harness that
    reads gate output until EOF will hang on them even after the gate itself
    prints its final result and exits - so reap them explicitly.
    """
    if not _POSIX:
        return
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def run_step_command(args: Sequence[str]) -> int:
    """Run one gate step in its own process group, reaping stragglers after."""
    process = subprocess.Popen(
        list(args),
        cwd=str(REPO_ROOT),
        stdin=subprocess.DEVNULL,
        start_new_session=_POSIX,
    )
    try:
        returncode = process.wait()
    except BaseException:
        # The step runs in its own session, so terminal signals (Ctrl-C) do
        # not reach it directly - propagate the interruption ourselves.
        _kill_step_process_group(process.pid)
        raise
    _kill_step_process_group(process.pid)
    return returncode


def run_captured_step(args: Sequence[str], echo: bool) -> tuple[int, list[str]]:
    """Like `run_step_command`, but captures (and optionally echoes) the step's
    merged stdout/stderr lines. A watchdog force-kills the step's process group
    if its output pipe does not reach EOF shortly after the leader exits, so an
    orphaned grandchild holding the pipe open can never wedge the gate.
    """
    process = subprocess.Popen(
        list(args),
        cwd=str(REPO_ROOT),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        start_new_session=_POSIX,
    )
    assert process.stdout is not None
    eof_seen = threading.Event()

    def _reap_if_pipe_stays_open() -> None:
        process.wait()
        if not eof_seen.wait(_STRAGGLER_GRACE_SECONDS):
            _kill_step_process_group(process.pid)

    threading.Thread(target=_reap_if_pipe_stays_open, daemon=True).start()

    captured: list[str] = []
    try:
        for line in process.stdout:
            if echo:
                print(line, end="", flush=True)
            captured.append(line.rstrip("\n"))
    except BaseException:
        _kill_step_process_group(process.pid)
        raise
    finally:
        eof_seen.set()
    returncode = process.wait()
    _kill_step_process_group(process.pid)
    return returncode, captured


def collect_only_counts(target_args: Sequence[str]) -> tuple[int, int, int] | None:
    """Run a fast `--collect-only` pass to report exact (total, selected, deselected)
    counts for a marker expression, without executing any tests. `-n auto` runs do
    not print this breakdown themselves, so this is the only reliable source for it.
    Returns None if the summary banner could not be parsed (purely diagnostic - never
    raises, since it must not affect the gate's pass/fail result).
    """
    _, lines = run_captured_step(
        python_command("-m", "pytest", *target_args, "--collect-only", "-q"),
        echo=False,
    )
    for line in reversed(lines):
        banner = parse_banner_line(line)
        if banner is None:
            continue
        counts = parse_collected_counts(banner)
        if counts is not None:
            return counts
    return None


def run_pytest_with_diagnostics(
    args: Sequence[str],
    name: str,
    collect_only_args: Sequence[str],
    slow_module_count: int = 10,
) -> bool:
    """Run a pytest step like `run_steps`, plus a diagnostic summary: exact
    collected/selected/deselected counts (via a fast --collect-only pre-pass) and
    the slowest modules by aggregated sampled test duration. Diagnostics are purely
    additive - a parsing miss only skips part of the summary, it never changes the
    step's pass/fail result, which comes solely from the pytest exit code.
    """
    print(f"\n=== {name} ===", flush=True)

    counts = collect_only_counts(collect_only_args)
    returncode, captured = run_captured_step(args, echo=True)

    result_line, module_durations = summarize_pytest_lines(captured)

    print("\n--- Test summary ---", flush=True)
    if counts is not None:
        total, selected, deselected = counts
        print(
            f"Collected: {total} items ({selected} selected, {deselected} deselected)", flush=True
        )
    if result_line:
        print(f"Result: {result_line}", flush=True)
    if module_durations:
        ranked = sorted(module_durations.items(), key=lambda kv: kv[1], reverse=True)
        print("Slowest modules (aggregated from sampled test durations):", flush=True)
        for module, seconds in ranked[:slow_module_count]:
            print(f"  {seconds:7.2f}s  {module}", flush=True)

    if returncode != 0:
        print(f"[FAIL] {name} failed with exit code {returncode}", flush=True)
        return False
    print(f"[PASS] {name}", flush=True)
    return True


def run_steps(steps: Sequence[tuple[list[str], str]]) -> bool:
    for args, name in steps:
        print(f"\n=== {name} ===", flush=True)
        returncode = run_step_command(args)
        if returncode != 0:
            print(f"[FAIL] {name} failed with exit code {returncode}", flush=True)
            return False
        print(f"[PASS] {name}", flush=True)
    return True


def exit_for_gate(name: str, passed: bool) -> None:
    if passed:
        print(f"\n[PASS] {name} gate passed.", flush=True)
        raise SystemExit(0)
    print(f"\n[FAIL] {name} gate failed.", flush=True)
    raise SystemExit(1)


def python_command(*args: str) -> list[str]:
    return [sys.executable, *args]
