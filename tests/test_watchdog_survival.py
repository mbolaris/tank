"""Watchdog test for survival_5k benchmark exit and runtime correctness."""

import sys
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_BENCH = REPO_ROOT / "tools" / "run_bench.py"


def test_watchdog_real_survival_5k_3200_frames():
    """Verify that the real survival_5k benchmark can run past frame 3100 and exits cleanly."""
    benchmark_file = REPO_ROOT / "benchmarks" / "tank" / "survival_5k.py"
    assert benchmark_file.exists()

    # Create a temporary modified benchmark file that runs for 3200 frames instead of 5000
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_bench = Path(tmpdir) / "survival_3200.py"

        # Read original content and update CONFIG["frames"] to 3200
        content = benchmark_file.read_text(encoding="utf-8")
        # Replace the frames config
        content = content.replace('"frames": 5000', '"frames": 3200')

        tmp_bench.write_text(content, encoding="utf-8")

        try:
            # Run the modified benchmark via subprocess with a timeout of 90 seconds
            result = subprocess.run(
                [
                    sys.executable,
                    str(RUN_BENCH),
                    str(tmp_bench),
                    "--seed",
                    "42",
                ],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=90,
            )
        except subprocess.TimeoutExpired as e:
            print("\n=== Watchdog Subprocess Timeout ===")
            print(f"Captured stdout:\n{e.stdout}")
            print(f"Captured stderr:\n{e.stderr}")
            raise

        assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
        assert "config_hash" in result.stdout or "config_hash" in result.stderr
