# Tank World Autoresearch: Agent Directives

This file is the "prompt" for the autonomous experiment loop. The human iterates
on this file. The AI agent iterates on the code. (Inspired by Karpathy's
autoresearch pattern.)

## Goal

Maximize the **ecosystem health benchmark score** (`benchmarks/tank/ecosystem_health_10k.py`).

Score formula:
```
score = generation_rate * diversity_bonus * stability_bonus * (1 - starvation_penalty)
```

Higher is better. You want fish that:
1. Reproduce quickly (high generation rate)
2. Use diverse strategies (many unique algorithms thriving)
3. Maintain stable populations (low variance over time)
4. Don't starve (effective food-seeking)

## Editable Files (your scope)

You may ONLY modify these files:

| File | What It Controls |
|------|-----------------|
| `core/algorithms/composable/definitions.py` | Algorithm parameter bounds and defaults |
| `core/algorithms/composable/behavior.py` | Main behavior execution logic |
| `core/algorithms/composable/actions.py` | Sub-behavior implementations |
| `core/config/fish.py` | Energy costs, thresholds, lifecycle params |
| `core/config/food.py` | Food detection ranges, spawning rates |

## Read-Only Files (understand but don't touch)

- `benchmarks/tank/ecosystem_health_10k.py` — The scoring function (fixed)
- `core/worlds/tank/` — World backend (fixed)
- `core/simulation/engine.py` — Simulation engine (fixed)
- `core/entities/` — Entity definitions (fixed)

## Experiment Protocol

Each experiment:

1. Make ONE focused change to an editable file
2. The loop automatically: commits -> benchmarks -> keeps or discards
3. Results appended to `results.tsv`

## Strategy Priorities

### Phase 1: Parameter Tuning (first ~20 experiments)
- Adjust algorithm parameter bounds in `definitions.py`
- Tune energy costs in `core/config/fish.py`
- Adjust food detection ranges in `core/config/food.py`
- Try different default values for behavior parameters

### Phase 2: Behavior Logic (experiments 20-50)
- Improve food-seeking efficiency in `actions.py`
- Better predator avoidance logic
- Smarter reproduction decisions (when to reproduce vs. eat)
- Improve the worst-performing algorithms specifically

### Phase 3: Structural Changes (experiments 50+)
- Add new sub-behaviors to `actions.py`
- Modify behavior composition in `behavior.py`
- Try novel survival strategies
- Combine insights from previous successful experiments

## What "Good" Looks Like

| Metric | Healthy | Warning |
|--------|---------|---------|
| Starvation rate | <60% of deaths | >80% means food-seeking is broken |
| Generation rate | >8 per 10k frames | <3 means evolution is stalled |
| Unique algorithms | >5 active | <3 means monoculture |
| Population stability | CV < 0.3 | CV > 0.5 means boom/bust cycles |

## Rules

1. **One change per experiment.** Small, testable, reversible.
2. **Simpler is better.** If you can delete code and maintain score, do it.
3. **Learn from history.** Check results.tsv for patterns in what works.
4. **Never stop.** If stuck, re-read the editable files for new angles.
5. **Parameter tuning first.** Exhaust simple changes before structural ones.
6. **Determinism matters.** Seed 42 always. Same code = same score.
