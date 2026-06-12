# Tank World Agent Quickstart

This document provides a clear, consistent on-ramp for AI agents (and human developers) contributing to Tank World.

## What is Tank World?

Tank World is an artificial life research framework where fish compete for survival and reproduce under 58 parametrizable behavior algorithms. The codebase itself evolves using Git as heredity:
- **PRs are mutations**: A code change is a genetic variant.
- **CI is natural selection**: Automated validation (tests, determinism, scoring) filters out regressions.
- **Merged PRs are offspring**: Merged code becomes the baseline for future agent runs.

## What should an agent do first?

Before making any changes, an agent must:
1. Initialize/verify the environment.
2. Run the baseline smoke gate to confirm the repository is healthy.
3. Understand the difference between Layer 1 (Algorithm Evolution) and Layer 2 (Meta-Evolution).

## What commands should it run?

Use these commands sequentially depending on your contribution phase:

### 1. Developer Environment Setup
```bash
pip install -e .[dev]
pre-commit install
```

### 2. Validation Tiers
* **Smoke Gate (Before Coding)**: Runs quick checks in under 30 seconds.
  ```bash
  python tools/smoke_gate.py
  ```
* **Fast Gate (Pre-PR Check)**: Runs the smoke gate plus all non-slow unit tests. Runs in under 3 minutes.
  ```bash
  python tools/fast_gate.py
  ```
* **Full Gate (Nightly/Maintainers only)**: Runs everything, including integration/slow tests and strict champion reproduction. Do not run this for routine local iterations.
  ```bash
  python tools/full_gate.py
  ```

### 3. Running Simulation Baseline
If you want to analyze population metrics or run simulations:
```bash
python main.py --headless --max-frames 30000 --stats-interval 10000 --export-stats results.json --seed 42
```

### 4. Running a Specific Benchmark
To measure performance against Best Known Solutions (BKS):
```bash
python tools/run_bench.py benchmarks/tank/survival_5k.py --seed 42
```

## What kinds of contributions are safe?

- **Layer 1 (Behavior & Config)**: Tweaking parameters in `core/config/fish.py` or modifying algorithm logic in `core/algorithms/composable/` to improve survival/reproduction without causing regressions.
- **Layer 2 (Docs, Tests, & Tooling)**: Improving validation gates, refining documentation clarity, or expanding tests in `tests/`.

## What should it avoid?

- **Mixing Layers**: Do not combine Layer 1 behavior optimizations with Layer 2 tooling, documentation, or workflow modifications in a single PR.
- **Unverified Champion Updates**: Do not update `champions/**/*.json` files unless you have reproduced the benchmark score deterministically and have a valid reason to do so.
- **Breaking Determinism**: Do not use non-deterministic inputs (like system time, global random, or network calls) in simulations or benchmarks.
- **Placeholder Work**: Do not leave TODOs or generic placeholders in code or documentation.

## How does it prove an improvement?

1. Run the benchmark locally using a fixed seed:
   ```bash
   python tools/run_bench.py benchmarks/tank/survival_5k.py --seed 42 --out results.json
   ```
2. Compare the output to the existing champion:
   ```bash
   python tools/validate_improvement.py results.json champions/tank/survival_5k.json
   ```
3. If the change represents a valid improvement, update the champion file:
   ```bash
   python tools/validate_improvement.py results.json champions/tank/survival_5k.json --update-champion
   ```
4. If a legitimate codebase change (like a bug fix) breaks deterministic outcomes and necessitates updating all champion baselines, run:
   ```bash
   python tools/verify_all_champions.py
   ```
   And commit the resulting `verify_*.json` outputs as your new baselines.

## What should a PR include?

A PR title must describe the improvement clearly. The description must include:
1. **Summary**: What was changed and why.
2. **Benchmark Results**: Before and after scores.
3. **Reproduction Command**: The exact command and seed used to reproduce the score.
4. **Validation Evidence**: Confirmation that `python tools/fast_gate.py` passes.
5. **No Regressions**: Evidence that other active benchmarks were not degraded.

---

## Copy/Paste Prompts for Agent Sessions

### Prompt A: Vague/Simple Entry (Start Here)
```text
Improve this Tank World repo. Start by reading AGENTS.md and docs/AGENT_QUICKSTART.md, run the smoke gate, find one small safe improvement, validate it, and summarize exactly what changed.
```

### Prompt B: Layer 1 (Algorithm/Config) Optimization
```text
You are an AI agent optimizing Tank World's simulation behaviors.
Your task is to identify and optimize a Layer 1 behavior algorithm or configuration to improve simulation health (e.g., lower starvation rate, higher average lifespan).
1. Read AGENTS.md and docs/AGENT_QUICKSTART.md.
2. Run the smoke gate: python tools/smoke_gate.py
3. Run a baseline benchmark: python tools/run_bench.py benchmarks/tank/survival_5k.py --seed 42
4. Modify fish parameters in core/config/fish.py or behavior logic in core/algorithms/composable/.
5. Validate using the fast gate: python tools/fast_gate.py
6. Compare scores against the champion and update the champion registry.
7. Commit only the Layer 1 changes with a detailed message following the AGENTS.md format.
Do not modify workflows, CI configurations, or unrelated documentation.
```

### Prompt C: Layer 2 (Docs/Tooling/CI) Contribution
```text
You are an AI agent focused on enhancing Tank World's development infrastructure (Layer 2).
Your task is to improve documentation, testing, or benchmark usability.
1. Read AGENTS.md and docs/AGENT_QUICKSTART.md.
2. Run the smoke gate: python tools/smoke_gate.py
3. Propose/implement edits to documentation, test harnesses under tests/, or tools in tools/.
4. Run the fast gate: python tools/fast_gate.py
5. Verify changes do not introduce type errors or lint failures.
6. Commit only Layer 2 changes.
Do not modify fish behaviors, game rules, physics, or champion scores.
```
