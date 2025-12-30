# TankWorld Agent Guide

This guide helps AI agents (like Claude) perform evolutionary experiments and code improvements on TankWorld.

## Overview: Two-Layer Evolution System

TankWorld implements a two-layer evolution mechanism:

1. **Layer 1: Population Evolution** (inside simulation)
   - Fish inherit algorithms and traits from parents
   - Natural selection via environmental pressure (starvation, predation)
   - 58 behavior algorithms + ComposableBehavior system

2. **Layer 2: Algorithmic Evolution** (outside simulation)
   - AI agents analyze simulation data
   - Identify underperforming algorithms
   - Improve code and parameters
   - Create PRs for human review

## Quick Start: Running an Experiment

### Step 1: Run Headless Simulation

```bash
# Short test (5k frames, ~20 seconds)
python main.py --headless --max-frames 5000 --stats-interval 2500 --seed 42

# Standard experiment (30k frames, ~2 minutes)
python main.py --headless --max-frames 30000 --stats-interval 10000 --export-stats results.json --seed 42

# Long experiment (100k frames, ~6 minutes)
python main.py --headless --max-frames 100000 --stats-interval 10000 --export-stats results.json --seed 42
```

**Key CLI Flags:**
- `--headless`: No UI, ~250+ FPS
- `--max-frames`: Simulation length (30fps → frames/30 = seconds)
- `--stats-interval`: Print stats every N frames
- `--export-stats FILE`: Export JSON for analysis
- `--seed N`: Reproducible random seed

### Step 2: Analyze Results

The simulation outputs key metrics to watch:

1. **Death Causes** - Most critical metric
   - `starvation`: Fish couldn't find food fast enough
   - `predation`: Killed by crabs
   - `old_age`: Natural death (desired!)

   **If starvation > 90%**: Food-seeking algorithms need improvement

2. **Reproduction Stats**
   - `success_rate`: >100% means multiple offspring per attempt
   - `total_births/deaths`: Population health indicator

3. **Generation Advancement**
   - `max_generation / frames * 10000`: Generations per 10k frames
   - Higher = faster evolution

4. **Algorithm Performance** (in console output)
   - Top performers by reproduction rate
   - Survival rates per algorithm
   - Average lifespan

**Artifacts to review after long runs:**
- `results.json` (exported stats; includes death_causes, max_generation, frame_count)
- `logs/algorithm_performance_report.txt` (per-algorithm reproduction and starvation rates)

### Step 3: Identify Improvements

Common patterns to look for:

| Pattern | Root Cause | Fix Location |
|---------|------------|--------------|
| >90% starvation | Food detection/pursuit too slow | `core/algorithms/composable/` |
| Frequent emergency spawns | Population crashes repeatedly | `core/reproduction_service.py` |
| Low diversity | Genetic drift | `core/algorithms/registry.py` |
| Short lifespans | Energy costs too high | `core/config/fish.py` |

### Step 4: Implement Improvements

Key files for evolution tuning:

```
core/config/fish.py              # Energy costs, thresholds
core/config/food.py              # Food detection, spawning
core/algorithms/composable/
  ├── definitions.py             # Parameter bounds
  ├── behavior.py                # Main execute logic
  └── actions.py                 # Sub-behavior implementations
core/reproduction_service.py     # Emergency spawn logic
core/time_system.py              # Night detection penalty
```

**Example: Boost food pursuit speed**
```python
# In core/algorithms/composable/definitions.py
# Change pursuit_speed bounds from (0.8, 1.2) to (0.9, 1.4)
"pursuit_speed": (0.9, 1.4),  # Increased for faster food catching
```

### Step 5: Validate Changes

```bash
# Quick validation run
python main.py --headless --max-frames 10000 --stats-interval 5000 --seed 42

# Compare metrics with baseline
python3 -c "
import json
with open('results.json') as f: data = json.load(f)
print(f'Starvation rate: {data[\"death_causes\"][\"starvation\"] / data[\"total_deaths\"] * 100:.1f}%')
print(f'Generation rate: {data[\"max_generation\"] * 10000 / data[\"frame_count\"]:.2f} per 10k frames')
"
```

## Key Metrics Reference

### Healthy Ecosystem Indicators
- Starvation deaths: <80% of total deaths
- Population stability: >20 fish most of the time
- Generation advancement: >5 generations per 10k frames
- Reproduction success: >120%

### Warning Signs
- Starvation >95%: Fish can't find food
- Frequent emergency spawns: Population unstable
- Generation rate <3 per 10k: Evolution too slow
- Diversity score <15%: Genetic bottleneck

## File Structure Quick Reference

```
core/
├── algorithms/           # 58 behavior algorithms
│   ├── composable/      # Meta-behavior system (dominant)
│   ├── food_seeking/    # 14 food algorithms
│   ├── predator_avoidance.py  # 10 flee algorithms
│   └── registry.py      # Algorithm registration
├── config/              # Tunable parameters
│   ├── fish.py         # Energy costs, thresholds
│   └── food.py         # Detection ranges, spawning
├── genetics/            # Genome, traits, inheritance
├── reproduction_service.py  # Birth logic, emergency spawns
└── time_system.py       # Day/night cycle, detection modifiers
```

## Recent Improvements (Dec 2024)

Based on 100k frame experiment showing 98.9% starvation:

1. **Reduced EXISTENCE_ENERGY_COST** (0.06 → 0.05)
   - File: `core/config/fish.py`
   - Effect: Better baseline survival

2. **Boosted pursuit_speed range** ((0.8,1.2) → (0.9,1.4))
   - File: `core/algorithms/composable/definitions.py`
   - Effect: Faster food catching

3. **Increased night detection** (25% → 40%)
   - File: `core/time_system.py`
   - Effect: Less punishing night hunting

4. **Improved emergency spawn** (random → clone best fish)
   - File: `core/reproduction_service.py`
   - Effect: Preserves successful genetics

Results: Generation advancement rate nearly doubled (4.4 → 8.7 per 10k frames)

## Solution Tracking & Comparison

TankWorld includes a solution tracking system for preserving, evaluating, and comparing the best skill game strategies produced by simulations. This enables agents to compete and share their best evolved solutions.

### Submitting Your Best Solution

**Option 1: Use the Capture Script**
```bash
# Run simulation and capture best solution automatically
python scripts/capture_first_solution.py
```

**Option 2: Use the CLI Tool**
```bash
# List existing solutions
python scripts/submit_solution.py list

# Evaluate a specific solution
python scripts/submit_solution.py evaluate <solution_id>

# Compare all solutions
python scripts/submit_solution.py compare

# Generate benchmark report
python scripts/submit_solution.py report --print
```

**Option 3: Capture from Running Simulation (API)**
```bash
# Capture best fish from a running tank
curl -X POST http://localhost:8000/api/solutions/capture/{tank_id} \
  -H "Content-Type: application/json" \
  -d '{"name": "My Strategy", "author": "Agent-Name", "evaluate": true}'
```

### Solution Evaluation

Solutions are benchmarked against 8 standard opponents:

| Opponent | Elo | Description |
|----------|-----|-------------|
| always_fold | 800 | Folds every hand |
| random | 900 | Random actions |
| loose_passive | 1100 | Calling station |
| tight_passive | 1150 | Rock player |
| tight_aggressive | 1400 | TAG style |
| loose_aggressive | 1350 | LAG style |
| maniac | 1450 | Hyper-aggressive |
| balanced | 1600 | GTO-inspired |

### Skill Tiers

| Tier | Elo Range | Description |
|------|-----------|-------------|
| failing | <900 | Worse than random |
| novice | 900-1100 | Basic play |
| beginner | 1100-1300 | Competent |
| intermediate | 1300-1450 | Solid |
| advanced | 1450-1550 | Strong |
| expert | 1550-1700 | Very strong |
| master | >1700 | Elite |

### Committing Your Solution to Git

After capturing a solution, commit it to share with other agents:

```bash
# Stage and commit your solution
git add solutions/*.json
git commit -m "Submit solution: <your-solution-name>

Author: <Agent-Name>
Elo: <rating>
Skill Tier: <tier>
"
git push
```

### Solution Files

Solutions are stored in `solutions/` directory as JSON files containing:
- **metadata**: Author, timestamp, fish ID, generation
- **behavior_algorithm**: The evolved behavioral strategy
- **capture_stats**: Performance metrics when captured
- **benchmark_result**: Evaluation against standard opponents

### Current Leaderboard

Run `python scripts/submit_solution.py list` to see current rankings.

First solution submitted: **Opus-4.5 Poker Champion** (Elo 1230, beginner tier)

## Tips for Agents

1. **Always run baseline first** - Get metrics before making changes
2. **Make targeted changes** - One improvement area at a time
3. **Use seed for reproducibility** - `--seed 42` for comparisons
4. **Document your changes** - Add comments explaining rationale
5. **Test with quick runs** - 10k frames validates basic functionality
6. **Long runs for evolution** - 100k+ frames shows evolutionary trends
7. **Submit your best solution** - Use `scripts/capture_first_solution.py` to capture and submit your best evolved strategy

## AI Tournament (Best Per Author)

TankWorld includes a tournament runner that selects the best solution per author and runs a head-to-head round robin.

```bash
# Run tournament (does NOT modify solution JSON files)
python scripts/run_ai_tournament.py

# Include the best fish from your currently-running local tank (requires server running on localhost:8000)
python scripts/run_ai_tournament.py --include-live-tank --write-back

# Run tournament and write results back into solution files + regenerate solutions/benchmark_report.txt
python scripts/run_ai_tournament.py --write-back

# More stable (slower) run
python scripts/run_ai_tournament.py --benchmark-hands 800 --benchmark-duplicates 25 --matchup-hands 5000 --write-back
```

Outputs:
- `solutions/ai_tournament_report.txt` (human-readable standings + head-to-head matrix)
- `results/ai_tournament_results.json` (optional; pass `--json-output results/ai_tournament_results.json`)

Re-running the tournament on the same git commit should produce the same head-to-head matrix (deterministic seeding is based on solution IDs).

## Prompt Template: Submit Your Next Attempt

Copy/paste the following prompt into your agent session (edit placeholders):

```
You are an AI agent working in the TankWorld repo. Your goal is to submit a new poker solution that improves your author’s best standing in the AI tournament.

Rules:
- Use your model name as `author` and include it in the solution `name`.
- Do not modify unrelated files.
- Prefer reproducible runs: always record the seed(s) used.

Workflow:
1) Baseline: run `python scripts/run_ai_tournament.py` and note current standings.
2) Evolve: run a longer headless simulation (50k–150k frames) and try multiple seeds.
   - Example: `python main.py --headless --max-frames 100000 --seed 4242`
3) Capture: capture the best poker fish into a solution JSON (create a capture script if needed).
4) Evaluate: run a stronger benchmark evaluation:
   - `python scripts/submit_solution.py evaluate <solution_id> --hands 800 --duplicates 25`
5) Save: ensure the solution JSON exists under `solutions/` and has `metadata.author` and `metadata.name` set correctly.
6) Verify: rerun the tournament including your new solution:
   - `python scripts/run_ai_tournament.py --write-back`
7) Submit: commit only the new/updated solution JSON and any intentional supporting changes.
   - `git add solutions/<solution_id>.json`
   - `git commit -m "Submit solution: <solution_name>\n\nAuthor: <author>\nElo: <elo>\nSkill Tier: <tier>\nbb/100: <bb_per_100>\n"`
   - `git push`

Deliverable:
- The new `solution_id`, Elo, tier, bb/100, and your position in the tournament standings.
```
