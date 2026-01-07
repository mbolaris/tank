---
description: Remove BaseSimulator architectural debt
---

# Workflow: Remove BaseSimulator

> **STATUS: COMPLETED (2024-12-24)**
> All phases of this workflow have been successfully completed.
> BaseSimulator has been removed and its responsibilities distributed to systems.

This workflow eliminates the BaseSimulator abstraction layer by moving its logic into the appropriate systems.

## Phase 1: Move Collision Logic to CollisionSystem ✅ COMPLETED (2024-12)

> **This phase has been completed.** CollisionSystem._do_update() now handles all collision iteration
> including fish-food, fish-crab, fish-fish poker proximity, and food-crab collisions.
> The engine's _phase_collision() calls collision_system.update() directly.

### What Was Done:

1. **Extended CollisionSystem** to include `_handle_fish_collisions()` and `_handle_food_collisions()`
2. **Updated SimulationEngine** `_phase_collision()` to call `collision_system.update()` directly
3. **All 1020 tests pass** - collision detection, poker games, determinism all working

### Remaining in BaseSimulator:
- `record_fish_death()` - Still used, needs Phase 3
- `cleanup_dying_fish()` - Still used, needs Phase 3
- `_attempt_post_poker_reproduction()` - Still used, needs Phase 2
- `_create_post_poker_offspring()` - Still used, needs Phase 2
- `keep_entity_on_screen()` - Still used, needs Phase 4
- `handle_collisions()` - No longer called by engine (but still exists for backwards compat)
- `handle_fish_collisions()` - Duplicated in CollisionSystem (can be removed after full migration)
- `handle_food_collisions()` - Duplicated in CollisionSystem (can be removed after full migration)

---

## Phase 2: Move Post-Poker Reproduction to PokerSystem

### Step 1: Extend PokerSystem

Move `_attempt_post_poker_reproduction()` and `_create_post_poker_offspring()` from BaseSimulator to PokerSystem.

**File:** `core/poker_system.py`

```python
def handle_poker_result(self, poker: PokerInteraction) -> None:
    """Process poker results including reproduction."""
    super().handle_poker_result(poker)

    # Move _attempt_post_poker_reproduction() logic here
    offspring = self._attempt_post_poker_reproduction(poker)
    if offspring:
        self._engine.add_entity(offspring)
        offspring.register_birth()
        self._engine.lifecycle_system.record_birth()

def _attempt_post_poker_reproduction(self, poker: PokerInteraction) -> Optional[Fish]:
    """Attempt to create offspring after poker game."""
    # Copy logic from BaseSimulator._attempt_post_poker_reproduction()
    pass

def _create_post_poker_offspring(self, winner: Fish, mate: Fish, rng: random.Random) -> Optional[Fish]:
    """Create offspring from poker winner and mate."""
    # Copy logic from BaseSimulator._create_post_poker_offspring()
    pass
```

### Step 2: Run Tests

```bash
pytest tests/test_poker_system_unit.py -v
pytest tests/test_mixed_poker_with_plants.py -v
```

---

## Phase 3: Move Death/Lifecycle Logic to EntityLifecycleSystem

### Step 1: Extend EntityLifecycleSystem

Move `record_fish_death()` and `cleanup_dying_fish()` from BaseSimulator to EntityLifecycleSystem.

**File:** `core/systems/entity_lifecycle.py`

```python
def record_fish_death(self, fish: Fish, cause: Optional[str] = None) -> None:
    """Record a fish death and mark for delayed removal."""
    # Copy logic from BaseSimulator.record_fish_death()
    pass

def cleanup_dying_fish(self) -> None:
    """Remove fish whose death effect timer has expired."""
    # Copy logic from BaseSimulator.cleanup_dying_fish()
    pass

def _do_update(self, frame: int) -> SystemResult:
    """Update lifecycle tracking and cleanup dying entities."""
    self.cleanup_dying_fish()

    return SystemResult(
        details={"births": self._birth_count, "deaths": self._death_count}
    )
```

### Step 2: Update SimulationEngine

```python
def record_fish_death(self, fish: Fish, cause: Optional[str] = None) -> None:
    """Delegate to EntityLifecycleSystem."""
    self.lifecycle_system.record_fish_death(fish, cause)
```

---

## Phase 4: Inline Remaining Utilities

### Step 1: Move keep_entity_on_screen() to SimulationEngine

**File:** `core/simulation/engine.py`

```python
def keep_entity_on_screen(self, entity: Agent) -> None:
    """Keep an entity fully within screen bounds."""
    display = self.config.display

    # Clamp horizontally
    if entity.pos.x < 0:
        entity.pos.x = 0
    elif entity.pos.x + entity.width > display.screen_width:
        entity.pos.x = display.screen_width - entity.width

    # Clamp vertically
    if entity.pos.y < 0:
        entity.pos.y = 0
    elif entity.pos.y + entity.height > display.screen_height:
        entity.pos.y = display.screen_height - entity.height
```

---

## Phase 5: Delete BaseSimulator

### Step 1: Remove Inheritance

**File:** `core/simulation/engine.py`

```python
# OLD
class SimulationEngine(BaseSimulator):
    ...

# NEW
class SimulationEngine:
    def __init__(self, ...):
        # Remove super().__init__() call
        self.frame_count: int = 0
        self.paused: bool = False
        # ... rest of init
```

### Step 2: Delete Files

```bash
rm core/simulators/base_simulator.py
rm core/simulators/__init__.py  # If now empty
rmdir core/simulators  # If now empty
```

### Step 3: Update Imports

Remove any imports of BaseSimulator:

```bash
grep -r "from core.simulators" core/ backend/
# Update any files that import BaseSimulator
```

---

## Phase 6: Verify Everything Works

### Run Full Test Suite

```bash
pytest tests/ -v
```

### Run Simulation

```bash
python main.py
```

### Check for Regressions

- Verify collision detection still works
- Verify poker games still happen
- Verify post-poker reproduction still works
- Verify fish death tracking still works

---

## Success Criteria

- ✅ All tests pass
- ✅ BaseSimulator.py deleted
- ✅ No imports of BaseSimulator remain
- ✅ Collision logic in CollisionSystem
- ✅ Post-poker reproduction in PokerSystem
- ✅ Death tracking in EntityLifecycleSystem
- ✅ Simulation runs without errors
- ✅ Code is more maintainable (logic in appropriate systems)

---

## Estimated Effort

- Phase 1: 2 hours
- Phase 2: 2 hours
- Phase 3: 1.5 hours
- Phase 4: 0.5 hours
- Phase 5: 0.5 hours
- Phase 6: 0.5 hours

**Total: ~7 hours**

---

## Notes

- This is the highest-priority architectural improvement
- Eliminates 852 lines of unnecessary abstraction
- Makes system responsibilities clearer
- Improves testability
- Reduces cognitive load for future developers
