# ADR-011: Keep Minigames Out of the Generic Core

## Status

Accepted (2026-06) — first slice landed; remaining surface scoped below.

## Context

Tank World is a generic multi-agent simulation that *hosts* minigames (poker,
soccer). The generic spine is meant to be domain-agnostic:

- `SimulationEngine` — "the slim orchestrator" (ADR-001)
- `MultiAgentWorldBackend` — "domain-agnostic world interface" (its own words)
- `core/interfaces.py` — "the single source of truth for all protocols"

In practice, minigame concepts had leaked into all three:

- `MultiAgentWorldBackend.get_recent_poker_events()` — a **poker** method on the
  interface whose docstring says *domain-agnostic*.
- `SimulationEngine` carried a cluster of minigame-specific methods
  (`add_poker_event`, `handle_mixed_poker_games`, `handle_poker_result`,
  `add_plant_poker_event`, `get_recent_poker_events`, plus the soccer
  `add_soccer_event` / `get_recent_soccer_events` /
  `*_soccer_league_live_state`). The engine had become the *mailbox* between
  minigame systems (writers) and the backend (UI readers).
- `core/interfaces.py` defined **two** protocols for "can play a skill game":
  `SkillfulAgent` (strategy-based, implemented by `Fish`) and `SkillGamePlayer`
  (component-based) — the latter never satisfied by any entity and exercised
  only by a `@pytest.mark.skip` test.

This matters for the project's stated goal — *fewer bugs as we extend*. Every
new minigame otherwise forces edits to the "generic" layer, the generic layer
can't be understood or tested without the specifics, and duplicate protocols
make every call site guess which one to trust.

A real `EventBus` (`core/events/event_bus.py`) already exists and is the
correct spine: entities emit domain events, the ecosystem/telemetry subscribe,
and `soccer_system` already emits goals through it. The leak is a *separate*,
older "UI event stream" mechanism bolted onto the engine.

> **Principle:** dependencies flow specific → generic, never the reverse. A
> minigame is a plugin; the generic core must not name it. One capability gets
> one protocol.

## Decision

Keep `SimulationEngine`, `MultiAgentWorldBackend`, and `core/interfaces.py`
free of minigame-specific surface. Minigame systems own their event streams;
the backend reads minigame UI events from the systems (it already aggregates
them into one `{type, data, frame}` list), not via engine facades. Domain
events flow on the `EventBus`.

### Shipped in this slice (safe subtraction)

1. **World interface de-leaked.** Removed
   `MultiAgentWorldBackend.get_recent_poker_events` — it had **zero** callers
   (the Tank UI path calls the engine directly). The base interface is genuinely
   domain-agnostic again.
2. **Dead engine pass-throughs removed.** `add_poker_event` (no callers) and
   `handle_mixed_poker_games` (the coordinator already calls
   `poker_system.handle_mixed_poker_games()` directly) deleted.
3. **Skill-game protocol consolidated.** Removed `SkillGamePlayer` (and its
   skipped test and now-unused `SkillGameComponent` import); `SkillfulAgent` is
   the one protocol for skill-game participation.

All three are verifiable subtractions: no production caller existed.

### Soccer event stream moved off the engine (follow-up, shipped)

The four soccer methods (`add_soccer_event`, `get_recent_soccer_events`,
`set/get_soccer_league_live_state`) were removed from `SimulationEngine`. The
`SoccerEventManager` now owns its stream end to end: it gained a
`frame_provider` (so callers don't thread `frame_count`) plus `record_outcome`
/ `recent`, and the engine exposes it as a single `soccer_events` property.
Phase hooks, the backend adapter, the soccer runner command, and the
`SoccerMixin` were migrated to `engine.soccer_events.*`; the `hasattr(engine,
"<method>")` capability gates became `hasattr(engine, "soccer_events")`,
preserving "does this world support soccer?" detection.

Behavior-neutral (UI event buffering, not the RNG path): `ecosystem_health_10k`
seed 42 is byte-identical (4.791812102268079). Verified by the websocket-payload,
metrics-trends, and soccer-integration tests plus mypy.

### Poker facade methods removed (follow-up, shipped)

The three poker facade methods (`handle_poker_result`, `get_recent_poker_events`,
`add_plant_poker_event`) were removed from `SimulationEngine`. `PokerSystem` is
already a registered system exposed as `engine.poker_system`, so callers now use
it directly:

- `poker_proximity` → `engine.poker_system.handle_poker_result` (guarded)
- `tank` backend poker-event collection → `engine.poker_system.get_recent_poker_events`
- `PokerSystem.handle_mixed_poker_games` previously bounced plant events through
  `engine.add_plant_poker_event`, which delegated *right back* to the same
  `PokerSystem` (a circular round-trip guarded by `hasattr`). It now calls
  `self.add_plant_poker_event` directly; the dead engine hop and guard are gone.

Behavior-neutral: `ecosystem_health_10k` seed 42 is byte-identical
(4.791812102268079); poker-system, mixed-poker-with-plants, adapter-hot-path,
and websocket-payload tests pass, plus mypy.

### Dead poker event alias removed (follow-up, shipped)

`engine.poker_events` was removed. The constructor allocated a deque that setup
later overwrote with `PokerSystem.poker_events`, so ownership was implicit and
the generic engine still exposed poker-specific state. Backend world hooks and
tests now read from the owning system directly: `engine.poker_system.poker_events`.
The frontend payload key remains `snapshot.poker_events`; only the internal
source of that payload changed.

### Tank adapter minigame facades removed (follow-up, shipped)

`TankWorldBackendAdapter.get_recent_poker_events()` and
`TankWorldBackendAdapter.get_soccer_league_live_state()` had no production
callers after the hook migration. They were deleted so the adapter stays focused
on the world backend contract; feature hooks now read poker events from
`engine.poker_system` and soccer live state from `engine.soccer_events`.

## Consequences

**Positive**
- The generic interfaces no longer name poker/soccer; a new minigame doesn't
  touch them.
- One skill-game protocol; call sites stop guessing.
- Pure subtraction — no behavior change, provable by the gate staying green.

**Negative**
- The engine still hosts the *used* minigame methods, so the decoupling is
  partial. Tracked above; honesty over a misleading "done".

## Related
- [ADR-001: Systems Architecture](001-systems-architecture.md)
- [ADR-002: Protocol-Based Design](002-protocol-based-design.md)
- [ADR-010: Unify Movement Drive Arbitration](010-movement-arbitration.md)
  (same theme: lifting ball/soccer logic out of generic movement)
