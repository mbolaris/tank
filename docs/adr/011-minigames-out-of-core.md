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

### Scoped, not yet done (the load-bearing surface)

The still-used engine methods — poker (`handle_poker_result`,
`add_plant_poker_event`, `get_recent_poker_events`) and soccer
(`add_soccer_event`, `get_recent_soccer_events`,
`set/get_soccer_league_live_state`) — are genuine integration points between
systems and the backend. Removing them is a real refactor: the
`PokerSystem` / `SoccerEventManager` should own their recent-event streams and
the backend should read them via the system registry (`engine.get_system(...)`)
or a generic `get_recent_minigame_events()` aggregator, with writers reaching
the stream directly rather than through an engine facade.

This was deliberately **deferred**: it touches backend hooks, phase hooks, and
UI serialization, so it carries regression risk that the dead-code removal does
not. It is the next increment, not this one. Shipping the safe slice now (and
saying so) is preferred over a large risky change that mixes pure subtraction
with behavior-affecting wiring.

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
