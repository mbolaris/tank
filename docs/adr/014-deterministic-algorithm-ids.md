# ADR-014: Deterministic Algorithm / Diversity IDs

## Status

Accepted (2026-06). **Layer 2** — changes how the `ecosystem_health_10k`
diversity metric is computed (and therefore the score's *semantics*), though in
practice both tank champions already recorded the deterministic values and still
reproduce, so no champion file changed. Extends ADR-012 (cross-process /
hash-seed determinism) to the diversity metric.

## Context

Determinism is non-negotiable in this project: benchmarks use fixed seeds and
must be reproducible (ADR-012 established cross-process / `PYTHONHASHSEED`
independence). A latent violation survived that work.

Seven production sites derived a compact integer "algorithm id" / diversity
bucket from a string via the builtin `hash`:

```python
algorithms.add(hash(behavior_id) % 1000)            # genetic_diversity_tracker
algorithm_id = hash(behavior_id) % 1000             # reproduction_service ×2, entity_lifecycle, fish
algo_id = hash(behavior_id) % 1000                  # enhanced_statistics
params["strategy_type"] = hash(type(...).__name__) % 1000   # poker_adapter
```

CPython **randomizes `hash(str)` per process** when `PYTHONHASHSEED` is unset
(it is unset here). Direct proof:

```
hash("food_seeker") % 1000  ->  919 / 500 / 901   (three processes)
PYTHONHASHSEED=0            ->  298 / 298 / 298
```

The trajectory is unaffected — those ids are telemetry, and a seed-42 headless
run is byte-identical across processes (`max_generation`/`births`/`deaths`).
**But** `unique_algorithms` and `diversity_score` (in
`core/genetic_diversity_tracker.py`) are derived from this hash, and they feed
the `ecosystem_health_10k` score (`diversity_bonus = 1 + log2(unique_algorithms)
* 0.3 + diversity_score`) and are stored in the champion. So that benchmark's
**score was not reproducible across processes** — contradicting ADR-012.

The existing `--verify-determinism` check never caught it: it runs the benchmark
twice in *one* process, and `hash` is stable within a process. The bug only
appears across separate interpreters, and surfaced as `diversity_stats`
flickering (18 vs 19 unique algorithms) between otherwise byte-identical runs
during ADR-013 Step 2 verification. The `% 1000` bucketing also caused silent
collisions that *undercount* uniques even within a single process.

## Decision

- Add `core/util/stable_hash.py` with
  `stable_algorithm_id(name) = zlib.crc32(name.encode("utf-8"))` — deterministic
  across processes, collision-free at this codebase's scale.
- `genetic_diversity_tracker.py` (the benchmark-feeding path): count
  `behavior_id` **strings** directly (`algorithms.add(behavior_id)`) —
  deterministic *and* accurate (no bucketing collisions).
- `enhanced_statistics.py`, `poker_adapter.py` (diagnostic paths): swap
  `hash(...) % 1000` → `stable_algorithm_id(...)`.
- Add `tests/test_stable_hash.py`, including a subprocess check that the id is
  identical across separate interpreters.
- **No champion re-baseline was needed.** Both tank champions already record the
  deterministic true counts (`ecosystem_health_10k`: `unique_algorithms=10`,
  score `4.791812102268079`; `survival_5k`: `unique_algorithms=6`), so a fresh
  run now reproduces each exactly — `validate_reproduction.py` passes for both,
  and `config_hash` is unchanged (config didn't change, only the diversity
  computation). The fix removes the *flakiness* (a re-run in a process where a
  hash collision dropped the count would previously have changed the
  `ecosystem_health_10k` score) without changing the recorded values. Had a
  stored value differed from the deterministic count, a re-baseline would have
  been required (precedent: champion version 4, retired for the ADR-012
  cross-process fix).

### Explicitly NOT in scope (separate bug)

The four **telemetry** `algorithm_id` sites (`reproduction_service` ×2,
`entity_lifecycle`, `fish`) still use `hash(behavior_id) % 1000`. They feed
per-algorithm stats that are *also* mis-keyed: `_init_algorithm_stats` keys
`algorithm_stats` by the **enumerate index of the 58 legacy `ALL_ALGORITHMS`
classes**, while telemetry writes under `hash(composable behavior_id) % 1000` —
two unrelated id spaces, so `algorithm_id in algorithm_stats` essentially never
matches and `algorithm_name` is almost always `"Unknown"`. Making those ids
merely deterministic would not fix the mis-keying, so it would be a half-fix.
The proper fix (decide that per-algorithm stats track composable `behavior_id`s,
and share `stable_algorithm_id` at both registration and telemetry) is a
dedicated change tracked in `docs/ARCHITECTURE_REVIEW.md`.

## Verification

- `mypy` clean (332 files); `fast_gate` 1728 passed; new `test_stable_hash.py`
  (incl. cross-process subprocess assertion).
- `ecosystem_health_10k` now scores **identically across two separate
  processes** (previously non-reproducible).
- `ecosystem_health_10k` now scores identically across two separate processes
  (`4.791812102268079`, previously non-reproducible) and `validate_reproduction.py`
  passes against the existing champion. `survival_5k` likewise still reproduces.
  No champion files changed.

## Consequences

- `ecosystem_health_10k` is cross-process reproducible again; the score changed
  (diversity now counts true unique behaviors), which is why the champion is
  re-baselined rather than treated as a regression/improvement.
- Champion comparisons via `validate_improvement.py` are meaningful again.
- A reusable `stable_algorithm_id` primitive now exists for the deferred
  per-algorithm-stats fix.

## Related
- [ADR-012: Cross-Process Determinism (Hash-Seed Independence)](012-hash-seed-determinism.md)
- [ADR-013: Collapse the GenericAgent State Layer](013-collapse-generic-agent-state-layer.md)
