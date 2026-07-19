# Performance Profile & Optimization Candidates (2026-07-18)

Profiling session against the headless tank world, seed 42, current master
(`e78d678f`). This document records where frame time actually goes and ranks
the optimizations worth implementing, with evidence, fix sketches, and the
determinism risk of each.

> **Status update (2026-07-19):** P1 (lazy mutation contexts + a
> correctly-scoped isolation cache), P2 (a per-fish nearest-crab memo), and
> the P5 `behavior_id` string cache have been implemented. Measured effect:
> `scripts/benchmark_performance.py --frames 3000 --warmup 500` at matched
> population (114 entities / 63 fish) went from 12.13ms to ~8.2ms average
> frame time (~32% faster). `--export-stats` on seeds 42/7/123 is bit-identical
> before/after. One correction to this doc's original P1 analysis: the naive
> "just defer `context_for_parents`" sketch was not actually safe as written —
> it would have changed how often the escalation hysteresis latch advances.
> The shipped fix decouples the latch update (now always once per frame, in
> `record_diversity_sample`) from the now-lazy isolation scan (safe to defer,
> since it's a pure/memoizable function). See the mutation_controller.py diff
> for the actual implementation. P3/P4/P6/P7 remain open.

## Method

Two independent measurements, both after a 2,000-frame warmup, profiling
frames 2,000–10,000 (population fluctuated 60–105 fish):

1. **cProfile** (call attribution): `WorldRegistry.create_world("tank", seed=42,
   headless=True)`, 8,000 frames. 160.4s total under instrumentation
   (~20.5 ms/frame; instrumentation roughly 4x-inflates, see baseline below).
2. **Built-in PhaseProfiler** (clean wall-time shares): same run shape with
   `TANK_PROFILE_PHASES=1`, reading `engine.profiler.times` directly.
   56.0s wall for 8,000 frames = **7.0 ms/frame** with phase timers;
   an untimed warmup measured **~4.8 ms/frame** true baseline.

Reproduce with:

```bash
# Clean frame timing statistics
python scripts/benchmark_performance.py --frames 2000 --warmup 500

# cProfile attribution
python scripts/benchmark_performance.py --frames 2000 --profile
```

## Where frame time goes (clean phase timers, 8,000 frames)

| Phase profiler bucket | Time | % of wall |
|---|---|---|
| reproduction | 19.8s | **35.3%** |
| decision (behavior/arbitration) | 11.1s | 19.7% |
| action (movement execution) | 9.2s | 16.4% |
| poker (interaction phase) | 5.6s | 9.9% |
| perception (spatial queries) | 3.6s | 6.4% |
| stats collection (frame_end) | 2.5s | 4.5% |
| resolution (collision) | 2.0s | 3.6% |
| spatial grid maintenance | 0.7s | 1.2% |
| soccer | 0.2s | 0.4% |

cProfile agrees: reproduction phase 52.6s of 164s cumulative (32%), entity_act
68.1s (41%), interaction 16.7s (10%), collision 9.9s (6%), frame_end 8.2s (5%).

The single hottest function in the whole profile is
`core/genetics/diversity.py:173 genetic_distance`: **5,301,001 calls, 26.8s
cumulative (~17% of everything)** — and 5,230,631 of those calls come from one
caller: `mutation_controller._is_genetically_isolated`.

---

## Ranked optimization candidates

### P1. Stop computing reproduction mutation contexts for every fish every frame (~25–30% of frame time)

**Evidence.** Over 8,000 frames there were **643,704**
`context_for_parents` computations for **454 actual births** (~1,400 contexts
per birth; ~80 per frame = 2 per living fish, one each from the banked and
trait asexual handlers). Cumulative cost 39.1s of 164s (24%); nearly all of it
is the O(population) genetic-isolation scan
([mutation_controller.py:165](../core/reproduction/mutation_controller.py)).

**Root cause.** [reproduction_service.py](../core/reproduction/reproduction_service.py)
`_handle_banked_asexual_reproduction` (line 292) and
`_handle_trait_asexual_reproduction` (line 328) build the full mutation context
*before* the cheap eligibility gates run. The context is only consumed when an
offspring is actually created (or, in the trait path, to shift the energy
threshold). Meanwhile the per-parent isolation cache
(`_cached_isolation`) is reset **every frame** by `record_diversity_sample`
(called at the top of `update_frame`), so nothing amortizes.

**Fixes**, in order of value; all are pure-compute deferrals — verified that
`context_for_parents` consumes no RNG, so they cannot perturb trajectories:

1. **Banked path:** defer context creation until after
   [asexual_factory.py](../core/reproduction/asexual_factory.py)
   `maybe_create_banked_offspring`'s cheap gates (cooldown, life stage,
   `bank < baby_energy_needed * MIN_NICHE_COST_MULTIPLIER`) pass — e.g. pass a
   lazy factory or move the context call inside, after the bank check. The
   file already uses exactly this pre-screen pattern for the niche-cost scan
   (lines 43–46). Only ~190 banked births occurred in 8,000 frames, so this
   eliminates ~320K context computations nearly for free.
2. **Trait path:** `can_asexually_reproduce` uses the context only to relax the
   energy threshold via `protected_reproduction_ratio`. Pre-screen with the
   *most permissive possible* threshold first; only build the context for fish
   that could pass at all. Same pattern, same safety argument.
3. **Persist the isolation cache across frames.** Key it on fish-list object
   identity exactly as `_behavior_counts_for` already does (the list object is
   rebuilt whenever membership changes, and genomes are immutable after
   creation — the code's own comment at mutation_controller.py:38–43 makes
   this argument). Then each fish pays the O(pop) scan once per population
   change instead of once per frame.

**Expected effect.** Reproduction phase drops from ~35% to low single digits;
overall ~25–30% frame-time reduction. **Risk: low.** Bit-identical trajectories
expected; verify with before/after `--export-stats` diffs on seeds 42, 7, 123.

### P2. Deduplicate per-fish perception queries within one decision pass (~5–8%)

**Evidence.** Each fish queries the same things multiple times per frame:

- Nearest-crab query runs in `has_threat_priority`
  ([actions.py:61](../core/algorithms/composable/actions.py), 304,722 calls via
  `has_survival_priority` in the movement arbiter) and then **again** inside
  `_execute_threat_response` (294,284 calls) during the same arbitration.
- Food is queried up to three times: `has_food_priority` → `_find_nearest_food`
  (4.7s), `score_food_candidates` → `nearby_resources` (275,556 calls), and
  post-move `check_collision_with_food` → `nearby_resources` again
  ([movement_strategy.py:63](../core/movement_strategy.py), 302,481 calls).

Aggregate spatial-query cost: `closest_type` 642K calls/5.8s, `query_food`
586K/3.5s, `query_fish` 419K/3.1s — roughly ~11s of 164s cProfile time is
duplicate work.

**Fix.** A per-fish, per-frame perception memo (nearest crab, food candidate
list) computed at the start of arbitration and reused by the considerations,
behavior execution, and the post-move food-collision check. Within a single
fish's update no other entity mutates, so cached results are exactly what the
duplicate queries would return. Scope the cache strictly to one fish's update
(frame-stamped), never across fish — entity positions change as the entity_act
loop progresses.

**Risk: low-medium.** Behavior-identical if scoping is respected; the danger is
accidentally widening the cache across fish or phases. Worth a focused test
that runs a few hundred frames with and without the cache asserting identical
positions.

### P3. Poker proximity graph is rebuilt from scratch every frame (~5–10%)

**Evidence.** The poker bucket is 9.9% of wall time.
[poker_proximity.py:111](../core/systems/poker_proximity.py)
`_build_proximity_graph` runs every frame and issues one
`nearby_evolving_agents` query per fish per frame (302,435 queries; 9.05s
cumulative for the system's `_do_update`) — regardless of whether any fish is
poker-eligible (cooldowns, energy, engagement).

**Fix options.** (a) Early-out fish that can't play (cooldown/energy) before
querying; (b) build the graph only every N frames; (c) reuse the
collision-phase candidate queries. Option (a) can be trajectory-preserving if
eligibility is checked with the same predicates the game-formation code applies
later; (b) and (c) change *when* games form.

**Risk: medium.** Any cadence change alters trajectories and therefore
benchmark scores (single-seed ecosystem_health swings are documented in
CLAUDE.md). Prefer (a) first; treat (b)/(c) as behavior changes requiring
multi-seed validation. Note poker runs even in standard benchmarks
(`poker_activity_enabled=False` does not disable fish-fish poker), so this
cost is on the benchmark path too.

### P4. `genetic_distance` micro-cost (~large, but mostly fixed by P1)

**Evidence.** 20.2s *self* time — the largest single self-time in the profile.
The per-genome trait profile is already cached
([diversity.py:154](../core/genetics/diversity.py)); the remaining cost is the
per-pair Python loop over ~40 traits with a per-trait kind branch, times 5.3M
calls.

**Recommendation.** Fix the call count (P1) first; it removes ~99% of calls.
Only then consider per-call work. **Caution:** restructuring the loop (e.g.
grouping traits by kind, or numpy) *reorders floating-point summation* and
breaks bit-identical trajectories — and numpy specifically risks the
cross-platform determinism problems already documented for champions. If
per-call cost still matters after P1, the only safe variants are ones that
preserve exact operation order (hoisting lookups, avoiding tuple unpacking).

### P5. Frame-end telemetry: cache `behavior_id`, reconsider per-frame diversity stats (~3–5%)

**Evidence.**

- `_format_behavior_id` ([behavior.py:51](../core/algorithms/composable/behavior.py))
  string-joins four enum names on every `behavior_id` property access —
  **1,328,415 calls, 3.7s**. Callers: the per-frame genetic diversity tracker
  (once per fish per frame) and the mutation controller's behavior counts.
- [genetic_diversity_tracker.py:24](../core/genetic_diversity_tracker.py)
  `update` runs every frame (4.4s cumulative): iterates every fish, reads
  traits, computes 7 population variances.

**Fixes.** Cache the formatted id on the `ComposableBehavior` instance —
sub-behaviors are fixed after construction (mutation builds new instances), so
a lazily-set `_behavior_id_cache` is bit-identical and trivial. For the
tracker, sampling every N frames would save most of the rest, **but** the
diversity score it feeds is read by reproduction thresholds every frame, so
sampling changes trajectories — treat that half as a behavior change, or leave
it. The string cache alone is ~2% and zero-risk.

### P6. Collision phase: per-fish sorted() and isinstance churn (~2–3%)

**Evidence.** [collision_system.py:238](../core/collision_system.py)
`_handle_fish_collisions` sorts each fish's candidate list every frame for
determinism (299,833 `sorted()` calls, 1.8s; 3.05M `collision_sort_key` calls,
1.0s) and re-classifies candidates with isinstance (6.5M calls in this phase).

**Fix.** `query_interaction_candidates` already walks type-specific grid
buckets — return pre-partitioned (fish/food/crab) lists so the handler skips
re-classification, and sort the smaller per-type lists (or presort cell lists
once per frame). Must reproduce the exact same final processing order;
otherwise trajectories change.

**Risk: medium** (easy to silently change ordering). Keep as a careful,
well-tested refactor.

### P7. Spatial grid double maintenance (~1–2% now, grows with population)

**Evidence.** Two overlapping mechanisms run: the spawn phase calls
`update_agent` for **every** entity every frame (804,906 calls), *and*
frame_end triggers a **full grid rebuild** whenever the entity list changed
that frame ([phase_executor.py:202](../core/simulation/phase_executor.py) →
`engine._rebuild_caches` → `spatial_grid.rebuild`) — 3,792 full rebuilds in
8,000 frames (food spawns/consumption dirty the list roughly every other
frame).

**Fix.** Make spawn/removal commits update the grid incrementally
(add_agent/remove_agent at mutation-apply time) and drop the full rebuild.
Cheap at today's population; more valuable if populations grow. Low priority.

---

## Instrumentation bugs found while profiling (fix first — they're cheap)

1. **`main.py --profile-phases` prints all zeros.** The flag rides
   `WorldRegistry.create_world(..., profile_phases=...)` into the mode-pack
   config, but `SimulationConfig.apply_flat_config` (via
   `TankWorldBackendAdapter.__init__`,
   [backend.py:51-78](../core/worlds/tank/backend.py)) drops the key, so
   `engine.profile_phases` stays False. The `TANK_PROFILE_PHASES=1` env var
   *does* enable engine-side profiling, but `main.py` gates the summary print
   on the CLI arg, so env-var users also see nothing. Fix: map
   `profile_phases` in `apply_flat_config`, and print the summary whenever
   `engine.profile_phases` is set. Note
   [IMPROVEMENT_PROPOSALS.md](IMPROVEMENT_PROPOSALS.md) lists item 1.7 (phase
   profiling) as *Shipped* — it has regressed since.
2. **`TankInteractions declares phase INTERACTION but is not scheduled in the
   explicit phase loop`** warning on every headless start — either schedule it
   or correct its declared phase.

## Backend publish path (code inspection only — server was paused, no WS client)

Not measurable live this session, but two clear candidates in
[state_publisher.py](../backend/runner/state_publisher.py) for when a client
is attached:

- `_build_delta_state` (lines 276–282) calls `to_delta_dict()` on **both** the
  current and the previous snapshot of every entity, every frame, just to
  detect changes — two dict allocations per entity per frame. Store the
  previous frame's delta dicts (instead of re-deriving from `EntitySnapshot`s)
  to halve that.
- `_collect_entities` rebuilds the full `EntitySnapshot` list every frame even
  when only computing a delta. Measure with a connected client before
  optimizing further; REST snapshot latency measured ~3ms/35KB while paused.

## Validation protocol for any perf PR

- **Trajectory-preserving changes (P1, P2, P5-string-cache, P6, P7):** run
  `python main.py --headless --max-frames 30000 --export-stats results.json --seed 42`
  before and after; the exported metrics must be identical. Spot-check seeds 7
  and 123 the same way. Then confirm the speedup with
  `python scripts/benchmark_performance.py --frames 2000 --warmup 500`.
- **Trajectory-changing changes (P3 cadence, P4 reordering, P5 sampling):**
  these are behavior changes, not pure optimizations — they need the full
  champion-validation path (multi-seed comparison against `champions/`), and
  remember champions' `config_hash` spans all benchmarks.
- Several hot files are grandfathered in the god-class ratchet at exact line
  counts — keep edits line-neutral there or land the split separately.
- Layer discipline: the instrumentation fixes above are Layer 2 and must not
  ride along in a Layer 1 perf PR.

## Bottom line

Reproduction bookkeeping — not fish behavior — is the single biggest cost in
the simulation today: ~1,400 mutation-context computations per actual birth,
~35% of every frame. P1 alone should cut frame time by roughly a quarter to a
third with zero trajectory risk, taking the headless engine from ~4.8 ms/frame
toward ~3.3 ms/frame at 90-fish populations. P2 and the P5 string cache are
the next-best behavior-preserving wins (~7–10% combined). Everything else is
either small or trades determinism for speed and should be treated as a
behavior change.
