"""Tests for benchmark runner toolchain."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.run_bench import expected_runtime_seconds, format_runtime_summary

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_BENCH = REPO_ROOT / "tools" / "run_bench.py"


def create_fake_benchmark(tmp_path: Path, runtime_seconds: float = 0.01) -> Path:
    bench_path = tmp_path / "fake_bench.py"
    content = """
BENCHMARK_ID = "tank/survival_5k"
CONFIG = {"frames": 2, "world_config": {}}
EXPECTED_RUNTIME_SECONDS = 3.5

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
    content = content.replace('"runtime_seconds": 0.01', f'"runtime_seconds": {runtime_seconds!r}')
    bench_path.write_text(content, encoding="utf-8")
    return bench_path


def create_real_world_short_benchmark(tmp_path: Path) -> Path:
    bench_path = tmp_path / "real_world_short_bench.py"
    content = """
BENCHMARK_ID = "tank/survival_5k"
CONFIG = {"frames": 2, "world_config": {"headless": True}}
EXPECTED_RUNTIME_SECONDS = 3.5

def run(seed, fingerprint_callback=None):
    from core.worlds import WorldRegistry
    from core.worlds.interfaces import FAST_STEP_ACTION

    world = WorldRegistry.create_world("tank", seed=seed, config={"headless": True})
    world.reset(seed=seed)
    world.step({FAST_STEP_ACTION: True})

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


def create_skill_benchmark(tmp_path: Path) -> Path:
    bench_path = tmp_path / "skill_bench.py"
    content = """
BENCHMARK_ID = "tank/foraging_gym"
CONFIG = {"fixture": True}
EXPECTED_RUNTIME_SECONDS = 1

def run(seed, fingerprint_callback=None):
    return {
        "benchmark_id": BENCHMARK_ID,
        "seed": seed,
        "score": 0.5,
        "runtime_seconds": 0.01,
        "metadata": {
            "skill": {
                "domain": "foraging",
                "benchmark_id": BENCHMARK_ID,
                "metric_name": "energy_ratio",
                "skill_index": 50.0,
                "rungs": [{"rung": "L0", "rung_id": "random", "metric": 0.1, "beaten": True}],
            }
        },
    }
"""
    bench_path.write_text(content, encoding="utf-8")
    return bench_path


class TestRunBench:
    """Tests for tools/run_bench.py"""

    @pytest.mark.parametrize("budget", [0, -1, True, False, "bad", float("inf"), float("nan")])
    def test_invalid_runtime_budget_is_rejected(self, budget):
        with pytest.raises(ValueError, match="finite positive number"):
            expected_runtime_seconds(SimpleNamespace(EXPECTED_RUNTIME_SECONDS=budget))

    def test_optional_runtime_budget(self):
        assert expected_runtime_seconds(SimpleNamespace()) is None
        assert expected_runtime_seconds(SimpleNamespace(EXPECTED_RUNTIME_SECONDS=None)) is None
        assert expected_runtime_seconds(SimpleNamespace(EXPECTED_RUNTIME_SECONDS=3.5)) == 3.5

    def test_determinism_reports_slow_second_run(self, tmp_path):
        """The second subprocess's runtime must not disappear behind the first."""
        fake_bench = create_fake_benchmark(tmp_path)
        source = fake_bench.read_text(encoding="utf-8")
        source = (
            'from pathlib import Path\nCOUNTER = Path(__file__).with_suffix(".runs")\n' + source
        )
        source = source.replace(
            "def run(seed, fingerprint_callback=None):",
            "def run(seed, fingerprint_callback=None):\n"
            "    runs = int(COUNTER.read_text()) if COUNTER.exists() else 0\n"
            "    COUNTER.write_text(str(runs + 1))",
        )
        source = source.replace(
            '"runtime_seconds": 0.01', '"runtime_seconds": 0.01 if runs == 0 else 7.0'
        )
        fake_bench.write_text(source, encoding="utf-8")
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
            timeout=15,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "Determinism run 1: Runtime: 0.0s" in result.stdout
        assert "Determinism run 2: Runtime: 7.0s" in result.stdout
        assert result.stdout.count("WARNING: Runtime exceeds budget") == 1
        assert "Determinism check PASSED" in result.stdout

    @pytest.mark.parametrize(
        ("elapsed", "budget", "warns"),
        [
            (None, 4.0, False),
            (6.0, None, False),
            (6.0, 0.0, False),
            (6.0, -4.0, False),
            (3.0, 4.0, False),
            (4.0, 4.0, False),
            (4.999, 4.0, False),
            (5.0, 4.0, False),
            (5.001, 4.0, True),
            (6.0, 4.0, True),
        ],
    )
    def test_runtime_warning_threshold(self, elapsed, budget, warns):
        summary = format_runtime_summary(elapsed, budget)
        assert ("WARNING:" in summary) == warns
        if elapsed == 6.0 and budget == 4.0:
            assert "exceeds budget by 50.0%" in summary

    @pytest.mark.parametrize("verify_determinism", [False, True])
    def test_over_budget_warning_is_advisory(self, tmp_path, verify_determinism):
        """Flag a slow run without failing it or changing its saved score."""
        fake_bench = create_fake_benchmark(tmp_path, runtime_seconds=7.0)
        out_path = tmp_path / "result.json"
        command = [
            sys.executable,
            str(RUN_BENCH),
            str(fake_bench),
            "--seed",
            "42",
            "--out",
            str(out_path),
        ]
        if verify_determinism:
            command.append("--verify-determinism")
        result = subprocess.run(
            command, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=15
        )
        assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
        assert "WARNING: Runtime exceeds budget by 100.0% (>25%)" in result.stdout
        if verify_determinism:
            assert "Determinism check PASSED" in result.stdout
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert data["score"] == 12.34
        assert data["runtime_seconds"] == 7.0
        assert data["expected_runtime_seconds"] == 3.5

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
        assert data["expected_runtime_seconds"] == 3.5
        assert "Runtime: 0.0s (budget ~3.5s)" in result.stdout

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
        assert data["expected_runtime_seconds"] == 3.5

        Path(out_path).unlink()

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
        assert "Runtime: 0.0s (budget ~3.5s)" in result.stdout

    def test_record_skill_appends_history(self, tmp_path):
        fake_bench = create_skill_benchmark(tmp_path)
        ledger = tmp_path / "skill_history.jsonl"
        result = subprocess.run(
            [
                sys.executable,
                str(RUN_BENCH),
                str(fake_bench),
                "--seed",
                "42",
                "--record-skill",
                "--skill-ledger",
                str(ledger),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
        assert "Skill history appended: 1 rows" in result.stdout
        rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
        assert rows[0]["benchmark_id"] == "tank/foraging_gym"
        assert rows[0]["seeds"] == [42]

    def test_run_bench_survival_5k_exits_cleanly(self, tmp_path):
        """Verify that tools/run_bench.py exits cleanly with 0 and doesn't hang after running survival_5k using a real world."""
        benchmark_file = create_real_world_short_benchmark(tmp_path)

        result = subprocess.run(
            [
                sys.executable,
                str(RUN_BENCH),
                str(benchmark_file),
                "--seed",
                "42",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=15,
        )

        assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
        # Output should be printed, and config_hash / expected_runtime_seconds should be populated
        assert (
            "expected_runtime_seconds" in result.stdout
            or "expected_runtime_seconds" in result.stderr
        )
        assert "config_hash" in result.stdout or "config_hash" in result.stderr
