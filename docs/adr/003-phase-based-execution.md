# ADR-003: Phase-Based Execution

## Status
Accepted (2024-12)

## Context

Game loops often have implicit ordering dependencies:
- Physics must run before collision detection
- Entity updates must complete before rendering
- Reproduction should happen after energy consumption

Without explicit ordering:
- Bugs appear when execution order changes
- Data races in parallel execution
- Difficult to reason about system interactions

## Decision

Use an explicit `UpdatePhase` enum to name phase boundaries and support
instrumentation. The `SimulationEngine` executes phases with explicit methods
(e.g., `_phase_frame_start`, `_phase_time_update`, ...). Systems may annotate
their phase using `@runs_in_phase` metadata; the engine can validate these
annotations but does not execute systems via a PhaseRunner.

```python
from core.update_phases import UpdatePhase, runs_in_phase

@runs_in_phase(UpdatePhase.COLLISION)
class CollisionSystem(BaseSystem):
    def _do_update(self, frame: int) -> SystemResult:
        ...
```
## Consequences

### Positive
- **Explicit ordering**: Dependencies are visible in code
- **Self-documenting**: Phase enum describes the update loop
- **Debuggable**: Easy to trace which phase a bug occurs in
- **Parallelizable**: Systems in the same phase could run in parallel
- **Extensible**: New phases can be added without changing systems

### Negative
- **Rigidity**: Hard to run systems out of order when needed
- **Cross-phase communication**: Must use shared state, not direct calls
- **Phase proliferation**: Too many phases become hard to manage

## Phase Responsibilities

| Phase | Purpose | Systems |
|-------|---------|---------|
| FRAME_START | Reset counters, reconcile plants | EntityLifecycleSystem |
| TIME_UPDATE | Day/night cycle | TimeSystem |
| ENVIRONMENT | Ecosystem + detection modifiers | (engine) |
| ENTITY_ACT | Entity updates | (entities) |
| LIFECYCLE | Removals + cleanup | EntityLifecycleSystem helpers |
| SPAWN | Auto food spawning + spatial updates | FoodSpawningSystem |
| COLLISION | Physical collisions | CollisionSystem |
| INTERACTION | Poker proximity + mixed poker | PokerProximitySystem, PokerSystem |
| REPRODUCTION | Asexual + emergency reproduction | ReproductionSystem |
| FRAME_END | Stats + cache rebuild | (engine) |
## Related
- ADR-001: Systems Architecture (systems use phases)
