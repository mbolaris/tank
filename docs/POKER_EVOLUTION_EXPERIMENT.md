# Poker Evolution Experiment

This experiment runs headless simulations for 3 tanks and benchmarks evolved poker strategies against the Standard Algorithm using duplicate deals with position rotation.

## One-command runs

Baseline (no experiment overrides):

```bash
python scripts/run_poker_evolution_experiment.py --variant baseline
```

Improved (enable poker evolution overrides):

```bash
python scripts/run_poker_evolution_experiment.py --variant improved --enable-poker-evolution
```

Optional flags:
- `--frames 108000` (default)
- `--seeds 101,202,303`
- `--timestamp 20251226_120624` (force output folder name)
- `--hands 1000` (benchmark hands per candidate)

## Outputs

Each run writes to `results/<timestamp>/<variant>/`:
- `A.json`, `B.json`, `C.json`: per-tank stats export with an embedded `stats_snapshot`.
- `poker_benchmark.json`: benchmark results vs the Standard Algorithm.
- `run_metadata.json`: command, seeds, frames, git commit, and env overrides.

## Key metrics

From `poker_benchmark.json`:
- `bb_per_100`: mean/median/min/max vs Standard Algorithm (higher is better).
- `win_rate_pct`: win rate percentage vs Standard Algorithm.
- `net_energy`: net energy won/lost during benchmark hands.
- `hands_played` and `duplicate_deal_sets`: variance indicators (higher is more stable).

Per-tank aggregates live under `tanks.<A|B|C>.aggregate`. Overall aggregates are in `aggregate`.

## Experiment toggles

Experiment-only knobs live in `core/config/poker_evolution.py` and are opt-in:
- `TANK_POKER_EVOLUTION_EXPERIMENT=1` (master toggle; set by `--enable-poker-evolution`)
- `TANK_POKER_WINNER_WEIGHT`
- `TANK_POKER_MUTATION_RATE_MULTIPLIER`
- `TANK_POKER_MUTATION_STRENGTH_MULTIPLIER`
- `TANK_POKER_NOVELTY_INJECTION_RATE`
- `TANK_POKER_STAKE_MULTIPLIER`
- `TANK_POKER_MAX_BET_CAP`

Example:

```bash
TANK_POKER_STAKE_MULTIPLIER=1.5 TANK_POKER_MAX_BET_CAP=30 \
python scripts/run_poker_evolution_experiment.py --variant improved --enable-poker-evolution
```

## Interpreting results

Success means `bb_per_100` improves (less negative or positive) consistently across tanks, with sufficient `hands_played` and `duplicate_deal_sets` to keep variance low. If `bb_per_100` moves in opposite directions between tanks, increase the hands or adjust selection pressure. Watch for tradeoffs like population collapse or runaway energy transfers.

Note: the benchmark is the primary poker skill signal. Some global poker stats (for example, `poker_stats_summary.total_games`) are not wired into the main loop and may read as 0; use the benchmark aggregates for evaluation.
