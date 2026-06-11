# ADR-006: Deprecate the Monolithic Food-Seeking Algorithms

## Status

Accepted (2026-06) — **stage 1 of 2** (metadata only; removal requires
champion re-baselining, see "Staged removal" below)

## Context

`core/algorithms/food_seeking/` holds 14 standalone food-seeking strategies
that predate the composable behavior framework
(`core/algorithms/composable/`). The improvement backlog (theme 3.1) flagged
them as fracturing evolution's search space across two systems.

While building the measurement harness for this decision
(`tools/benchmark_algorithms.py`) we established a more fundamental fact:
**the live simulation never selects a monolithic algorithm for fish
movement.** Fish execute their genome's `ComposableBehavior` (or a code-pool
movement policy); the monoliths are reachable only through the priority-1
`Fish.movement_policy` override, which nothing in production sets. The 14
modules are vestigial weight: maintained, registered in `ALL_ALGORITHMS`,
mutated through genome inheritance — but never driving a fish.

## Measurement

`tools/benchmark_algorithms.py` pins every fish (including newborns) to a
fresh instance of one algorithm via the `movement_policy` override and runs a
headless tank world (survival_5k's world config, 2000 frames). The composable
baseline is run through the *identical* pinning path, so the comparison has
no ball-pursuit or code-pool confounds. 3 seeds (42–44) per candidate,
each run in a pristine worker process; exactly reproducible.

Mean survival score (avg fish count × avg fish energy / 100), starvation
fraction of deaths, and final population over 3 seeds:

| algorithm | score | starv | final pop | seedwise wins vs baseline |
|---|---|---|---|---|
| food_quality_optimizer | 23.11 | 1.00 | 38.0 | **3/3** |
| opportunistic_feeder | 20.80 | 0.96 | 36.3 | **3/3** |
| cooperative_forager | 20.39 | 1.00 | 30.7 | **3/3** |
| spiral_forager | 20.11 | 0.97 | 30.3 | 2/3 |
| greedy_food_seeker | 19.94 | 1.00 | 36.0 | 2/3 |
| energy_aware_food_seeker | 19.77 | 0.91 | 31.7 | 2/3 |
| zigzag_forager | 19.39 | 0.96 | 28.3 | 1/3 |
| circular_hunter | 19.28 | 1.00 | 31.3 | 2/3 |
| patrol_feeder | 18.89 | 1.00 | 34.0 | 2/3 |
| **composable_baseline** | **18.81** | **1.00** | **31.0** | — |
| food_memory_seeker | 18.65 | 1.00 | 30.7 | 2/3 |
| aggressive_hunter | 17.50 | 0.97 | 28.7 | 0/3 |
| surface_skimmer | 16.02 | 1.00 | 26.3 | 0/3 |
| ambush_feeder | 15.33 | 0.96 | 30.7 | 0/3 |
| bottom_feeder | 14.36 | **0.61** | 21.7 | 0/3 |

Reproduce with:
`python tools/benchmark_algorithms.py --out results.json` (≈3.5 min, 4 workers).

## Decision

- **KEEP (port into the composable framework):** `food_quality_optimizer`,
  `opportunistic_feeder`, `cooperative_forager` — the only candidates that
  beat the production composable baseline pairwise on **every** seed.
  +23%, +11%, and +8% mean score respectively. Their tactics
  (quality-weighted targeting, opportunistic switching, shared-target
  avoidance) should become food-approach configurations or sub-behaviors of
  `ComposableBehavior`. This is also the most concrete lead we have on the
  ecosystem's chronically high starvation rate: the production baseline
  leaves measurable foraging performance on the table.
- **DEPRECATE (remove in a future release):** the other 11. The mid-table is
  statistically indistinguishable from the baseline (a 3-seed spread of ±3
  overlaps it), so they add maintenance cost and search-space noise without
  adding capability. `bottom_feeder` has a notably low starvation fraction
  (0.61) but the worst overall score — passivity trades deaths for
  stagnation, not a tactic worth porting.

Deprecation is recorded in `core/algorithms/registry.py` as
`DEPRECATED_ALGORITHMS` (a `frozenset` of algorithm ids) plus a deprecation
note in each module docstring.

## Staged removal (why nothing is excluded yet)

`ALL_ALGORITHMS` feeds `rng.choice` during genome creation. Removing (or
reordering) entries changes every seeded trajectory and invalidates all
recorded champions. Stage 1 (this ADR) is therefore metadata-only and
champion-safe — all four champions reproduce exactly.

Stage 2, a single future change bundled so the ecosystem pays the
re-baseline cost once:

1. Port the three KEEP algorithms' tactics into the composable framework.
2. Remove the 11 deprecated modules and drop all monoliths from
   `ALL_ALGORITHMS`.
3. Fix the bounds-table drift documented in the backlog (11 algorithms with
   missing/mismatched `ALGORITHM_PARAMETER_BOUNDS` entries) — moot for
   removed modules, required for survivors.
4. Re-baseline all champions in the same PR, with before/after scores in the
   commit message.

## Consequences

- The algorithm library's effective search space is documented honestly:
  one framework (composable), three proven tactics to absorb, eleven modules
  on a removal path.
- `tools/benchmark_algorithms.py` remains as the harness for any future
  algorithm-vs-baseline question (it is what "benchmark which monoliths are
  still winners" turned into).
- Until stage 2 lands, the deprecated modules still exist and still mutate;
  nothing behavioral changed in this stage.
