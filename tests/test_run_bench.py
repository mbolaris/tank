"""Tests for benchmark runner toolchain."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_BENCH = REPO_ROOT / "tools" / "run_bench.py"
TANK_BENCHMARK = REPO_ROOT / "benchmarks" / "tank" / "survival_5k.py"


def create_fake_benchmark(tmp_path: Path) -> Path:
    bench_path = tmp_path / "fake_bench.py"
    content = """
BENCHMARK_ID = "tank/survival_5k"
CONFIG = {"frames": 2, "world_config": {}}

def run(seed, fingerprint_callback=None):
    if fingerprint_callback is not None:
        class FakeWorld:
            def get_debug_snapshot(self):
                return {"frame": 0, "entities": []}
        fingerprint_callback(FakeWorld(), 0)
    return {
        "benchmark_id": BENCHMARK_ID,
        "seed": seed,
        "score": 12.34,
        "runtime_seconds": 0.01,
        "metadata": {
            "frames": 2,
            "avg_energy": 100.0,
            "avg_pop": 10.0,
        }
    }
"""
    bench_path.write_text(content, encoding="utf-8")
    return bench_path


class TestRunBench:
    """Tests for tools/run_bench.py"""

    def test_run_bench_from_repo_root(self, tmp_path):
        """Test running benchmark from repo root directory."""
        fake_bench = create_fake_benchmark(tmp_path)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            out_path = f.name

        result = subprocess.run(
            [
                sys.executable,
                str(RUN_BENCH),
                str(fake_bench),
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
        assert data["benchmark_id"] == "tank/survival_5k"

        Path(out_path).unlink()

    def test_run_bench_from_different_cwd(self, tmp_path):
        """Test running benchmark from a different directory (not repo root)."""
        run_dir = tmp_path / "run_dir"
        run_dir.mkdir()
        fake_bench = create_fake_benchmark(tmp_path)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            out_path = f.name

        result = subprocess.run(
            [
                sys.executable,
                str(RUN_BENCH),
                str(fake_bench),
                "--seed",
                "42",
                "--out",
                out_path,
            ],
            cwd=str(run_dir),
            env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},  # Allow finding local modules
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"

        with open(out_path) as f:
            data = json.load(f)
        assert "score" in data

        Path(out_path).unlink()

    @pytest.mark.slow
    def test_verify_determinism_flag(self, tmp_path):
        """Test --verify-determinism flag works."""
        fake_bench = create_fake_benchmark(tmp_path)
        result = subprocess.run(
            [
                sys.executable,
                str(RUN_BENCH),
                str(fake_bench),
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
