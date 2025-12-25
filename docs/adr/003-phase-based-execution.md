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

Use an **explicit `UpdatePhase` enum** to order simulation updates:

```python
class UpdatePhase(Enum):
    """Defines the order of simulation update phases."""
    
    ENVIRONMENT = 1      # Day/night, weather
    ENTITY_UPDATE = 2    # Movement, AI decisions
    COLLISION = 3        # Collision detection/response
    REPRODUCTION = 4     # Spawning new entities
    LIFECYCLE = 5        # Death, cleanup
    STATISTICS = 6       # Metrics, analytics
```

Systems declare their phase using the `@runs_in_phase` decorator:

```python
@runs_in_phase(UpdatePhase.COLLISION)
class CollisionSystem(BaseSystem):
    def _do_update(self, frame: int) -> SystemResult:
        ...
```

The `SimulationEngine` then executes phases in order:

```python
def update(self) -> None:
    for phase in UpdatePhase:
        self._execute_phase(phase)
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
| ENVIRONMENT | Time, weather, global state | TimeSystem |
| ENTITY_UPDATE | Individual entity AI/movement | (handled per-entity) |
| COLLISION | Detect and resolve collisions | CollisionSystem |
| REPRODUCTION | Create new entities | ReproductionSystem |
| LIFECYCLE | Deaths, cleanup | EntityLifecycleSystem |
| STATISTICS | Metrics, logging | StatsSystem |

## Related
- ADR-001: Systems Architecture (systems use phases)
