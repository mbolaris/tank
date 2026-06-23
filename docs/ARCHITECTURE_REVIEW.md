# Architecture Review: Tank World

> **Last reviewed: 2026-06.** This is a living document. When you complete an
> item under "Open items," move it to "Recently completed" with a one-line note
> so the next reader (human or agent) doesn't redo finished work.

## Executive summary

Tank World has a **solid architectural foundation**: protocol-based interfaces,
a slim phase-based engine that delegates to focused collaborators, a
deferred-mutation queue that fails loudly on misuse, and a factory/registry for
worlds. The abstractions are largely *correct*.

The standing risk to "fewer bugs as we extend" is not wrong structure — it is
**half-finished abstractions and documentation drift**. This review tracks both,
and is biased toward **quality over quantity** (removing and finishing, not
adding).

## What's working well ✓

1. **Slim orchestrator + delegation.** `SimulationEngine` coordinates; it does
   not contain business logic. Work is delegated to `PhaseExecutor`,
   `SystemCoordinator`, `MutationExecutor`, and `FrameAggregator`. See ADR-003.
2. **Protocol-based interfaces.** `core/interfaces.py` is the single source of
   truth for capability protocols (`EnergyHolder`, `Movable`, `Mortal`, …),
   following the Interface Segregation Principle. See ADR-002.
3. **Deferred-mutation queue with guards.** `add_entity()`/`remove_entity()`
   *raise* if called mid-phase; callers must use `request_spawn()`/
   `request_remove()`. This eliminates mid-iteration mutation bugs by design.
4. **Explicit phase ordering.** The update loop runs named phases in a fixed
   order, so "what happens when" is always answerable. See ADR-003.
5. **Template Method for systems.** `BaseSystem.update()` handles enabled-checks
   and metrics; subclasses implement `_do_update()` and always return a
   `SystemResult`. See ADR-001.
6. **Component composition.** Both `Fish` and `Plant` are built from focused
   components rather than inheritance bloat. See ADR-004.
7. **Factory/registry for worlds.** `WorldRegistry` + `SystemPack` add a new
   world by registering a factory — no scattered `if mode == …` branching.
8. **ADRs + decision log.** Significant choices are written down in `docs/adr/`.

## Recently completed (do not re-do)

These were open items in earlier reviews and are now **done** (verified against
the code, 2026-06):

| Item | Evidence |
|------|----------|
| Dead skill-game framework removed (~2,900 LOC; principle #6) | The generic `SkillGame` framework was a parallel abstraction to the real poker path: `core/poker`/`core/mixed_poker` never imported `core.skills`, no `SystemPack` wired `SkillGameSystem`, and only scripts/tests constructed it. Removed `core/skills/` (RPS, number-guessing, poker_adapter, base, config), `core/skill_game_system.py`, `core/fish/skill_game_component.py`, the `SkillfulAgent` protocol, and the dead `Fish.get_strategy/set_strategy/learn_from_game` surface. The genuinely-live bit — the poker-eligibility gate, misnamed `can_play_skill_games` — was kept and renamed `Fish.can_play_poker`, and `movement_observations` now reads it directly (dropping a `getattr`-lie per Open-item #5). **Determinism note:** byte-identical (seed-42, 30k frames; golden-replay guard green). The post-poker reproduction path had drawn `engine.rng.random()` only to pick whose (always-empty) skill strategies the offspring inherited; dropping that draw would have reshuffled the shared stream for every poker-on config and tripped `test_replay_golden`, so it is **retained as an explicit determinism anchor** in `_create_post_poker_offspring` (documented inline; remove via a coordinated re-record when that path next changes). A clean example of *cosmetic minigame state coupled to the core RNG stream* — the motivation for `docs/POKER_SEAM_PROPOSAL.md`. |
| Unused `ParameterRegistry` removed (137 LOC; principle #6) | `core/parameters/` was a read-only facade over three bounds tables that its own docstring said was "intended for tooling … mutation engines" — but the mutation engine reads the source tables directly and nothing but one test imported it. Deleted the package and `tests/core/test_parameter_registry.py`. |
| God-class ratchet now actually ratchets | `tests/test_god_class_limits.py` skipped legacy files entirely (so they could regrow unbounded), tracked only a count, and carried 6 stale/deleted entries with comments that lied (`fish.py # 1201` — was 810). Rewrote it: `LEGACY_MAX_LINES` is now a **path-keyed dict pinned to each file's current size** (resolving the 4-way `engine.py` basename collision), `test_no_new_god_classes` enforces the per-file ceiling against regrowth, and `test_legacy_list_is_current` fails when a listed file drops under 500 or disappears — forcing harvest. Net: 45→33 honest, enforced pins; 7 already-refactored files (e.g. `environment.py` 433, `behavioral.py` 270) harvested. |
| Documentation drift corrected | `ARCHITECTURE.md`/`CLAUDE.md` cited module paths that no longer exist after the package consolidations: `core/poker_system.py`→`core/poker/integration/poker_system.py`, `core/reproduction_service.py`/`_system.py`→`core/reproduction/…`, `composable.py`→`composable/` (package). Also rewrote the doc sections describing the just-deleted skill framework (the "Skill Game System" section, the `SkillfulAgent`/`SkillGamePlayer` protocol entries) to describe the real poker path. |
| Plant uses components (was: inline duplication) | `core/plant/` — `PlantEnergyComponent`, `PlantNectarComponent`, `PlantPokerComponent`, `PlantMigrationComponent`, `PlantVisualComponent` |
| `Entity` → `MobileEntity` → `Agent` hierarchy | `core/entities/base.py` (`Entity`, `MobileEntity`, `Agent`); static entities no longer inherit movement/AI |
| `_emit_event()` deduplicated to base class | `core/entities/base.py` |
| Deprecated poker recording methods removed | gone from `core/ecosystem.py` |
| Deprecated engine facades removed | `cleanup_dying_fish`, `record_fish_death`, `handle_reproduction` removed from the engine |
| Dead `poker_participant_manager` module removed | cooldowns now live on entities via the `PokerPlayer` protocol |
| Error-handling strategy documented | ADR-007; `ConfigurationError` adopted in `SimulationConfig.validate()` |
| `SystemResult` contract made uniform | every `_do_update` now returns `SystemResult` |
| Duplicate betting-round enum collapsed | `MultiplayerBettingRound` is now an alias of `BettingRound` |
| `core/protocols.py` re-export shim removed | import `core.interfaces` directly |
| `core/` module-load import graph is a verified DAG (was: 3 latent facade cycles) | cycles broken; `tests/test_import_acyclic.py` guards it; ADR-008 |
| Unused `PhaseRunner` execution model removed (finish-or-delete) | `core/update_phases.py` keeps only the `UpdatePhase` taxonomy the engine uses |
| `core/worlds` mode registration made lazy (was: eager at import → `core.worlds`↔`core.simulation` import-time cycle) | `core/worlds/registry.py`; de-poisons `core.worlds.*` imports; ADR-008 |
| Persistence/versioning contract made honest (one validated snapshot version; legacy-save shims removed; finish-or-delete) | `core/contracts/version.py` keeps a single `SNAPSHOT_VERSION` (dead, unconsumed `ENTITY_TRANSFER_VERSION`/`WS_PAYLOAD_VERSION` removed; misplaced module docstring fixed); `core/transfer/entity_transfer.py` drops the unvalidated per-entity version stamp and the dead fish `movement_policy_id` shim (`genome_codec` already defaults it); `core/genetics/plant_genome.py` replaces the *random* `strategy_type`/`fractal_type` migration with a deterministic default (removes RNG from restore); `backend/world_persistence.py` `_resolve_engine()` replaces silent `except: pass` paths; `docs/persistence.md` refreshed to v3.0 with real APIs |
| Engine-level poker event storage removed | `PokerSystem` owns `poker_events`; backend hooks and tests read `engine.poker_system.poker_events` directly, leaving the generic engine without duplicate poker-specific state. See ADR-011 |
| SystemResult contract made fail-fast | `BaseSystem.update()` now raises `TypeError` when `_do_update()` returns anything other than `SystemResult`, instead of normalizing invalid `None` returns to an empty result |
| Tank adapter minigame event facades removed | `TankWorldBackendAdapter` no longer exposes `get_recent_poker_events()` or `get_soccer_league_live_state()` pass-throughs; backend hooks read `PokerSystem` and `SoccerEventManager` directly |
| GenericAgent state layer collapsed (was: energy/death/reproduction duplicated by Fish mixins *and* the base) | `core/entities/generic_agent.py` — removed the shadowed, divergent `energy`/`max_energy`/`size`/`modify_energy`/`is_dead`/`can_reproduce` (the mixins on `Fish`, its only subclass, always won the MRO; `GenericAgent.modify_energy` had silently diverged — it dropped overflow energy instead of banking it for reproduction) plus the now-unread `AgentComponents.energy` field; made `update` abstractness real via `ABC`. Behavior-neutral (seed-42 30k-frame headless byte-identical). ADR-013, extending ADR-009 to the state layer |
| Agent/component docs realigned to code (ADR-009 step 4 finished) | CLAUDE.md, `docs/ARCHITECTURE.md` (7 spots incl. runnable examples), and the `core/entities/base.py` module docstring no longer describe the deleted Perception/Locomotion/Feeding components or the `perceive/decide/act` loop; hierarchy now shown as `Entity → MobileEntity → Agent → GenericAgent → Fish` |
| Orphaned `soccer_evolution` experiment removed | `core/experiments/` (module + empty package) and its two only-consumer tests deleted; no production code imported it, and it used bare `random` against the `core.util.rng` determinism rule |
| ADR-013 Step 2 resolved (mixin/component layering kept) | Investigated the Fish mixin↔component split: intentional layering (Fish/world *policy* in the mixins over pure-state components), not a duplicate model — so "retire the mixins" was withdrawn. Deleted the one real dead duplicate (`EnergyManagementMixin._apply_energy_gain_internal`, an uncalled clone of `modify_energy`'s overflow path) and rewrote the docstrings to state the policy-vs-state, Fish-only nature. Behavior-neutral. ADR-013 Step 2 |
| Benchmark diversity metric made cross-process deterministic (was: process-randomized `hash(str)`) | `core/util/stable_hash.py` adds `stable_algorithm_id` (CRC32); `genetic_diversity_tracker` now counts `behavior_id` strings directly (deterministic + collision-free), and `enhanced_statistics`/`poker_adapter` use the stable id. `ecosystem_health_10k` now scores identically across separate processes; both tank champions still reproduce (`validate_reproduction` passes), so no re-baseline was needed. `tests/test_stable_hash.py` (incl. a subprocess cross-process check) guards it. ADR-014. The four telemetry `algorithm_id` sites were deliberately left for the separate keying fix — now done in ADR-015 |
| Per-algorithm stats re-keyed to the composable `behavior_id` (was: registration by legacy `ALL_ALGORITHMS` enumerate-index vs telemetry by `behavior_id` hash → counters never recorded, names always "Unknown") | Registration (`population_tracker._init_algorithm_stats`) and the 5 telemetry sites now both derive the key from `behavior_id` via `stable_algorithm_id`; `ComposableBehavior.all_behavior_ids()` enumerates the 384-combo key space. End-to-end: a seed-42 run now records births/deaths/reproductions across ~91 behaviors with real names (was ~0 / "Unknown"). Telemetry-only — champions still reproduce. `tests/test_algorithm_tracking.py` rewritten to cover the shared id space. ADR-015 |
| Poker-benchmark fish selection fixed (was: silent no-op) | `periodic_benchmark` and `comprehensive_benchmark` ranked fish by `f.components.poker_stats.total_winnings` — a field that exists on neither `AgentComponents` nor `FishPokerStats` — so the sort key was always 0 and "top fish" = input order. Now rank by `fish.poker_stats.get_net_energy()` (won − lost − house cuts; `None` until the fish plays). `tests/test_poker_benchmark_selection.py` proves the ordering. Item 5 |
| Ball drive lifted out of generic movement (ADR-010 follow-through) | `_get_ball_pursuit_velocity` removed from `core/movement_strategy.py` (the generic strategy no longer imports `core.entities.ball.Ball` or carries any soccer concept). The drive is now the self-contained `BallPursuitConsideration` + `ball_pursuit_velocity()` in `core/movement/ball_pursuit.py`, owning its own energy gate and survival-yield (the "self-contained Consideration" ADR-010 designed). Byte-identical seed-42 30k. Residual (full relocation to `core/minigames/soccer` via IoC registration) tracked in Open item 5 |
| Internal movement path no longer round-trips the external-brain action layer | `AlgorithmicMovement.move()` clamped each fish's desired velocity inline (`MAX_ACTION_VELOCITY`) instead of allocating an `Action` per fish per frame via `translate_action` wrapped in a bare `except Exception`. The translation registry (`core/actions`) remains the seam for *external* brains; it was never needed on the internal composable-behavior path, where it only re-applied the same ±5.0 clamp. Removes the silent-fallback ADR-007 flagged at `movement_strategy.py`. Byte-identical seed-42 30k; `tests/core/test_movement_actions.py` rewritten to assert the inline-clamp contract |
| `getattr` lies removed from ball pursuit | `getattr(fish, "max_speed", 2.0)` (Fish has **no** `max_speed`; only `Food`/`Ball` do — the default always fired) → explicit `BALL_PURSUIT_TARGET_SPEED`; `getattr(fish, "energy"/"max_energy", …)` (Fish is an `EnergyHolder`, always has them) → direct access. Genuinely-optional `environment.ball` access *kept* as `getattr` — the point is to distinguish optional from guaranteed, not to ban the tool |

## Open items

### 1. EcosystemManager facade surface (low priority)
`core/ecosystem.py` exposes ~20 `@property` delegations to sub-trackers
(`PopulationTracker`, `PokerStatsManager`, …). Each new tracker field tends to
add another property. Consider keeping the 5–7 most-used and letting callers
reach sub-trackers directly (`ecosystem.population.current_generation`). This is
a facade-size trade-off, not a bug — revisit only if the boilerplate grows.

### 2. Algorithm sprawl, governed by ADR-006 (in progress)
~15 monolithic food-seeking algorithms in `core/algorithms/food_seeking/` are
superseded by `ComposableBehavior`. ADR-006 deprecates them in stages; **removal
is blocked on champion re-baselining** (Layer 2 concern), so they are
intentionally retained for now. Do not remove ad hoc.

### 3. Error-handling migration (incremental, per ADR-007)
ADR-007 defines the convention (exceptions for exceptional/propagating failures;
`Result` for expected/inline-handled ones). Migrate **opportunistically** when
touching a module — no big-bang rewrite. Do not delete the currently-unused
`TankError` subclasses; the ADR gives them a job.

Adopted so far (reference examples to copy): `ConfigurationError`
(`SimulationConfig.validate`, every unknown-world/mode lookup), `GeneticsError`
(`Genome.assert_valid`), and `PersistenceError` (snapshot restore;
`VersionMismatchError` now subclasses it). Many generic `raise ValueError`/
`RuntimeError` sites remain — note that genuine *argument-type* misuse (e.g.
`"interval must be >= 1"`) correctly stays `ValueError`; only domain failures
move to the hierarchy.

### 4. In-function import debt (now measured & guarded, per ADR-008)
`core/` carries hundreds of function-level (in-function) imports originally
added to route around circular dependencies. Measurement (ADR-008) showed the
module-load graph was only *accidentally* tangled — three sibling-via-facade
cycles — now broken and locked acyclic by `tests/test_import_acyclic.py`. With
cycles unable to reappear silently, the remaining in-function imports are mostly
*defensive* rather than load-bearing: promote them to module scope
**opportunistically** when you already touch a module, leaning on the acyclicity
test to prove nothing re-tangles. Still no big-bang rewrite — the value is
incremental and the test is the safety net.

**Progress (2026-06):** the `core.util.rng` leaf helpers (`require_rng`,
`require_rng_param`, `get_rng_or_default`) — the single largest in-function
pattern at 121 imports across 51 files — are now imported at module scope. The
module is a pure leaf (imports only stdlib, nothing from `core`), so the
promotion is unconditionally cycle-safe and was the obvious first cut; a seed-42
headless before/after diff confirmed identical simulation state (only wall-clock
timing differed). This continues the `poker.py` cleanup in commit `d6543a8`.
A reusable picker for the next pass: a promotion of `from X import …` inside
module `M` is safe iff `X` cannot already reach `M` in the module-load graph —
compute this with the reachability check over the graph that
`tests/test_import_acyclic.py` builds (validate the winners with a
fresh-interpreter import too, since `core/__init__.py` eagerly imports
subpackages and the static graph cannot see import-time execution edges).

Building on that, the **`core/algorithms/` subsystem is now fully converted**
(0 in-function imports): `core.entities` (runtime `Crab`/`Food`/`Fish`), config
constants, `SignalType`, `MemoryType`, and `math` were hoisted to module scope;
type-only `core.world` imports moved into `TYPE_CHECKING` (local annotations are
never evaluated, so they need no runtime import); and redundant re-imports
(e.g. `Vector2`, already re-exported via `core.algorithms.base`) were dropped.
Aliased imports (`Fish as FishClass`) stay as runtime aliases alongside the
type-only `Fish`. Determinism was reconfirmed by a seed-42 headless before/after
diff (identical simulation state). ~199 cycle-safe in-function imports remain
across the rest of `core/`. Still incremental, still test-backed.

### 5. Defensive access erodes the protocol layer (new, systemic, opportunistic)
`core/` (excl. tests) carries ~354 `getattr`, ~193 `hasattr`, and ~60 bare
`except`. The protocol layer (`core/interfaces.py`) exists precisely so callers
*don't* probe for attributes — yet much code routes around it with
`getattr(x, "field", default)`, which converts a loud `AttributeError` (fixed in
minutes) into a silent wrong value (found, if ever, after a 30k-frame
archaeology dig). The `getattr(fish, "max_speed", 2.0)` bug (Open-item-4 sibling,
now fixed) is the archetype: the attribute never existed, the default was
load-bearing, and a downstream clamp hid the consequence — invisible until two
layers change.

Treat this exactly like the in-function import debt (item 4): **opportunistic,
test-backed, no big-bang.** When you touch a module, replace
protocol-guaranteed `getattr`/`hasattr` with direct access and let it fail loud;
keep `getattr` only for *genuinely optional/foreign* attributes (e.g.
`environment.ball`, which may not exist). A good first sweep is the rest of
`core/movement_strategy.py` and the `Fish.__init__` config-defaulting chain
(`getattr(environment, "simulation_config", None)` → `…soccer` → `…enabled`),
which also mixes construction with save-migration self-healing — extract that to
a `Genome.normalize()` invoked at load time (SRP: a constructor should
construct).

### 6. Movement-consideration IoC (deferred, enables full ADR-011 compliance)
`default_considerations()` (generic `core/movement`) still *names* the ball
drive. The clean form is registration: the tank/soccer pack inserts its
considerations into the arbiter, so the generic factory lists only generic
drives and a new minigame touches zero generic code. Blocked on a small seam —
`AlgorithmicMovement` is constructed arg-less in 4 sites (`entity_factory`,
`reproduction_service`, `entity_transfer`, `backend/runner/commands/fish`), so
the arbiter has no pack/config access today. Determinism note: ball pursuit is a
no-op (returns `None` *before* any RNG draw) when no ball is present, so adding
it conditionally is RNG-neutral — the migration can be byte-identical. See
ADR-010 follow-up and ADR-011.

## Design principles to maintain

1. **Composition over inheritance** — extend the component pattern, don't grow
   class hierarchies.
2. **Single responsibility** — one reason to change per component/system.
3. **Explicit over implicit** — keep the explicit phase ordering; don't
   auto-magic system execution order.
4. **Protocols for contracts** — keep `core/interfaces.py` canonical.
5. **Fail fast, fail loud** — the mutation-queue guards and config validation
   raise on misuse. Prefer this over silent fallbacks.
6. **Finish or delete abstractions** — a half-adopted abstraction (used in 2 of
   N call sites) costs more than it saves. Commit to it or remove it.

## Related
- `docs/adr/` — Architecture Decision Records (ADR-001 … ADR-007)
- `docs/ARCHITECTURE.md` — full technical architecture
- `CLAUDE.md` — project intelligence and conventions
