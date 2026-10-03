# Benchmarks

Benchmarks are normal Python modules with a `BENCHMARK_ID`, a deterministic
`run(seed)` function, and an optional `EXPECTED_RUNTIME_SECONDS` budget. The
budget is a human-facing reference, not a timeout or scoring input.

`tools/run_bench.py` prints the actual runtime against that budget and includes
the budget in the result JSON as `expected_runtime_seconds`. Runs more than
25% over budget print an advisory warning, including during
`--verify-determinism`. The warning does not change the score or exit status.
Determinism checks report each subprocess separately. `tools/run_bench_matrix.py`
prints the same runtime summary for each seed, so a slow seed cannot be hidden
by the total runtime. Declared budgets must be finite and positive; invalid
budgets fail before the benchmark runs.

## Runtime Budgets

The live benchmark list, module paths, descriptions, and runtime budgets are
generated in [docs/BENCHMARK_CATALOG.md](../docs/BENCHMARK_CATALOG.md). Reference
budgets are intentionally loose so slower contributor machines still look
normal. If a run triggers the warning, investigate machine load or a possible
regression before revising the reference budget. Determinism-check subprocesses
have a separate timeout of three times the budget (600s without a budget).
