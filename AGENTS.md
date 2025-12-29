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

## Tips for Agents

1. **Always run baseline first** - Get metrics before making changes
2. **Make targeted changes** - One improvement area at a time
3. **Use seed for reproducibility** - `--seed 42` for comparisons
4. **Document your changes** - Add comments explaining rationale
5. **Test with quick runs** - 10k frames validates basic functionality
6. **Long runs for evolution** - 100k+ frames shows evolutionary trends
