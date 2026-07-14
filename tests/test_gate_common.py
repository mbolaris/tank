"""Tests for the helpers behind the validation gates.

The parsing tests are pure string-parsing functions exercised with literal
sample text captured from real pytest/pytest-xdist runs, so they stay fast and
deterministic. The step-runner tests spawn tiny real subprocesses to prove the
gates reap orphaned grandchildren instead of hanging on them, and that a
gate's own process hard-exits promptly even if it leaks a lingering thread.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tools import gate_common
from tools.gate_common import (
    parse_banner_line,
    parse_collected_counts,
    parse_duration_line,
    run_captured_step,
    run_step_command,
    summarize_pytest_lines,
)


def test_parse_banner_line_extracts_inner_text():
    line = "============================= test session starts =============================\n"
    assert parse_banner_line(line) == "test session starts"


def test_parse_banner_line_returns_none_for_non_banner():
    assert parse_banner_line("tests/smoke/test_tank_mode_smoke.py .          [100%]") is None
    assert parse_banner_line("16 workers [19 items]") is None


def test_parse_collected_counts_with_deselection():
    banner = "1901/2058 tests collected (157 deselected) in 1.49s"
    assert parse_collected_counts(banner) == (2058, 1901, 157)


def test_parse_collected_counts_without_deselection():
    banner = "2058 tests collected in 1.49s"
    assert parse_collected_counts(banner) == (2058, 2058, 0)


def test_parse_collected_counts_singular_item():
    banner = "1 test collected in 0.01s"
    assert parse_collected_counts(banner) == (1, 1, 0)


def test_parse_collected_counts_returns_none_for_result_banner():
    # A final result banner ("N passed...") must not be mistaken for a collection banner.
    assert parse_collected_counts("6 passed, 1 deselected in 0.95s") is None


def test_parse_duration_line_extracts_seconds_and_module():
    line = "0.29s call     tests/smoke/test_petri_mode_smoke.py::test_petri_mode_smoke"
    assert parse_duration_line(line) == (0.29, "tests/smoke/test_petri_mode_smoke.py")


def test_parse_duration_line_strips_class_and_param_suffix():
    line = (
        "0.09s setup    tests/test_config_hash.py::" "TestComputeConfigHash::test_changes_with_seed"
    )
    assert parse_duration_line(line) == (0.09, "tests/test_config_hash.py")


def test_parse_duration_line_returns_none_for_non_duration_text():
    assert parse_duration_line("============ slowest 25 durations ============") is None
    assert parse_duration_line("(3 durations < 0.005s hidden.)") is None


def test_summarize_pytest_lines_aggregates_durations_by_module():
    lines = [
        "============================= test session starts =============================",
        "16 workers [19 items]",
        "...................                                                      [100%]",
        "============================ slowest 25 durations =============================",
        "0.77s call     tests/smoke/test_petri_mode_smoke.py::test_petri_mode_smoke",
        "0.13s setup    tests/smoke/test_petri_mode_smoke.py::test_petri_mode_smoke",
        "0.19s call     tests/test_ecosystem_poker_records.py::test_a",
        "0.02s call     tests/test_ecosystem_poker_records.py::test_b",
        "============================= 19 passed in 5.16s ==============================",
    ]

    result_line, module_durations = summarize_pytest_lines(lines)

    assert result_line == "19 passed in 5.16s"
    assert module_durations == {
        "tests/smoke/test_petri_mode_smoke.py": 0.90,
        "tests/test_ecosystem_poker_records.py": 0.21,
    }


def test_summarize_pytest_lines_ignores_collect_only_style_banner():
    # A --collect-only banner must never be mistaken for the run's final result line.
    lines = ["1901/2058 tests collected (157 deselected) in 1.49s"]

    result_line, module_durations = summarize_pytest_lines(lines)

    assert result_line is None
    assert module_durations == {}


def test_summarize_pytest_lines_handles_no_matches():
    assert summarize_pytest_lines([]) == (None, {})


# A grandchild leaked by a step sleeps this long; the gate must never wait it out.
_ORPHAN_SLEEP_SECONDS = 30

posix_only = pytest.mark.skipif(os.name != "posix", reason="process-group reaping is POSIX-only")


@posix_only
def test_run_captured_step_does_not_hang_on_orphan_holding_pipe(monkeypatch):
    """A step that leaks a background grandchild (e.g. a stuck formatter pool
    worker) must not wedge the gate's output-capture loop: once the leader
    exits, the watchdog kills the step's process group and the pipe closes.
    """
    monkeypatch.setattr(gate_common, "_STRAGGLER_GRACE_SECONDS", 0.5)
    leaker = (
        "import subprocess, sys;"
        "subprocess.Popen([sys.executable, '-c',"
        f" 'import time; time.sleep({_ORPHAN_SLEEP_SECONDS})']);"
        "print('leader done')"
    )

    start = time.monotonic()
    returncode, lines = run_captured_step([sys.executable, "-c", leaker], echo=False)
    elapsed = time.monotonic() - start

    assert returncode == 0
    assert "leader done" in lines
    assert elapsed < _ORPHAN_SLEEP_SECONDS / 2


@posix_only
def test_run_step_command_reaps_orphaned_grandchild(tmp_path):
    """Orphans left behind by a finished step inherit the gate's own stdout, so
    they must be dead by the time the step returns - otherwise a harness reading
    the gate's output to EOF hangs even after the gate exits.
    """
    pid_file = tmp_path / "orphan_pid.txt"
    leaker = (
        "import pathlib, subprocess, sys;"
        "child = subprocess.Popen([sys.executable, '-c',"
        f" 'import time; time.sleep({_ORPHAN_SLEEP_SECONDS})']);"
        f"pathlib.Path({str(pid_file)!r}).write_text(str(child.pid))"
    )

    returncode = run_step_command([sys.executable, "-c", leaker])

    assert returncode == 0
    orphan_pid = int(pid_file.read_text())
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if _process_gone_or_zombie(orphan_pid):
            return
        time.sleep(0.05)
    raise AssertionError(f"orphaned grandchild {orphan_pid} survived run_step_command")


def _process_gone_or_zombie(pid: int) -> bool:
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
    except (FileNotFoundError, ProcessLookupError):
        return True
    # Field after the parenthesized command name is the state; a zombie has
    # been killed and merely awaits reaping by init.
    return stat.rsplit(")", 1)[1].split()[0] == "Z"


def test_exit_for_gate_hard_exits_despite_lingering_non_daemon_thread():
    """exit_for_gate must os._exit rather than `raise SystemExit`: a lingering
    non-daemon thread (e.g. a leaked worker-pool thread) would otherwise keep
    the interpreter alive until the thread finishes, so a CI job invoking a
    gate as its final step would wedge instead of exiting promptly. Runs on
    every platform (unlike the process-group tests above) since this is core
    CPython thread-shutdown behavior, not POSIX process-group semantics.
    """
    code = (
        "import threading, time\n"
        "from tools.gate_common import exit_for_gate\n"
        "threading.Thread(target=lambda: time.sleep(30)).start()\n"
        "exit_for_gate('TEST', True)\n"
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(gate_common.REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(
            "exit_for_gate did not hard-exit within 5s despite a lingering "
            "non-daemon thread - it likely regressed to `raise SystemExit`, "
            "which blocks process exit until non-daemon threads finish."
        )
    assert result.returncode == 0
