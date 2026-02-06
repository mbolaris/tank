# AI Agent Guide: Tank World Evolution

**You are an AI agent. Your mission is to improve this self-evolving artificial life framework.** Read this document and begin contributing.

Tank World is a research framework where AI agents autonomously run experiments, analyze results, and commit improvements. Git is the heredity mechanism: your PRs are mutations, CI is selection, and merged changes become the baseline for future agents.

---

## TL;DR - Start Here

```bash
# 1. Setup
pip install -e .[dev]
pre-commit install

# 2. Run a benchmark
python tools/run_bench.py benchmarks/tank/survival_5k.py --seed 42

# 3. Run a baseline simulation with stats export
python main.py --headless --max-frames 30000 --stats-interval 10000 --export-stats results.json --seed 42

# 4. Run tests (fast gate)
pytest -m "not slow and not integration"

# 5. Identify what needs improvement, make changes, validate, commit
```

---

## The Three-Layer Evolution System

| Layer | What Evolves | How | Your Role |
|-------|--------------|-----|-----------|
| **Layer 0** | Fish behaviors in-world | Natural selection in simulation | Run simulations, capture champions |
| **Layer 1** | Algorithms and code | AI proposes improvements, CI validates | Analyze data, improve code, submit PRs |
| **Layer 2** | Tooling and workflows | Meta-evolution of how we evolve | Improve benchmarks, instructions, CI gates |

---

## The Evolution Loop

Every agent session should follow this loop:

```
1. RUN SIMULATION ──> 2. EVALUATE ──> 3. IDENTIFY GAPS
       |                                      |
       v                                      v
6. COMMIT & PR <──── 5. VALIDATE <──── 4. IMPROVE CODE
       |
       └───────────> REPEAT
```

---

## Step 1: Run Simulations

### Headless Mode (Use This)

```bash
# Quick test (5k frames)
python main.py --headless --max-frames 5000 --stats-interval 2500 --seed 42

# Standard experiment (30k frames)
python main.py --headless --max-frames 30000 --stats-interval 10000 --export-stats results.json --seed 42

# Long evolution run (100k frames)
python main.py --headless --max-frames 100000 --stats-interval 10000 --export-stats results.json --seed 42
```

### CLI Flags

| Flag | Description |
|------|-------------|
| `--headless` | No UI, 10-300x faster |
| `--max-frames N` | Simulation length (30 FPS, so 30000 = ~17 minutes sim time) |
| `--stats-interval N` | Print stats every N frames |
| `--export-stats FILE` | Export JSON for analysis |
| `--seed N` | Reproducible random seed (always use this) |

### Run Benchmarks

```bash
# Run the survival benchmark
python tools/run_bench.py benchmarks/tank/survival_5k.py --seed 42

# Validate against current champion
python tools/validate_improvement.py results.json champions/tank/survival_5k.json
```

---

## Step 2: Evaluate Performance

### Key Metrics from `results.json`

**Death Causes (Most Critical)**
- `starvation`: Fish couldn't find food. >90% = food-seeking needs improvement.
- `predation`: Killed by crabs.
- `old_age`: Natural death. This is the desired outcome.

**Population Health**
- `total_births / total_deaths`: Should be >1 for growth
- `reproduction_success_rate`: >100% means multiple offspring per attempt
- `max_generation`: Higher = faster evolution

### Healthy Ecosystem Indicators

| Metric | Healthy Range | Warning |
|--------|--------------|---------|
| Starvation deaths | <80% | >95% = urgent fix needed |
| Population | >20 fish stable | Frequent emergency spawns = unstable |
| Generation rate | >5 per 10k frames | <3 = evolution too slow |
| Reproduction success | >120% | <100% = population declining |
| Diversity score | >15% | <10% = genetic bottleneck |

### Diagnosis Patterns

| Pattern | Root Cause | Fix Location |
|---------|------------|--------------|
| >90% starvation | Food detection too slow | `core/algorithms/composable/` |
| Frequent emergency spawns | Population crashes | `core/reproduction_service.py` |
| Low diversity | Genetic drift | `core/algorithms/registry.py` |
| Short lifespans | Energy costs too high | `core/config/fish.py` |

---

## Step 3: Identify and Implement Improvements

### Priority Areas

1. **Layer 1 (Algorithms)**: Improve the 58 behavior algorithms in `core/algorithms/`
2. **Layer 0 (In-World)**: Tune parameters in `core/config/` for better ecosystem dynamics
3. **Layer 2 (Meta)**: Improve benchmarks, CI, documentation, and workflows

### Key Files for Algorithm Improvements

```
core/algorithms/composable/
  definitions.py             # Algorithm parameter bounds
  behavior.py                # Main execute logic
  actions.py                 # Sub-behavior implementations
core/config/fish.py          # Energy costs, thresholds, lifecycle
core/config/food.py          # Food detection, spawning rates
core/reproduction_service.py # Emergency spawn logic
core/time_system.py          # Day/night detection penalty
```

### Using the AI Code Evolution Agent

```bash
# Run simulation and export stats
python main.py --headless --max-frames 30000 --export-stats results.json --seed 42

# Let AI identify and improve worst performer
python scripts/ai_code_evolution_agent.py results.json --provider anthropic

# With validation
python scripts/ai_code_evolution_agent.py results.json --provider anthropic --validate

# Dry run
python scripts/ai_code_evolution_agent.py results.json --provider anthropic --dry-run
```

---

## Step 4: Validate Changes

### Run Tests

```bash
# Quick gate (fast, what CI runs first)
pytest -m "not slow and not integration"

# Full test suite
pytest

# Specific test files
pytest tests/test_determinism.py
pytest tests/test_energy_integration.py
```

### Run Code Quality Checks

```bash
# Format code
black core/ tests/ tools/ backend/ --config pyproject.toml

# Fix linting errors
ruff check --fix core/ tests/ tools/ backend/

# Or run all checks at once
pre-commit run --all-files
```

### Validate Benchmark Improvement

```bash
# Run benchmark
python tools/run_bench.py benchmarks/tank/survival_5k.py --seed 42

# Compare against current champion
python tools/validate_improvement.py results.json champions/tank/survival_5k.json
```

---

## Step 5: Commit and Submit

### Branch Naming

```bash
# Algorithm improvements (Layer 1)
git checkout -b improve/[algorithm-name]-[brief-description]

# Meta improvements (Layer 2)
git checkout -b meta/[improvement-type]-[brief-description]

# New solutions/champions
git checkout -b solution/[author]-[strategy-name]
```

### Commit Message Format

```bash
git commit -m "$(cat <<'EOF'
Improve [benchmark]: [Algorithm] optimization

New score: [X] (previous: [Y], +[Z]%)
Algorithm: [Name] with [change description]
Seed: 42
Reproduction: python tools/run_bench.py benchmarks/tank/survival_5k.py --seed 42

- [Change 1]
- [Change 2]
EOF
)"
```

### Push and PR

```bash
git push -u origin [branch-name]
```

PR must include: benchmark results, reproduction command, explanation, evidence of no regressions.

---

## Claude Code Workflow

Tank World has built-in support for Claude Code agentic development:

### Automatic Setup

- **CLAUDE.md** is loaded automatically at session start, giving Claude full project context
- **SessionStart hook** installs all dependencies in remote (web) sessions
- **.claude/settings.json** pre-approves common commands (pytest, benchmarks, git, etc.)

### Recommended Session Flow

1. Read CLAUDE.md (automatic) to understand the project
2. Run `pytest -m "not slow and not integration"` to verify everything works
3. Run a benchmark to understand current baseline
4. Analyze results and identify improvement targets
5. Make changes, validate with tests and benchmarks
6. Commit with clear metrics in the message

### What Claude Code Can Do Here

- **Improve algorithms**: Analyze simulation data, read algorithm source, propose and implement changes
- **Fix bugs**: Run tests, identify failures, implement fixes
- **Extend benchmarks**: Create new evaluation harnesses with deterministic seeds
- **Improve documentation**: Update guides, add examples, clarify instructions
- **Run the evolution loop**: Execute the full baseline -> analyze -> improve -> validate -> commit cycle

---

## Solution Tracking System

### Submit Solutions

```bash
# Capture from simulation
python scripts/capture_first_solution.py

# CLI management
python scripts/submit_solution.py list
python scripts/submit_solution.py evaluate <id>
python scripts/submit_solution.py compare
```

### Run AI Tournament

```bash
# Basic tournament
python scripts/run_ai_tournament.py

# With live tank capture
python scripts/run_ai_tournament.py --include-live-tank --write-back

# More stable evaluation
python scripts/run_ai_tournament.py --benchmark-hands 800 --benchmark-duplicates 25 --matchup-hands 5000 --write-back
```

---

## CI Compatibility

### Python Version
CI runs Python 3.10. Code must be 3.8-compatible:
```python
# Use this for modern type hints
from __future__ import annotations
from typing import Dict, List, Tuple
```

### Pre-commit Hooks
```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files  # Run before committing
```

### Common CI Failures

| Error | Fix |
|-------|-----|
| `black` formatting | Run `black core/ tests/ tools/ backend/ --config pyproject.toml` |
| `ruff` linting | Run `ruff check --fix core/ tests/ tools/ backend/` |
| Type errors | Use `from __future__ import annotations` |
| Test failures | Run `pytest -x` locally first |

---

## Reference

### Documentation

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Claude Code project intelligence (auto-loaded) |
| `AGENTS.md` | This file |
| `README.md` | Project overview |
| `SETUP.md` | Environment setup |
| `docs/VISION.md` | Long-term goals |
| `docs/ARCHITECTURE.md` | Technical architecture |
| `docs/EVO_CONTRIBUTING.md` | Evolutionary PR protocol |
| `docs/BEHAVIOR_DEVELOPMENT_GUIDE.md` | Creating new behaviors |

### Key Directories

| Directory | Contents |
|-----------|----------|
| `core/algorithms/` | 58 behavior algorithms |
| `core/config/` | Tunable parameters |
| `benchmarks/` | Evaluation harnesses |
| `champions/` | Best-known solutions |
| `scripts/` | Automation scripts |
| `tools/` | Development utilities |
| `tests/` | Test suite (60+ files) |

### Essential Scripts

| Script | Purpose |
|--------|---------|
| `main.py` | Run simulation (web or headless) |
| `tools/run_bench.py` | Run benchmarks |
| `tools/validate_improvement.py` | Compare against champions |
| `scripts/ai_code_evolution_agent.py` | AI-powered code improvement |
| `scripts/run_ai_tournament.py` | Run solution tournaments |
| `scripts/submit_solution.py` | Manage solutions |

---

## Tips

1. **Always run baseline first** before making changes
2. **Always use `--seed 42`** for reproducible benchmarks
3. **One improvement at a time** for clean PRs
4. **Validate before committing** with tests and benchmarks
5. **Clear commit messages** with metrics and reproduction commands
6. **Check for regressions** on other benchmarks
7. **Pull frequently** to get improvements from other agents
8. **Focus on high-impact areas** like starvation rate and generation speed
9. **Small improvements compound** over time through the evolution loop

---

## Prompt Template for New Agent Sessions

```
You are an AI agent working in the TankWorld repo (https://github.com/mbolaris/tank).
Your mission is to improve the evolutionary ALife framework.

Current task: [CHOOSE ONE]
- Run simulation and capture best evolved strategy
- Improve worst-performing algorithm
- Add new benchmark for [specific metric]
- Fix issue with [component]

Workflow:
1. Run baseline: python main.py --headless --max-frames 30000 --export-stats results.json --seed 42
2. Analyze: Review results.json for underperformers
3. Improve: Modify relevant code in core/
4. Validate: pytest && python tools/run_bench.py benchmarks/tank/survival_5k.py --seed 42
5. Commit: Clear message with metrics
6. Push: git push -u origin [branch]

Rules:
- Always use deterministic seeds
- Run pre-commit before committing
- Include benchmark results in PR
- One focused improvement per PR
```

---

**Every improvement you make gets committed to the evolutionary lineage. Your changes become the baseline for future agents. Start contributing now.**
