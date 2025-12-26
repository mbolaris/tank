# Poker Evolution Experiment Report (2025-12-26)

## Commands

Baseline:

```bash
python scripts/run_poker_evolution_experiment.py --variant baseline
```

Improved:

```bash
python scripts/run_poker_evolution_experiment.py --variant improved --enable-poker-evolution
```

Results:
- Baseline: `results/20251226_120624/baseline/`
- Improved: `results/20251226_122709/improved/`

## Baseline metrics (vs Standard Algorithm)

Aggregate (9 candidates):
- `bb_per_100` mean -6058.002, median -3523.82, min -83300.0, max 27907.15
- `win_rate_pct` mean 33.81, median 34.0, min 20.1, max 47.0
- `net_energy` mean -19664.39, median -49980.0, min -98667.0, max 101691.4
- Variance indicators: hands played mean 115.8 (min 6, max 280); duplicate deal sets mean 57.78 (min 3, max 140)

Per tank `bb_per_100` (mean):
- A: -33460.693
- B: 16443.47
- C: -1156.783

## Diagnosis

- Benchmarks show high variance (many candidates busted early), so selection pressure from poker skill is noisy.
- Evolution relies on poker outcomes, but strategy inheritance/mutation likely washes out wins before they compound.
- Global poker stats in `stats_snapshot` report `poker_stats_summary.total_games` as 0, so in-sim poker success is not well tracked; the benchmark is the reliable signal.

## Changes made (Layer 2)

- Added experiment toggles and poker-evolution knobs (winner-biased inheritance, mutation dampening, novelty control, stake scaling): `core/config/poker_evolution.py`.
- Applied experiment overrides to poker strategy crossover and mutation plumbing:
  - `core/poker_system.py`
  - `core/genetics/behavioral.py`
  - `core/poker/strategy/implementations/factory.py`
  - `core/mixed_poker/interaction.py`
- Fixed poker strategy distribution win-rate aggregation bug: `core/ecosystem.py`.
- Added reproducible experiment runner and benchmark export: `scripts/run_poker_evolution_experiment.py`.

## Improved metrics (vs Standard Algorithm)

Aggregate (9 candidates):
- `bb_per_100` mean -849.601, median -1819.29, min -8248.9, max 9447.38
- `win_rate_pct` mean 23.46, median 22.8, min 16.1, max 33.3
- `net_energy` mean -44028.17, median -90737.9, min -102375.6, max 101087.0
- Variance indicators: hands played mean 361.6 (min 64, max 1000); duplicate deal sets mean 180.56 (min 32, max 500)

Per tank `bb_per_100` (mean):
- A: -3274.783
- B: -2708.8
- C: 3434.78

## Before/after comparison (mean bb_per_100)

| Tank | Baseline | Improved | Delta |
| --- | --- | --- | --- |
| A | -33460.693 | -3274.783 | +30185.91 |
| B | 16443.47 | -2708.8 | -19152.27 |
| C | -1156.783 | 3434.78 | +4591.563 |
| Aggregate | -6058.002 | -849.601 | +5208.401 |

## Conclusion

- Aggregate `bb_per_100` improved by +5208.401, with tanks A and C showing large gains.
- Tank B regressed, and aggregate win rate dropped, suggesting the improvements are not uniformly stable yet.
- Longer benchmarks (higher hands and deal sets) reduced variance and produced more consistent measurements.

## Next iteration ideas

- Wire poker result counts into `poker_stats_summary.total_games` to align in-sim signals with the benchmark.
- Run longer benchmarks (2,000-5,000 hands) for tighter confidence intervals.
- Tune stake multipliers or winner weight only for fish-vs-fish games to avoid plant poker dominating energy flows.
