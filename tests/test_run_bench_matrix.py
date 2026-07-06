"""Tests for benchmark matrix runner toolchain and validation."""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_BENCH_MATRIX = REPO_ROOT / "tools" / "run_bench_matrix.py"
VALIDATE_IMPROVEMENT = REPO_ROOT / "tools" / "validate_improvement.py"


def create_fake_benchmark(tmp_path: Path, scores_dict=None) -> Path:
    bench_path = tmp_path / "fake_bench.py"
    scores_dict = scores_dict or {42: 10.0, 7: 20.0, 123: 30.0}
    content = f"""
BENCHMARK_ID = "tank/survival_5k"
CONFIG = {{"frames": 2, "world_config": {{}}}}
EXPECTED_RUNTIME_SECONDS = 3.5

SCORES = {scores_dict}

def run(seed, fingerprint_callback=None):
    score = SCORES.get(seed, 15.0)
    return {{
        "benchmark_id": BENCHMARK_ID,
        "seed": seed,
        "score": score,
        "runtime_seconds": 0.01,
        "metadata": {{
            "frames": 2,
            "avg_energy": 100.0,
            "avg_pop": 10.0,
        }}
    }}
"""
    bench_path.write_text(content, encoding="utf-8")
    return bench_path


class TestRunBenchMatrix:
    """Tests for tools/run_bench_matrix.py and matrix validation."""

    def test_run_bench_matrix_basic(self, tmp_path):
        """Test running benchmark matrix and verifying output JSON structure."""
        fake_bench = create_fake_benchmark(tmp_path)
        out_path = tmp_path / "matrix_result.json"
        test_ledger = tmp_path / "attempts_test.jsonl"

        result = subprocess.run(
            [
                sys.executable,
                str(RUN_BENCH_MATRIX),
                str(fake_bench),
                "--seeds",
                "42,7,123",
                "--out",
                str(out_path),
            ],
            cwd=str(REPO_ROOT),
            env={**os.environ, "ATTEMPT_LEDGER_PATH": str(test_ledger)},
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"

        # Verify JSON
        assert out_path.exists()
        with open(out_path, encoding="utf-8") as f:
            data = json.load(f)

        assert data["benchmark_id"] == "tank/survival_5k"
        assert data["seeds"] == [42, 7, 123]
        assert data["scores"] == [10.0, 20.0, 30.0]
        assert data["mean"] == 20.0
        assert data["min"] == 10.0
        assert data["max"] == 30.0
        assert data["n"] == 3
        assert abs(data["stdev"] - 10.0) < 1e-6
        assert "per_seed" in data
        assert "42" in data["per_seed"]
        assert data["per_seed"]["42"]["score"] == 10.0

    def test_compare_and_validate_matrix(self, tmp_path):
        """Test validating matrix results against single-seed and matrix champions."""
        test_ledger = tmp_path / "attempts_test.jsonl"

        # 1. Create a single-seed champion file
        champ_path = tmp_path / "champion.json"
        champ_data = {
            "benchmark_id": "tank/survival_5k",
            "version": 1,
            "champion": {
                "score": 15.0,
                "seed": 42,
                "timestamp": 1234567.0,
                "config_hash": "0123456789abcdef",
            },
        }
        champ_path.write_text(json.dumps(champ_data, indent=2), encoding="utf-8")

        # 2. Run a matrix that beats the champion on seed 42 (e.g. seed 42 score is 16.0)
        fake_bench_better = create_fake_benchmark(
            tmp_path, scores_dict={42: 16.0, 7: 20.0, 123: 30.0}
        )
        res_better_path = tmp_path / "better.json"

        # Run run_bench_matrix
        subprocess.run(
            [
                sys.executable,
                str(RUN_BENCH_MATRIX),
                str(fake_bench_better),
                "--seeds",
                "42,7,123",
                "--out",
                str(res_better_path),
            ],
            cwd=str(REPO_ROOT),
            env={**os.environ, "ATTEMPT_LEDGER_PATH": str(test_ledger)},
        )

        # Patch the config_hash of better.json to match the champion's config_hash to bypass check
        with open(res_better_path, encoding="utf-8") as f:
            res_data = json.load(f)
        res_data["config_hash"] = "0123456789abcdef"
        with open(res_better_path, "w", encoding="utf-8") as f:
            json.dump(res_data, f, indent=2)

        # Validate improvement
        val_res = subprocess.run(
            [
                sys.executable,
                str(VALIDATE_IMPROVEMENT),
                str(res_better_path),
                str(champ_path),
                "--update-champion",
            ],
            cwd=str(REPO_ROOT),
            env={**os.environ, "ATTEMPT_LEDGER_PATH": str(test_ledger)},
            capture_output=True,
            text=True,
        )
        assert val_res.returncode == 0, f"stdout: {val_res.stdout}\nstderr: {val_res.stderr}"
        assert "SUCCESS: Improvement detected!" in val_res.stdout

        # Verify champion is now updated to a matrix format
        with open(champ_path, encoding="utf-8") as f:
            updated_champ = json.load(f)

        assert updated_champ["version"] == 2
        champ_rec = updated_champ["champion"]
        assert champ_rec["mean"] == 22.0
        assert champ_rec["seeds"] == [42, 7, 123]
        assert "per_seed" in champ_rec
        assert champ_rec["per_seed"]["42"]["score"] == 16.0

        # 3. Test running run_bench_matrix with --champion directly
        # Let's run a matrix that is worse on seed 42 (score 14.0) against the updated champion
        fake_bench_worse = create_fake_benchmark(
            tmp_path, scores_dict={42: 14.0, 7: 15.0, 123: 15.0}
        )
        res_worse_path = tmp_path / "worse.json"

        # Execute run_bench_matrix first
        subprocess.run(
            [
                sys.executable,
                str(RUN_BENCH_MATRIX),
                str(fake_bench_worse),
                "--seeds",
                "42,7,123",
                "--out",
                str(res_worse_path),
            ],
            cwd=str(REPO_ROOT),
            env={**os.environ, "ATTEMPT_LEDGER_PATH": str(test_ledger)},
            capture_output=True,
            text=True,
        )

        # Patch the champion's config_hash to match the new run's computed config_hash
        with open(res_worse_path, encoding="utf-8") as f:
            worse_data = json.load(f)
        new_hash = worse_data["config_hash"]

        with open(champ_path, encoding="utf-8") as f:
            champ_data = json.load(f)
        champ_data["champion"]["config_hash"] = new_hash
        with open(champ_path, "w", encoding="utf-8") as f:
            json.dump(champ_data, f, indent=2)

        # Run comparison directly using --champion flag on run_bench_matrix
        compare_res = subprocess.run(
            [
                sys.executable,
                str(RUN_BENCH_MATRIX),
                str(fake_bench_worse),
                "--seeds",
                "42,7,123",
                "--champion",
                str(champ_path),
            ],
            cwd=str(REPO_ROOT),
            env={**os.environ, "ATTEMPT_LEDGER_PATH": str(test_ledger)},
            capture_output=True,
            text=True,
        )
        # Should fail because candidate is worse on all seeds (14 vs 16, 15 vs 20, 15 vs 30)
        assert compare_res.returncode == 1
        assert "FAILURE: Candidate failed to improve on the champion" in compare_res.stdout
