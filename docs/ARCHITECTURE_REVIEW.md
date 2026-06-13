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
`Result` for expected/inline-handled ones). ~90 generic `raise ValueError`/
`RuntimeError` sites remain. Migrate **opportunistically** when touching a
module — no big-bang rewrite. Do not delete the currently-unused `TankError`
subclasses; the ADR gives them a job.

### 4. Module dependency cycles (watch item — large effort)
There are ~750 function-level (in-function) imports in `core/`, used to route
around circular dependencies. This is real debt, but untangling it is a *large,
risky* refactor, not a small safe change. **Measure before acting**; prefer
breaking cycles opportunistically when a module is already being restructured.

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
