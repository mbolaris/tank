"""Tests for tools/mypy_gate.py hardening against mypy-not-runnable."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

from tools.mypy_gate import main


def _fake_run(stdout: str = "", stderr: str = "", returncode: int = 0):
    """Return a factory that yields a fake subprocess.run result."""

    def _run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0] if args else [],
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
        )

    return _run


class TestMypyGateFatalDetection:
    """Ensure the gate fails when mypy can't actually run."""

    def test_no_module_named_mypy(self):
        fake = _fake_run(
            stderr="/usr/bin/python: No module named mypy\n",
            returncode=1,
        )
        with patch("tools.mypy_gate.subprocess.run", fake):
            rc = main([])
        assert rc == 2

    def test_module_not_found_error(self):
        fake = _fake_run(
            stderr="ModuleNotFoundError: No module named 'mypy'\n",
            returncode=1,
        )
        with patch("tools.mypy_gate.subprocess.run", fake):
            rc = main([])
        assert rc == 2

    def test_traceback_in_output(self):
        fake = _fake_run(
            stderr="Traceback (most recent call last):\n  File ...\nImportError: ...\n",
            returncode=1,
        )
        with patch("tools.mypy_gate.subprocess.run", fake):
            rc = main([])
        assert rc == 2

    def test_unexpected_returncode(self):
        fake = _fake_run(stdout="", returncode=2)
        with patch("tools.mypy_gate.subprocess.run", fake):
            rc = main([])
        assert rc == 2

    def test_segfault_returncode(self):
        fake = _fake_run(stdout="", returncode=-11)
        with patch("tools.mypy_gate.subprocess.run", fake):
            rc = main([])
        assert rc == 2

    def test_clean_run_passes(self, tmp_path: Path):
        fake = _fake_run(stdout="Success: no issues found in 42 source files\n", returncode=0)
        baseline = tmp_path / "mypy_baseline.txt"
        with (
            patch("tools.mypy_gate.subprocess.run", fake),
            patch("tools.mypy_gate.BASELINE_PATH", baseline),
        ):
            rc = main(["--write-baseline"])
        assert rc == 0
