"""Watchdog test for survival_5k benchmark exit and runtime correctness."""

import sys
import subprocess
import tempfile
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_BENCH = REPO_ROOT / "tools" / "run_bench.py"


@pytest.mark.slow
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
        content = content.replace("FRAMES = 5000", "FRAMES = 3200")

        tmp_bench.write_text(content, encoding="utf-8")

        try:
            # Run the modified benchmark via subprocess with a timeout of 240 seconds
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
                timeout=240,
            )
        except subprocess.TimeoutExpired as e:
            stdout_str = (
                e.stdout.decode("utf-8", errors="replace")
                if isinstance(e.stdout, bytes)
                else (e.stdout or "")
            )
            stderr_str = (
                e.stderr.decode("utf-8", errors="replace")
                if isinstance(e.stderr, bytes)
                else (e.stderr or "")
            )
            print("\n=== Watchdog Subprocess Timeout ===")
            print(f"Captured stdout:\n{stdout_str}")
            print(f"Captured stderr:\n{stderr_str}")
            raise

        assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
        assert "config_hash" in result.stdout or "config_hash" in result.stderr


@pytest.mark.slow
def test_verify_determinism_exits_cleanly():
    """Verify that --verify-determinism exits cleanly (does not hang).

    Runs both the benchmark's own --verify-determinism entry-point and the
    run_bench.py --verify-determinism wrapper on a short 1000-frame copy so the
    test completes quickly but still exercises the full subprocess round-trip.
    """
    benchmark_file = REPO_ROOT / "benchmarks" / "tank" / "survival_5k.py"
    assert benchmark_file.exists()

    content = benchmark_file.read_text(encoding="utf-8")
    # Truncate to 1000 frames so both subprocess runs finish in well under 30 s
    short_content = content.replace("FRAMES = 5000", "FRAMES = 1000")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_bench = Path(tmpdir) / "survival_1000.py"
        tmp_bench.write_text(short_content, encoding="utf-8")

        # --- 1. benchmark __main__ --verify-determinism ---
        try:
            proc = subprocess.run(
                [sys.executable, str(tmp_bench), "--seed", "42", "--verify-determinism"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired as e:
            stdout_str = (
                e.stdout.decode("utf-8", errors="replace")
                if isinstance(e.stdout, bytes)
                else (e.stdout or "")
            )
            stderr_str = (
                e.stderr.decode("utf-8", errors="replace")
                if isinstance(e.stderr, bytes)
                else (e.stderr or "")
            )
            print("\n=== benchmark --verify-determinism Timeout ===")
            print(f"stdout:\n{stdout_str}")
            print(f"stderr:\n{stderr_str}")
            raise

        assert (
            proc.returncode == 0
        ), f"benchmark --verify-determinism failed\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
        assert (
            "DETERMINISM PASSED" in proc.stdout
        ), f"Expected 'DETERMINISM PASSED' in stdout\n{proc.stdout}"

        # --- 2. run_bench.py --verify-determinism ---
        try:
            proc2 = subprocess.run(
                [
                    sys.executable,
                    str(RUN_BENCH),
                    str(tmp_bench),
                    "--seed",
                    "42",
                    "--verify-determinism",
                ],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired as e:
            stdout_str = (
                e.stdout.decode("utf-8", errors="replace")
                if isinstance(e.stdout, bytes)
                else (e.stdout or "")
            )
            stderr_str = (
                e.stderr.decode("utf-8", errors="replace")
                if isinstance(e.stderr, bytes)
                else (e.stderr or "")
            )
            print("\n=== run_bench.py --verify-determinism Timeout ===")
            print(f"stdout:\n{stdout_str}")
            print(f"stderr:\n{stderr_str}")
            raise

        assert (
            proc2.returncode == 0
        ), f"run_bench.py --verify-determinism failed\nstdout: {proc2.stdout}\nstderr: {proc2.stderr}"
        assert (
            "Determinism check PASSED" in proc2.stdout
        ), f"Expected 'Determinism check PASSED' in stdout\n{proc2.stdout}"
