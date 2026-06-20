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

### 5. Agent state model: mixins vs components (ADR-013 Step 2)
`Fish` still carries **two** parallel models for the same three concerns: the
inheritance mixins (`EnergyManagementMixin`, `MortalityMixin`,
`ReproductionMixin`) *and* the components they delegate to (`EnergyComponent` +
`AgentComponents`). ADR-013 removed the *third* (inert) copy on `GenericAgent`;
the next step is to pick one canonical home — recommend **components** (the model
the architecture champions; mixins are an inheritance escape hatch) — and retire
the other. Behavior-sensitive: the overflow-routing path must stay byte-identical
for determinism and champion benchmarks, so it earns its own ADR + benchmark
validation. Do not start ad hoc.

### 6. `periodic_benchmark` top-fish selection is a silent no-op (latent)
`core/poker/evaluation/periodic_benchmark.py:49` sorts candidates by
`f.components.poker_stats.total_winnings`, but `AgentComponents` has no
`poker_stats` field, so the `hasattr(f.components, "poker_stats")` guard is
*always false* and every fish sorts with key `0` (top-N = first-N in input
order). Same "code written against a field the abstraction doesn't have" theme.
Fix by reading `fish.poker_stats` directly (or exposing it on `components`).
Low urgency (benchmark-only), but it means that selection currently does nothing.

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
