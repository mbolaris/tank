"""Tests for the pytest-output parsing helpers behind the pre-PR gate diagnostics.

These are pure string-parsing functions exercised with literal sample text captured
from real pytest/pytest-xdist runs, so they stay fast and deterministic - no
subprocesses, no sleeps.
"""

from tools.gate_common import (
    parse_banner_line,
    parse_collected_counts,
    parse_duration_line,
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
