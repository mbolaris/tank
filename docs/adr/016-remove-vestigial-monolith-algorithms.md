# ADR-016: Remove the Vestigial Monolithic Algorithm Categories

## Status

Accepted (2026-07)

## Context

ADR-006 established a fact broader than the decision it recorded: **the live
simulation never selects a monolithic algorithm for fish movement.** Fish
execute their genome's `ComposableBehavior` (or a code-pool movement policy);
monoliths are reachable only through the priority-1 `Fish.movement_policy`
override, which nothing in production sets. ADR-006 acted on that fact for the
14 food-seekers; this ADR applies the same finding to the remaining five
categories.

An independent reachability audit (2026-07) reconfirmed the fact for the 44
algorithms that remained after ADR-006 stage 2:

- `Fish.movement_policy` is assigned only by `tools/benchmark_algorithms.py`
  (the pinning harness), `scripts/train_petri_dish.py`, and unit tests. No
  production code path sets it.
- The genome carries only `ComposableBehavior` and `PokerStrategyAlgorithm`
  (`core/genetics/behavioral.py`); `genome_codec.py` never serializes a
  monolith, so no persisted world can restore one.
- `core/evolution/inheritance.py::inherit_algorithm` — the only production-side
  entry into the monolith crossover machinery — has **zero production
  callers** (tests only).
- The poker-interaction monoliths (`core/algorithms/poker.py`) are movement
  behaviors, not poker strategies; fish poker strategies live in
  `core/poker/strategy/` and are unaffected.
- The one tactic ADR-006 found worth keeping (quality-weighted food targeting)
  is already ported into `core/algorithms/composable/food_selection.py`.

The cost of keeping them: five modules (~3,100 lines) that are formatted,
linted, type-checked, bounds-audited (the Theme 3.2 drift list is mostly these
algorithms), catalog-generated, and conformance-tested on every gate run —
while never driving a single fish.

## Decision

Remove the five vestigial categories and everything that exists only to serve
them:

- **DELETE:** `core/algorithms/predator_avoidance.py` (10 algorithms),
  `core/algorithms/schooling.py` (10), `core/algorithms/energy_management.py`
  (8), `core/algorithms/territory.py` (8), `core/algorithms/poker.py` (8).
- **KEEP:** the three ADR-006 survivor foragers
  (`core/algorithms/food_seeking/`) — they beat the composable baseline on
  every seed and remain the comparison candidates for
  `tools/benchmark_algorithms.py` — plus the composable framework and
  `core/algorithms/base.py` (which the survivors and the harness still use).
- **KEEP (for now):** the registry's crossover/mutation machinery
  (`inherit_algorithm_with_mutation`, `crossover_algorithms_weighted`,
  `get_random_algorithm`) — it operates over the surviving `ALL_ALGORITHMS`
  and is exercised by tests; shrinking it further is a separate decision.
- Prune the removed algorithms' entries from `ALGORITHM_PARAMETER_BOUNDS`
  (which resolves the bulk of proposal 3.2's bounds-drift list) and from
  `ALL_ALGORITHMS` (47 → 3).
- `core/config/ecosystem.py::TOTAL_ALGORITHM_COUNT` (50) stays untouched: it
  is a score-normalization constant for the diversity metric, already stale
  (47), and correcting it changes benchmark scores — that is a Layer 1
  re-baseline decision, out of scope here.

## Acceptance gate

Removal must be RNG-neutral. All four champions
(`tank/survival_5k`, `tank/ecosystem_health_10k`, `soccer/training_3k`,
`soccer/training_5k`) were reproduced bit-exactly on the pre-removal tree and
must reproduce bit-exactly on the post-removal tree at their recorded seeds.
No champion re-baseline is performed: identical trajectories are the proof
that the removed code was vestigial.

## Consequences

- The algorithm library is one framework (composable) plus three proven
  foragers: 3 registered standalone algorithms, each with a defined purpose (benchmark comparison candidates).
- The search space evolution actually explores is now the same as the search
  space the code describes.
- `tools/benchmark_algorithms.py` remains the harness for future
  algorithm-vs-baseline questions; candidates now live in git history rather
  than in the registry.
- Docs regenerated: `docs/ALGORITHM_CATALOG.md`; `docs/ARCHITECTURE.md` counts
  corrected (they still claimed 58).
