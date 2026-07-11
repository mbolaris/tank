# Benchmarks

Benchmarks are normal Python modules with a `BENCHMARK_ID`, a deterministic
`run(seed)` function, and an optional `EXPECTED_RUNTIME_SECONDS` budget. The
budget is a human-facing reference, not a timeout or scoring input.

`tools/run_bench.py` prints the actual runtime against that budget and includes
the budget in the result JSON as `expected_runtime_seconds`.

## Runtime Budgets

The live benchmark list, module paths, descriptions, and runtime budgets are
generated in [docs/BENCHMARK_CATALOG.md](../docs/BENCHMARK_CATALOG.md). Reference
budgets are intentionally loose so slower contributor machines still look
normal. If a run is many times over budget, investigate the environment or a
possible regression.
