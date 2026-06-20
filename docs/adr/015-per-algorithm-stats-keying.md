# ADR-015: Per-Algorithm Stats Keyed by Composable `behavior_id`

## Status

Accepted (2026-06). Completes the follow-up deferred by
[ADR-014](014-deterministic-algorithm-ids.md) (ARCHITECTURE_REVIEW item 6).
Telemetry-only — no trajectory or benchmark-score change.

## Context

`EcosystemManager.algorithm_stats` tracks per-algorithm performance counters
(births, deaths, reproductions, food eaten, current population) and backs
`get_algorithm_performance_report()`. It was silently broken:

- **Registration** (`population_tracker._init_algorithm_stats`) keyed
  `algorithm_stats` by the **enumerate index `0..57` of the legacy
  `ALL_ALGORITHMS` classes**, naming each by class `__name__`.
- **Telemetry** (five sites — fish birth, fish food, `entity_lifecycle` death,
  `reproduction_service` ×2) keyed by `hash(composable behavior_id) % 1000`
  ∈ `[0, 999]`.

These are unrelated id spaces — different sizes and different *meaning* (legacy
algorithm classes vs composable behaviors). `algorithm_id in algorithm_stats`
therefore almost never matched, and because every counter update is guarded by
that membership check, the updates silently no-op'd: per-algorithm counters
stayed at zero and the performance report was empty/garbage. (Lineage
*names* were unaffected, because `BirthEvent` carries a direct `algorithm_name`.)

Two facts make the right fix clear:

- `ALL_ALGORITHMS` is otherwise **dead** — its only consumer was this
  registration. Live fish behavior is entirely the composable framework, whose
  identity is `behavior_id` (the product of four enums = **384** combinations).
- `tests/test_algorithm_tracking.py` passed only because it injected literal ids
  (`0`/`1`/`5`) that happened to match legacy indices; it never exercised the
  telemetry path, so it never caught the mismatch.

## Decision

Make the composable `behavior_id` the single canonical per-algorithm key, shared
by registration and telemetry, derived through `stable_algorithm_id` (ADR-014):

- Add `ComposableBehavior.all_behavior_ids()` and a shared
  `ComposableBehavior._format_behavior_id(...)` so the enumerator and the
  `behavior_id` property cannot drift.
- Register `algorithm_stats[stable_algorithm_id(bid)] = AlgorithmStats(id,
  name=bid)` for every one of the 384 behaviors.
- Switch the five telemetry sites from `hash(behavior_id) % 1000` to
  `stable_algorithm_id(behavior_id)`.
- Retire the `ALL_ALGORITHMS`-index registration (and the now-unused
  `TOTAL_ALGORITHM_COUNT` import in `population_tracker`; the constant still
  serves the diversity-score denominator in `ecosystem_stats`).

## Verification

- `mypy` clean; `fast_gate` green.
- `tests/test_algorithm_tracking.py` rewritten to assert the shared id space:
  registration covers all 384 behaviors, their stable ids are collision-free, a
  telemetry id equals its registration id, counters increment, and an
  unregistered id is ignored (not a `KeyError`).
- **End-to-end:** a seed-42 tank run now records non-zero per-algorithm
  births/deaths/reproductions across ~91 distinct behaviors with real
  `behavior_id` names (previously ~0 and `"Unknown"`).
- Telemetry-only: a seed-42 headless trajectory is unchanged and the
  `ecosystem_health_10k` champion still reproduces.

## Consequences

- The per-algorithm performance report is trustworthy for the first time.
- `algorithm_stats` now holds 384 entries (most empty until a behavior appears);
  the reporter already filters by `min_sample_size`, and the memory cost is
  negligible.
- Counter updates remain membership-guarded, so a fish with no composable
  behavior (the `algorithm_id = 0` fallback) is simply not attributed rather
  than crashing.
- `ALL_ALGORITHMS` is now unused by the ecosystem (only `core/algorithms`
  exports and `test_algorithmic_evolution` still reference it). Whether to retire
  that legacy registry entirely is a separate question.

## Related
- [ADR-014: Deterministic Algorithm / Diversity IDs](014-deterministic-algorithm-ids.md)
- [ADR-009: Reconcile the GenericAgent Component Model](009-generic-agent-model-reconciliation.md)
