"""Tests for benchmark runner toolchain."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_BENCH = REPO_ROOT / "tools" / "run_bench.py"
TANK_BENCHMARK = REPO_ROOT / "benchmarks" / "tank" / "survival_30k.py"


class TestRunBench:
    """Tests for tools/run_bench.py"""

    def test_run_bench_from_repo_root(self):
        """Test running benchmark from repo root directory."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            out_path = f.name

        result = subprocess.run(
            [
                sys.executable,
                str(RUN_BENCH),
                str(TANK_BENCHMARK),
                "--seed",
                "42",
                "--out",
                out_path,
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"

        with open(out_path) as f:
            data = json.load(f)
        assert "score" in data
        assert "benchmark_id" in data
        assert data["benchmark_id"] == "tank/survival_30k"

        Path(out_path).unlink()

    def test_run_bench_from_different_cwd(self):
        """Test running benchmark from /tmp (not repo root) - this was the blocker."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            out_path = f.name

        result = subprocess.run(
            [
                sys.executable,
                str(RUN_BENCH),
                str(TANK_BENCHMARK),
                "--seed",
                "42",
                "--out",
                out_path,
            ],
            cwd="/tmp",  # Critical: run from different directory
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"

        with open(out_path) as f:
            data = json.load(f)
        assert "score" in data

        Path(out_path).unlink()

    @pytest.mark.slow
    def test_verify_determinism_flag(self):
        """Test --verify-determinism flag works."""
        result = subprocess.run(
            [
                sys.executable,
                str(RUN_BENCH),
                str(TANK_BENCHMARK),
                "--seed",
                "42",
                "--verify-determinism",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
        assert (
            "Determinism check PASSED" in result.stderr
            or "Determinism check PASSED" in result.stdout
        )
