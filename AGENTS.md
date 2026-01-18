# AI Agent Guide: Instant Contribution to Tank World Evolution

**START HERE.** This file is your operating manual. If you are an AI agent (Claude, GPT, Grok, or similar) that has just pulled this repository, your mission is to accelerate the multi-tier evolution loop. Read this document and begin contributing **immediately**.

---

## TL;DR - Immediate Actions

If you want to start contributing RIGHT NOW, run these commands:

```bash
# 1. Setup (if not already done)
pip install -e .[dev]
pre-commit install

# 2. Run a baseline simulation
python main.py --headless --max-frames 30000 --stats-interval 10000 --export-stats results.json --seed 42

# 3. Evaluate current state
python tools/run_bench.py benchmarks/tank/survival_5k.py --seed 42

# 4. Run the AI tournament to see current standings
python scripts/run_ai_tournament.py --write-back

# 5. Identify what needs improvement, make changes, test, and commit
```

---

## Overview: What is Tank World?

Tank World is a **self-evolving artificial life research framework** where:

1. **Fish (entities) evolve** behaviors through genetic algorithms inside simulations
2. **AI agents evolve** the algorithms, benchmarks, and code outside simulations
3. **The framework evolves** its own tools, workflows, and infrastructure

**The key innovation**: Git is the heredity mechanism. PRs are mutations, CI is selection, merged changes are offspring that future agents inherit.

### The Three-Layer Evolution System

| Layer | What Evolves | How | Your Role |
|-------|--------------|-----|-----------|
| **Layer 0** | In-world fish behaviors | Natural selection in simulation | Run simulations, capture champions |
| **Layer 1** | Algorithms & code | AI proposes improvements, CI validates | Analyze data, generate improvements, submit PRs |
| **Layer 2** | Tooling & workflows | Meta-evolution of how we evolve | Improve benchmarks, instructions, CI gates |

---

## Immediate Mission: Enter the Evolution Loop

Upon pulling this repo, execute the following loop **continuously**:

```
┌─────────────────────────────────────────────────────────────────┐
│                    THE EVOLUTION LOOP                            │
│                                                                  │
│   1. RUN SIMULATION ──► 2. EVALUATE ──► 3. IDENTIFY GAPS        │
│          │                                      │                │
│          ▼                                      ▼                │
│   6. COMMIT & PR ◄──── 5. VALIDATE ◄──── 4. IMPROVE CODE        │
│          │                                                       │
│          └───────────────► REPEAT ─────────────────────────►    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Step 1: Environment Setup

### Quick Setup (Linux/Mac)

```bash
# Clone if needed
git clone https://github.com/mbolaris/tank.git
cd tank

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .[dev]

# Install pre-commit hooks (CRITICAL - prevents CI failures)
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

### Quick Setup (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
pip install pre-commit
pre-commit install
```

---

## Step 2: Run Simulations

### Headless Mode (Fastest - Use This)

```bash
# Quick test (5k frames, ~20 seconds)
python main.py --headless --max-frames 5000 --stats-interval 2500 --seed 42

# Standard experiment (30k frames, ~2 minutes)
python main.py --headless --max-frames 30000 --stats-interval 10000 --export-stats results.json --seed 42

# Long evolution run (100k frames, ~6 minutes)
python main.py --headless --max-frames 100000 --stats-interval 10000 --export-stats results.json --seed 42
```

### Key CLI Flags

| Flag | Description |
|------|-------------|
| `--headless` | No UI, 10-300x faster |
| `--max-frames N` | Simulation length (30 FPS, so 30000 = ~17 minutes sim time) |
| `--stats-interval N` | Print stats every N frames |
| `--export-stats FILE` | Export JSON for analysis |
| `--seed N` | **CRITICAL**: Reproducible random seed |

### Run Benchmarks

```bash
# Run the survival benchmark
python tools/run_bench.py benchmarks/tank/survival_5k.py --seed 42

# Validate against current champion
python tools/validate_improvement.py results.json champions/tank/survival_5k.json
```

### Soccer Mode (Alternative Evolution Target)

```bash
# Run soccer simulation
python main.py --headless --mode soccer --max-frames 30000 --seed 42
```

---

## Step 3: Evaluate Performance

### Key Metrics to Monitor

After running simulations, analyze these metrics from `results.json`:

#### Death Causes (Most Critical)
- `starvation`: Fish couldn't find food - **>90% = food-seeking needs improvement**
- `predation`: Killed by crabs
- `old_age`: Natural death - **This is desired!**

#### Population Health
- `total_births / total_deaths`: Should be >1 for growth
- `reproduction_success_rate`: >100% means multiple offspring per attempt
- `max_generation`: Higher = faster evolution

#### Algorithm Performance
Check `logs/algorithm_performance_report.txt` for:
- Per-algorithm reproduction rates
- Survival rates
- Average lifespan

### Healthy Ecosystem Indicators

| Metric | Healthy Range | Warning |
|--------|--------------|---------|
| Starvation deaths | <80% | >95% = urgent fix needed |
| Population | >20 fish stable | Frequent emergency spawns = unstable |
| Generation rate | >5 per 10k frames | <3 = evolution too slow |
| Reproduction success | >120% | <100% = population declining |
| Diversity score | >15% | <10% = genetic bottleneck |

### Pattern Analysis

| Pattern | Root Cause | Fix Location |
|---------|------------|--------------|
| >90% starvation | Food detection too slow | `core/algorithms/composable/` |
| Frequent emergency spawns | Population crashes | `core/reproduction_service.py` |
| Low diversity | Genetic drift | `core/algorithms/registry.py` |
| Short lifespans | Energy costs too high | `core/config/fish.py` |

---

## Step 4: Identify and Implement Improvements

### Priority Areas for Improvement

1. **Level 0 (In-World)**: Evolve better fish traits and behaviors
   - Run longer simulations with different seeds
   - Capture champion genomes when fish perform well
   - Test different environmental parameters

2. **Level 1 (Algorithms)**: Improve the 58 behavior algorithms
   - Analyze `results.json` for underperformers
   - Modify algorithms in `core/algorithms/`
   - Tune parameters in `core/config/`

3. **Level 2 (Meta)**: Improve the evolution framework
   - Better benchmarks in `benchmarks/`
   - Improved CI workflows in `.github/workflows/`
   - Enhanced documentation and instructions

### Key Files for Improvements

```
core/config/fish.py              # Energy costs, thresholds
core/config/food.py              # Food detection, spawning
core/algorithms/composable/
  ├── definitions.py             # Parameter bounds
  ├── behavior.py                # Main execute logic
  └── actions.py                 # Sub-behavior implementations
core/reproduction_service.py     # Emergency spawn logic
core/time_system.py              # Day/night detection penalty
```

### Using the AI Code Evolution Agent

```bash
# Run simulation and export stats
python main.py --headless --max-frames 30000 --export-stats results.json --seed 42

# Let AI identify and improve worst performer
python scripts/ai_code_evolution_agent.py results.json --provider anthropic

# With validation (runs test simulation before committing)
python scripts/ai_code_evolution_agent.py results.json --provider anthropic --validate

# Dry run (see what would change without committing)
python scripts/ai_code_evolution_agent.py results.json --provider anthropic --dry-run
```

---

## Step 5: Validate Changes

### Run Tests

```bash
# Quick gate (fast, portable)
pytest -m "not slow and not integration"

# Full test suite
pytest

# Specific test files
pytest tests/test_simulation.py
pytest tests/test_determinism.py
```

### Run Formatters (Pre-commit handles this)

```bash
# Format code
black core/ tests/ tools/

# Fix linting errors
ruff check --fix --unsafe-fixes core/ tests/ tools/

# Or just run pre-commit
pre-commit run --all-files
```

### Validate Benchmark Improvement

```bash
# Run your benchmark
python tools/run_bench.py benchmarks/tank/survival_5k.py --seed 42

# Compare against current champion
python tools/validate_improvement.py results.json champions/tank/survival_5k.json
```

### Test Simulation Behavior

```bash
# Quick validation run
python main.py --headless --max-frames 10000 --stats-interval 5000 --seed 42

# Compare key metrics
python3 -c "
import json
with open('results.json') as f: data = json.load(f)
deaths = data.get('death_causes', {})
total = sum(deaths.values()) or 1
print(f'Starvation: {deaths.get(\"starvation\", 0) / total * 100:.1f}%')
print(f'Max generation: {data.get(\"max_generation\", 0)}')
"
```

---

## Step 6: Commit and Submit

### Create Branch

```bash
# For algorithm improvements (Layer 1)
git checkout -b improve/[algorithm-name]-[brief-description]

# For meta improvements (Layer 2)
git checkout -b meta/[improvement-type]-[brief-description]

# For new solutions/champions
git checkout -b solution/[author]-[strategy-name]
```

### Commit Changes

```bash
# Stage changes
git add [modified files]

# Commit with descriptive message
git commit -m "$(cat <<'EOF'
Improve [benchmark]: [Algorithm] optimization

New score: [X] (previous: [Y], +[Z]%)
Algorithm: [Name] with [change description]
Seed: 42
Reproduction: python tools/run_bench.py benchmarks/tank/survival_5k.py --seed 42

- [Change 1]
- [Change 2]
- [Impact description]
EOF
)"
```

### Push and Create PR

```bash
git push -u origin [branch-name]
```

Then open a PR on GitHub with:
- Benchmark results showing improvement
- Reproduction command
- Explanation of changes
- Evidence of no regressions

---

## Solution Tracking System

### Submit Your Best Evolved Solution

```bash
# Option 1: Use capture script (runs sim and captures best fish)
python scripts/capture_first_solution.py

# Option 2: CLI tool
python scripts/submit_solution.py list           # See existing solutions
python scripts/submit_solution.py evaluate <id>  # Evaluate a solution
python scripts/submit_solution.py compare        # Compare all solutions

# Option 3: Capture from running simulation (requires server)
curl -X POST http://localhost:8000/api/solutions/capture/{tank_id} \
  -H "Content-Type: application/json" \
  -d '{"name": "My Strategy", "author": "Agent-Name", "evaluate": true}'
```

### Run AI Tournament

```bash
# Basic tournament
python scripts/run_ai_tournament.py

# Tournament with live tank capture
python scripts/run_ai_tournament.py --include-live-tank --write-back

# More stable evaluation (slower but more accurate)
python scripts/run_ai_tournament.py --benchmark-hands 800 --benchmark-duplicates 25 --matchup-hands 5000 --write-back
```

### Commit Your Solution

```bash
git add solutions/*.json
git commit -m "$(cat <<'EOF'
Submit solution: [Your Solution Name]

Author: [Your Agent Name]
Elo: [rating]
Skill Tier: [tier]
bb/100: [value]
EOF
)"
git push
```

---

## Continuous Evolution Loop Template

Use this workflow template for continuous improvement:

```python
# Pseudocode for continuous evolution
while True:
    # 1. Run baseline
    baseline = run_benchmark(seed=42)

    # 2. Analyze results
    gaps = identify_underperformers(baseline)

    # 3. Generate improvement
    for gap in gaps:
        improvement = propose_improvement(gap)

        # 4. Validate
        test_result = run_benchmark(seed=42, with_improvement=True)

        if test_result.score > baseline.score:
            # 5. Submit
            create_branch()
            commit_changes()
            push_and_pr()

    # 6. Pull latest changes from others
    git_pull()
```

---

## CI Compatibility Notes

### Python Version
CI runs Python 3.8. Use compatible type hints:
```python
# Good (3.8 compatible)
from __future__ import annotations
from typing import Dict, List, Tuple

# Bad (3.9+ only)
def foo() -> dict[str, list[int]]:  # Will fail in CI
```

### Pre-commit Hooks
Always install and run pre-commit:
```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files  # Run before committing
```

### Common CI Failures and Fixes
| Error | Fix |
|-------|-----|
| `black` formatting | Run `black core/ tests/ tools/` |
| `ruff` linting | Run `ruff check --fix core/ tests/` |
| Type errors | Use `from __future__ import annotations` |
| Test failures | Run `pytest -x` locally first |

---

## Resource Reference

### Documentation
| File | Purpose |
|------|---------|
| `AGENTS.md` | This file - AI agent guide |
| `README.md` | Project overview |
| `SETUP.md` | Environment setup |
| `docs/VISION.md` | Long-term goals |
| `docs/ARCHITECTURE.md` | Technical architecture |
| `docs/EVO_CONTRIBUTING.md` | Evolutionary PR protocol |
| `MULTILEVEL_EVOLUTION_STRATEGY.md` | Soccer evolution strategy |
| `BEHAVIOR_DEVELOPMENT_GUIDE.md` | Creating new behaviors |

### Key Directories
| Directory | Contents |
|-----------|----------|
| `core/` | Simulation engine and algorithms |
| `core/algorithms/` | 58 behavior algorithms |
| `core/config/` | Tunable parameters |
| `benchmarks/` | Evaluation harnesses |
| `champions/` | Best-known solutions |
| `solutions/` | Submitted poker solutions |
| `scripts/` | Automation scripts |
| `tools/` | Development utilities |
| `tests/` | Test suite |

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

## Tips for AI Agents

1. **Always run baseline first** - Get metrics before making changes
2. **Use deterministic seeds** - `--seed 42` for reproducibility
3. **Make targeted changes** - One improvement area at a time
4. **Validate before committing** - Run tests and benchmarks locally
5. **Document your changes** - Clear commit messages with metrics
6. **Check for regressions** - Ensure you don't break other benchmarks
7. **Submit your best solutions** - Use the solution tracking system
8. **Pull frequently** - Get improvements from other agents
9. **Focus on high-impact areas** - Starvation rate, generation speed
10. **Iterate rapidly** - Small improvements compound over time

---

## Prompt for New Agent Sessions

Copy this to start a new evolution session:

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

## Emergency Commands

If something breaks:

```bash
# Reset to clean state
git checkout main
git pull origin main

# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Reinstall dependencies
pip install -e .[dev] --force-reinstall

# Clear tank data
rm -rf data/tanks/*

# Run full test suite
pytest -x
```

---

**Remember**: Every improvement you make gets committed to the evolutionary lineage. Your changes become the baseline for future agents. Small, validated improvements compound into significant advances. Start contributing now!
