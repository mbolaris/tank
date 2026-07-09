# Benchmarks

Benchmarks are normal Python modules with a `BENCHMARK_ID`, a deterministic
`run(seed)` function, and an optional `EXPECTED_RUNTIME_SECONDS` budget. The
budget is a human-facing reference, not a timeout or scoring input.

`tools/run_bench.py` prints the actual runtime against that budget and includes
the budget in the result JSON as `expected_runtime_seconds`.

## Runtime Budgets

Reference budgets are intentionally loose so slower contributor machines still
look normal. If a run is many times over budget, treat that as a signal to check
the environment or investigate a regression.

| Benchmark | Budget | Reference |
|---|---:|---|
| `benchmarks/tank/survival_5k.py` | ~45s | Champion runtime ~35s |
| `benchmarks/tank/ecosystem_health_10k.py` | ~75s | Champion runtime ~63s |
| `benchmarks/tank/selection_response_10k.py` | ~90s | 10k-frame selection assay |
| `benchmarks/tank/foraging_gym.py` | ~2s | Isolated foraging skill, random floor, attainable oracle ceiling |
| `benchmarks/soccer/training_3k.py` | ~5s | Champion runtime ~3s |
| `benchmarks/soccer/training_5k.py` | ~5s | Champion runtime ~3s |
