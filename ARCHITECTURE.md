# Architecture Guide

This document describes key architectural patterns and design decisions in the simulation.

## Design Philosophy

The simulation follows these core principles:

1. **Composition over inheritance** - Entities use components; systems use delegation
2. **Protocols over ABCs** - Structural typing for flexibility
3. **Explicit ordering** - Update phases prevent state bugs
4. **Safe mutations** - Request queues prevent iterator invalidation

## Key Patterns

### 1. Protocol-Based Interfaces

**Location:** [`core/interfaces.py`](file:///c:/shared/bolaris/tank/core/interfaces.py)

Use Python `Protocol` for structural typing instead of abstract base classes:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class EnergyHolder(Protocol):
    @property
    def energy(self) -> float: ...

    @property
    def max_energy(self) -> float: ...

    def modify_energy(self, amount: float) -> None: ...
```

**Benefits:**
- Duck typing with type safety
- No inheritance required
- Entities can implement multiple protocols naturally
- IDE autocomplete and type checking work seamlessly

**Examples:** `TraitContainer`, `TelemetrySink`, `PokerPlayer`, `Positionable`

### 2. Update Phases

**Location:** [`core/update_phases.py`](file:///c:/shared/bolaris/tank/core/update_phases.py)

Explicit execution order prevents common state bugs:

```python
class UpdatePhase(Enum):
    ENTITY_ACT = 1      # Agents make decisions
    POKER_GAMES = 2     # Poker interactions resolve
    COLLISIONS = 3      # Collision detection
    REPRODUCTION = 4    # New entities spawn
    LIFECYCLE = 5       # Deaths, state transitions
    CLEANUP = 6         # Remove dead entities
```

**Key rule:** Systems execute in phase order every frame. Entity mutations only apply between phases.

### 3. Entity Mutation Queue

**Location:** [`core/simulation/entity_mutation_queue.py`](file:///c:/shared/bolaris/tank/core/simulation/entity_mutation_queue.py)

**Rule:** Only the engine applies entity mutations, at explicit commit points between phases.

#### Safe entity addition/removal

```python
# ❌ NEVER do this during update phases:
environment.entities.remove(entity)
engine.add_entity(entity)  # Raises RuntimeError if _current_phase is set

# ✅ ALWAYS use the request pattern in game systems:
engine.request_remove(entity, reason="collision")
engine.request_spawn(entity, reason="overflow_food")
```

**Why?** Direct modification during iteration causes `RuntimeError`. The queue batches changes and applies them at safe commit points.

#### Commit Points (6 per frame)

The engine applies queued mutations at strategic points in the update loop:

```python
def update(self):
    self._phase_frame_start()
        self._apply_entity_mutations("frame_start")    # 1. After plant reconciliation

    # ... time, environment phases ...

    self._phase_lifecycle(...)
        self._apply_entity_mutations("lifecycle")      # 2. After death processing

    self._phase_spawn()
        self._apply_entity_mutations("spawn")          # 3. After food spawning

    self._phase_collision()
        self._apply_entity_mutations("collision")      # 4. After collision handling

    self._phase_interaction()
        self._apply_entity_mutations("interaction")    # 5. After poker games

    self._phase_reproduction()
        self._apply_entity_mutations("reproduction")   # 6. After mating
```

**Design rationale:** Frequent commits minimize the window where entities are "pending" but not yet applied.

#### Usage in game systems

```python
# In CollisionSystem
def handle_fish_food_collision(self, fish, food):
    fish.eat(food)
    if food.is_fully_consumed():
        self._engine.request_remove(food, reason="food_consumed")

# In FoodSpawningSystem
def _spawn_food(self):
    food = Food(...)
    self._engine.request_spawn(food, reason="auto_food_spawn")

# In Fish entity (overflow spawning)
from core.util.mutations import request_spawn_in

def handle_overflow_energy(self):
    food = Food(...)
    request_spawn_in(self.environment, food, reason="overflow_food")
```

#### API Decision Tree

```
Do you need to spawn/remove an entity?
├─ Is this a game system/entity?
│  └─ Use request_spawn() / request_remove()
├─ Is this persistence/migration?
│  └─ Use add_entity() / remove_entity() (outside tick only)
└─ Is this a test?
   └─ Use add_entity() / remove_entity() in setup
```

#### Phase Guards

Direct mutation methods block mid-tick calls:

```python
def add_entity(self, entity):
    if self._current_phase is not None:
        raise RuntimeError(
            f"Unsafe call to add_entity during phase {self._current_phase}. "
            "Use request_spawn() instead."
        )
    self._add_entity(entity)
```

This prevents game systems from accidentally bypassing the queue during update().

### 4. Facade Pattern

**Location:** [`core/ecosystem.py`](file:///c:/shared/bolaris/tank/core/ecosystem.py)

`EcosystemManager` composes specialized trackers behind a unified interface:

```python
class EcosystemManager:
    def __init__(self):
        self.population = PopulationTracker()
        self.lineage = LineageTracker()
        self.poker_manager = PokerStatsManager()
        self.reproduction_manager = ReproductionStatsManager()
        self.energy_tracker = EnergyTracker()
```

**Benefits:**
- Single point of access for ecosystem data
- Each tracker has focused responsibility
- Easy to add new trackers without changing client code

### 5. System Architecture

**Location:** [`core/systems/base.py`](file:///c:/shared/bolaris/tank/core/systems/base.py)

Systems follow a consistent pattern:

```python
class MySystem(BaseSystem):
    def _do_update(self, frame: int) -> SystemResult:
        # System logic here
        return SystemResult(
            entities_affected=count,
            details={"custom_stat": value}
        )
```

**Key features:**
- `SystemResult` for debugging and metrics
- Systems registered by phase
- Enable/disable individual systems
- No direct entity manipulation (use requests)

## Common Gotchas

### 🚨 Entity Mutations During Iteration

```python
# ❌ BAD - causes RuntimeError
for fish in fishes:
    if fish.is_dead():
        environment.entities.remove(fish)

# ✅ GOOD - queued for batch processing
for fish in fishes:
    if fish.is_dead():
        environment.request_remove(fish)
```

### 🚨 RNG Usage

Always use the engine's RNG for deterministic behavior:

```python
# ❌ BAD - non-deterministic
import random
x = random.randint(0, 100)

# ✅ GOOD - uses engine's seeded RNG
x = self.engine.rng.randint(0, 100)
```

### 🚨 Direct System Access

Systems should be accessed through the registry, not stored as direct references:

```python
# ❌ BAD - tight coupling
collision_system = engine.collision_system

# ✅ GOOD - registry lookup
collision_system = engine._system_registry.get_system("Collision")
```

## Extending the Simulation

### Adding a New Entity Type

1. Create class in `core/entities/`
2. Inherit from `Entity` or `Agent`
3. Implement relevant protocols (`EnergyHolder`, `Positionable`, etc.)
4. Register in `EntityManager` if needed
5. Add spawning logic to appropriate system

### Adding a New System

1. Create class in `core/systems/`
2. Inherit from `BaseSystem`
3. Implement `_do_update(frame) -> SystemResult`
4. Register in `SimulationEngine.__init__()` with appropriate phase
5. Return meaningful `SystemResult` for debugging

### Adding a New Update Phase

1. Add enum value to `UpdatePhase` in correct order
2. Update `PHASE_DESCRIPTIONS` dict
3. Register systems for new phase
4. Document ordering requirements

## Testing Patterns

### Determinism Tests

```python
def test_determinism():
    eng1 = SimulationEngine(seed=42)
    eng2 = SimulationEngine(seed=42)

    for _ in range(100):
        eng1.update()
        eng2.update()

    assert eng1.get_state() == eng2.get_state()
```

### System Tests

```python
def test_system_returns_result():
    system = MySystem(engine)
    result = system.update(frame=1)

    assert isinstance(result, SystemResult)
    assert result.entities_affected >= 0
```

## Further Reading

- **Determinism:** See `tests/test_determinism.py` for enforcement patterns
- **Protocols:** Python docs on [Protocol](https://peps.python.org/pep-0544/)
- **Component Design:** Fish class uses `EnergyComponent`, `LifecycleComponent`, etc.

---

## World Backends Plugin Model

**Location:** [`core/worlds/`](file:///c:/shared/bolaris/tank/core/worlds/) + [`backend/world_registry.py`](file:///c:/shared/bolaris/tank/backend/world_registry.py)

The simulation supports multiple world types (Tank, Petri, Soccer) through a registry pattern:

```python
# Register a world type
register_world(
    world_type="tank",
    factory=_create_tank_world,
    view_mode="side",
    display_name="Fish Tank",
)

# Create worlds via registry (NOT direct imports)
world, snapshot_builder = create_world("tank", seed=42)
```

**Import Boundaries:**
- `core/worlds/*` must not import `backend/*` or `frontend/*`
- `backend/*` uses registry to access worlds, not direct `core/worlds/tank/*` imports
- Only `backend/world_registry.py` may import world implementations for registration

**Why this matters:** Keeps `core/` portable and testable without server dependencies.

---

## Renderer Consumes Snapshot Only

**Principle:** The frontend receives serialized JSON snapshots, never imports Python modules.

```
┌─────────────┐     step()      ┌──────────────────┐
│ WorldBackend│────────────────▶│  SnapshotBuilder │
└─────────────┘                 └────────┬─────────┘
                                         │ build_snapshot()
                                         ▼
                               ┌──────────────────┐
                               │   JSON Snapshot  │
                               └────────┬─────────┘
                                WebSocket broadcast
                                         │
                                         ▼
                               ┌──────────────────┐
                               │  React Frontend  │
                               └──────────────────┘
```

**Benefits:**
- Frontend is language-agnostic (could be any renderer)
- Snapshots are serializable for replay/persistence
- No circular dependencies between core and rendering

---

## Policies Are Pure

**Principle:** Behavior algorithms (policies) are pure functions of observable state.

```python
# ✅ GOOD - Pure policy, uses only observation
class GreedyFoodSeeker(BehaviorAlgorithm):
    def decide(self, fish: Fish, env: Environment) -> Vector2:
        nearest_food = env.get_nearest_food(fish.position)
        return (nearest_food.position - fish.position).normalized()

# ❌ BAD - Policy calls engine/ecosystem methods
class BadPolicy(BehaviorAlgorithm):
    def decide(self, fish: Fish, env: Environment) -> Vector2:
        self.engine.spawn_food()  # Side effect!
        self.ecosystem.log_event()  # Coupling to ecosystem!
        return Vector2.zero()
```

**Rules:**
- Policies receive observations, return actions
- No `engine.X()` or `ecosystem.X()` calls inside policies
- Side effects happen in systems, not policies
- This enables policy replay, testing, and ML training
