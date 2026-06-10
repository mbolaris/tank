"""Benchmark-harness integrity test (IMPROVEMENT_PROPOSALS.md 1.3).

Re-runs every recorded champion benchmark at its recorded seed and asserts the
score reproduces within tolerance. If run_bench.py, a benchmark, or core config
changes in a way that breaks champion reproducibility, this fails loudly
instead of leaving the champions registry silently stale.

Marked slow: runs in the nightly gate, not the fast gate.
"""

import glob
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOLERANCE = 1e-9


def _champion_files() -> list[str]:
    return sorted(glob.glob(str(ROOT / "champions" / "**" / "*.json"), recursive=True))


def _load_benchmark(bench_path: Path):
    module_name = f"integrity_{bench_path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, bench_path)
    assert spec is not None and spec.loader is not None, f"Cannot load {bench_path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.slow
@pytest.mark.parametrize("champ_path", _champion_files(), ids=lambda p: Path(p).stem)
def test_champion_reproduces(champ_path: str) -> None:
    with open(champ_path) as f:
        champ_data = json.load(f)

    bench_id = champ_data["benchmark_id"]
    record = champ_data.get("champion", champ_data)
    seed = record["seed"]
    recorded_score = record["score"]

    bench_path = ROOT / "benchmarks" / f"{bench_id}.py"
    assert bench_path.exists(), f"Champion {champ_path} references missing benchmark {bench_path}"

    bench_module = _load_benchmark(bench_path)
    result = bench_module.run(seed)

    assert abs(result["score"] - recorded_score) <= TOLERANCE, (
        f"Champion {bench_id} (seed {seed}) does not reproduce: "
        f"recorded {recorded_score!r}, got {result['score']!r}. "
        "Either the benchmark/core changed (re-baseline the champion) or "
        "determinism broke."
    )
