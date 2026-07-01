"""Shared helpers for named validation gates."""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

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


def collect_only_counts(target_args: Sequence[str]) -> tuple[int, int, int] | None:
    """Run a fast `--collect-only` pass to report exact (total, selected, deselected)
    counts for a marker expression, without executing any tests. `-n auto` runs do
    not print this breakdown themselves, so this is the only reliable source for it.
    Returns None if the summary banner could not be parsed (purely diagnostic - never
    raises, since it must not affect the gate's pass/fail result).
    """
    result = subprocess.run(
        python_command("-m", "pytest", *target_args, "--collect-only", "-q"),
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for line in reversed(result.stdout.splitlines()):
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

    process = subprocess.Popen(
        list(args),
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    captured = []
    for line in process.stdout:
        print(line, end="", flush=True)
        captured.append(line.rstrip("\n"))
    returncode = process.wait()

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
        result = subprocess.run(args, cwd=str(REPO_ROOT))
        if result.returncode != 0:
            print(f"[FAIL] {name} failed with exit code {result.returncode}", flush=True)
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
