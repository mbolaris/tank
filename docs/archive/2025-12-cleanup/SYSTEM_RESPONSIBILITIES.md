# System Responsibilities

This document defines clear responsibilities for each system in the simulation architecture.

## Core Principle

> **Each system has ONE primary responsibility.**
> If you're adding code, ask: "Which system owns this responsibility?"

---

## Systems Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    SimulationEngine                         │
│  (Orchestrator - coordinates systems, owns no game logic)  │
└─────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ CollisionSystem │  │  PokerSystem    │  │ LifecycleSystem │
│   (COLLISION)   │  │   (COLLISION)   │  │   (LIFECYCLE)   │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ReproductionSys  │  │ SkillGameSystem │  │   TimeSystem    │
│ (REPRODUCTION)  │  │   (COLLISION)   │  │  (ENVIRONMENT)  │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## CollisionSystem

**Phase:** `COLLISION`
**File:** `core/collision_system.py`

### Responsibilities
- ✅ Detect fish-food collisions (eating)
- ✅ Detect fish-crab collisions (predation damage)
- ✅ Detect fish-fish proximity (for poker games)
- ✅ Detect food-crab collisions (crab eating)
- ✅ Track collision statistics per frame

### Does NOT Handle
- ❌ Entity lifecycle (deaths) - that's LifecycleSystem
- ❌ Reproduction - that's ReproductionSystem
- ❌ Poker game logic - that's PokerSystem
- ❌ Movement - that's handled by entities

### Key Methods
```python
def _do_update(self, frame: int) -> SystemResult
def _handle_fish_food_collisions(self)
def _handle_fish_crab_collisions(self)
def _handle_fish_proximity(self)  # Triggers poker
```

---

## PokerSystem

**Phase:** `COLLISION`
**File:** `core/poker_system.py`

### Responsibilities
- ✅ Manage active poker games
- ✅ Process poker game results
- ✅ Handle post-poker reproduction (sexual)
- ✅ Track poker statistics
- ✅ Create offspring from poker-based mating

### Does NOT Handle
- ❌ Proximity detection - that's CollisionSystem
- ❌ Asexual reproduction - that's ReproductionSystem
- ❌ General birth/death tracking - that's LifecycleSystem

### Key Methods
```python
def start_poker_game(fish1, fish2) -> PokerInteraction
def handle_poker_result(poker: PokerInteraction)
def _attempt_post_poker_reproduction(poker)
def _create_post_poker_offspring(winner, mate, rng)
```

---

## EntityLifecycleSystem

**Phase:** `LIFECYCLE`
**File:** `core/systems/entity_lifecycle.py`

### Responsibilities
- ✅ Process entity deaths
- ✅ Record death statistics (cause, age, etc.)
- ✅ Set death visual effects
- ✅ Cleanup dying fish after effect timer expires
- ✅ Track birth/death events

### Does NOT Handle
- ❌ Causing deaths (collision damage, starvation)
- ❌ Creating new entities - that's ReproductionSystem
- ❌ Entity update logic - that's per-entity

### Key Methods
```python
def process_entity_death(entity, cause)
def record_fish_death(fish, death_cause)
def cleanup_dying_fish()
def record_birth()
```

---

## ReproductionSystem

**Phase:** `REPRODUCTION`
**File:** `core/systems/reproduction_system.py`

### Responsibilities
- ✅ Check asexual reproduction eligibility
- ✅ Process entity update results for spawned entities
- ✅ Add newborns to simulation
- ✅ Track reproduction statistics

### Does NOT Handle
- ❌ Sexual/poker reproduction - that's PokerSystem
- ❌ Entity death - that's LifecycleSystem
- ❌ Offspring genome creation - that's in Fish

### Key Methods
```python
def _do_update(self, frame: int) -> SystemResult
def _check_asexual_reproduction(fish)
```

---

## SkillGameSystem

**Phase:** `COLLISION` (triggered during proximity)
**File:** `core/skill_game_system.py`

### Responsibilities
- ✅ Manage skill-based mini-games (rock-paper-scissors, etc.)
- ✅ Process game outcomes
- ✅ Track skill game statistics
- ✅ Evolve fish skill strategies

### Does NOT Handle
- ❌ Poker games - that's PokerSystem
- ❌ Collision detection - that's CollisionSystem

---

## TimeSystem

**Phase:** `ENVIRONMENT`
**File:** `core/systems/time_system.py`

### Responsibilities
- ✅ Track day/night cycle
- ✅ Provide time-of-day modifiers
- ✅ Trigger time-based events

### Does NOT Handle
- ❌ Entity behavior changes - entities read time state themselves

---

## Adding New Systems

1. **Identify the responsibility** - What ONE thing does this system do?
2. **Choose the phase** - When should this run relative to other systems?
3. **Create the system class** - Extend `BaseSystem`
4. **Register with engine** - Add to `SimulationEngine.__init__()`

```python
from core.systems.base import BaseSystem, SystemResult
from core.update_phases import UpdatePhase, runs_in_phase

@runs_in_phase(UpdatePhase.ENVIRONMENT)
class WeatherSystem(BaseSystem):
    """Manages weather conditions and their effects."""

    def __init__(self, engine: "SimulationEngine"):
        super().__init__(engine, "Weather")
        self.current_weather = "sunny"

    def _do_update(self, frame: int) -> SystemResult:
        # Weather logic here
        return SystemResult(details={"weather": self.current_weather})
```

---

## Decision Flow

When adding new functionality, use this decision tree:

```
Is it about collisions?
├── Yes → CollisionSystem
└── No ↓

Is it about poker games?
├── Yes → PokerSystem
└── No ↓

Is it about entity birth/death?
├── Yes → LifecycleSystem
└── No ↓

Is it about creating new entities?
├── Yes → ReproductionSystem
└── No ↓

Is it about time/environment?
├── Yes → TimeSystem
└── No ↓

Is it entity-specific behavior?
├── Yes → Add to entity class or component
└── No → Consider creating a new system
```
