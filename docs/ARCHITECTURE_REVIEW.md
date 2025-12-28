# Architecture Review: Fish Tank Simulation

## Executive Summary

Your simulation has a **solid foundation** with good patterns in key areas. However, there's room for improvement in consistency and reducing complexity. This review prioritizes **quality over quantity** - identifying code to remove and abstractions to simplify.

## Changes Implemented

### Phase 1: Code Cleanup (Completed)
- ✅ Removed 3 deprecated poker methods (~90 lines)
- ✅ Moved `_emit_event()` to Entity base class (deduplicated)
- ✅ Updated docstring example in ecosystem_stats.py

### Phase 2: Entity Hierarchy (Completed)
- ✅ Created `Entity` base class with core attributes
- ✅ `Agent` now extends `Entity` (adds movement/AI)
- ✅ `Castle` now inherits from `Entity` (not Agent)
- ✅ Castle no longer has unused velocity/AI methods

### Findings
- All 14 food-seeking algorithms are **legacy code** replaced by `ComposableBehavior`
- They're kept for backwards compatibility with old saves

---

## What's Working Well ✓

### 1. Component Composition for Fish
Fish uses composition (EnergyComponent, LifecycleComponent, etc.) rather than inheritance bloat. This is the right pattern.

```python
# Good: Fish delegates to focused components
self._lifecycle_component = LifecycleComponent(max_age, size_modifier)
self._energy_component = EnergyComponent(max_energy, base_metabolism)
self._reproduction_component = ReproductionComponent()
self._skill_game_component = SkillGameComponent()
```

### 2. Protocol-Based Interfaces
`core/interfaces.py` defines clean protocols (EnergyHolder, PokerPlayer, etc.). This enables duck typing and structural subtyping - very Pythonic.

### 3. Entity Mutation Queue
`EntityMutationQueue` prevents mid-iteration bugs by deferring spawns/removals. This is a defensive pattern that prevents subtle bugs.

### 4. Explicit Phase Ordering
The 10-phase update loop is explicit and debuggable. You know exactly when things happen.

### 5. Facade Pattern for EcosystemManager
Composing specialized trackers (PopulationTracker, PokerStatsManager, etc.) behind a facade keeps the API clean.

---

## Critical Issues to Address

### Issue #1: Inconsistent Component Patterns (High Priority)

**Problem:** Fish uses components, but Plant embeds everything inline.

| Entity | Lines | Uses Components? |
|--------|-------|------------------|
| Fish   | 1103  | Yes (5 components) |
| Plant  | 852   | No |

**Why this matters:** When you add features, you'll duplicate logic. Plant's energy handling is already duplicated from Fish.

**Recommendation:** Extract `PlantEnergyComponent` and `PlantPokerMixin` to match Fish's pattern. This will:
- Reduce Plant.py by ~150 lines
- Make energy behavior testable in isolation
- Enable code reuse

---

### Issue #2: Duplicate Code to Remove (High Priority)

#### A. `_emit_event()` duplication

**Identical code in two files:**
- `core/entities/fish.py:478-485`
- `core/entities/plant.py:147-154`

```python
def _emit_event(self, event: object) -> None:
    """Emit a telemetry event if a sink is available."""
    telemetry = self.ecosystem
    if telemetry is None:
        return
    record_event = getattr(telemetry, "record_event", None)
    if callable(record_event):
        record_event(event)
```

**Fix:** Move to `Agent` base class. All entities that emit events inherit it.

#### B. Deprecated Poker Methods

Three deprecated methods exist with their replacements:

| Deprecated Method | Replacement | Location |
|-------------------|-------------|----------|
| `record_poker_outcome()` | `record_poker_outcome_record()` | ecosystem.py:701-741 |
| `record_plant_poker_game()` | `record_plant_poker_game_record()` | ecosystem.py:757-789 |
| `record_mixed_poker_outcome()` | `record_mixed_poker_outcome_record()` | ecosystem.py:832-859 |

**Current callers:**
- `core/ecosystem_stats.py:246` - uses deprecated `record_poker_outcome(record)`
- `tests/verify_memory_leaks.py:60` - uses deprecated `record_plant_poker_game()`

**Fix:** Update callers to use `*_record()` methods, then delete the deprecated methods. This removes ~90 lines of wrapper code.

---

### Issue #3: Castle and Food Shouldn't Be Agents (Medium Priority)

**Problem:** The inheritance hierarchy is too broad.

```
Agent (movement, avoidance, alignment methods)
├── Fish ✓ (uses movement)
├── Plant ✗ (plants don't move)
├── Crab ✓ (uses movement)
├── Castle ✗ (decorative, never moves)
└── Food ✗ (floats down, no AI)
```

Castle and Food inherit methods they never use (`avoid()`, `align_near()`, `move_away()`, etc.).

**Recommendation:** Create a simpler base:

```python
class Entity:
    """Base for all simulation entities."""
    pos: Vector2
    state: EntityStateMachine

class MobileEntity(Entity):
    """Entities that move with velocity."""
    vel: Vector2
    def update_position(self): ...
    def handle_screen_edges(self): ...

class Agent(MobileEntity):
    """Entities with AI behaviors (avoidance, alignment)."""
    def avoid(self, others): ...
    def align_near(self, others): ...
```

Then:
- `Fish`, `Crab` → inherit from `Agent`
- `Plant`, `Castle` → inherit from `Entity`
- `Food` → inherit from `MobileEntity` (has velocity but no AI)

This reduces cognitive load and prevents accidental method calls.

---

### Issue #4: EcosystemManager Has Too Many Properties (Medium Priority)

**Problem:** 19 `@property` delegations create a maintenance burden.

```python
# Lines 109-217: 19 properties just forwarding to sub-trackers
@property
def max_population(self) -> int:
    return self.population.max_population

@property
def current_generation(self) -> int:
    return self.population.current_generation
# ... 17 more
```

**Why this matters:** Every new tracker field requires a new property. It's boilerplate that obscures real logic.

**Recommendation:** Direct access to composed objects is cleaner:

```python
# Instead of:
ecosystem.current_generation
ecosystem.total_births

# Use:
ecosystem.population.current_generation
ecosystem.population.total_births
```

Keep only the most-used properties (5-7 max). For others, access the tracker directly. This is more explicit and reduces the facade's surface area.

---

### Issue #5: Algorithm Sprawl (Low Priority, Consider Later)

14 food-seeking algorithms exist:
```
GreedyFoodSeeker, EnergyAwareFoodSeeker, OpportunisticFeeder,
FoodQualityOptimizer, AmbushFeeder, PatrolFeeder, SurfaceSkimmer,
BottomFeeder, ZigZagForager, CircularHunter, FoodMemorySeeker,
AggressiveHunter, SpiralForager, CooperativeForager
```

**Question to answer:** Are all 14 actually used in production? Or were some experiments?

If some are unused, remove them. If they're used, consider whether they can share more base behavior.

---

## Code to Remove (Quality Over Quantity)

### Immediate Removals (~180 lines saved)

| File | Lines | What | Why |
|------|-------|------|-----|
| `ecosystem.py` | 701-741 | `record_poker_outcome()` | Deprecated, has replacement |
| `ecosystem.py` | 757-789 | `record_plant_poker_game()` | Deprecated, has replacement |
| `ecosystem.py` | 832-859 | `record_mixed_poker_outcome()` | Deprecated, has replacement |
| `fish.py` | 478-485 | `_emit_event()` | Move to base class |
| `plant.py` | 147-154 | `_emit_event()` | Move to base class |

### After Updating Callers (~40 lines of updates required)

1. `core/ecosystem_stats.py:246` - change `record_poker_outcome(record)` to `record_poker_outcome_record(record)`
2. `tests/verify_memory_leaks.py:60` - use record object instead of kwargs

---

## Prioritized Refactoring Roadmap

### Phase 1: Remove Deprecated Code (Low Risk, High Value)
**Time: 1 session**

1. Update 2 callers of deprecated poker methods
2. Delete 3 deprecated methods (~90 lines)
3. Move `_emit_event()` to Agent base class (~14 lines deduped)
4. Remove TODO at `plant.py:104` if resolved

**Result:** Cleaner codebase, no behavior change

### Phase 2: Simplify Entity Hierarchy (Medium Risk)
**Time: 2-3 sessions**

1. Create `Entity` base class (just pos, state)
2. Create `MobileEntity` (Entity + velocity)
3. Keep `Agent` for AI behaviors
4. Migrate `Castle` and `Food` to appropriate bases
5. Update isinstance checks if any

**Result:** Clearer hierarchy, better extensibility

### Phase 3: Plant Component Extraction (Medium Risk)
**Time: 2 sessions**

1. Extract `PlantEnergyComponent` matching Fish's pattern
2. Create shared `PokerPlayerMixin` for poker methods
3. Reduce Plant.py from 852 to ~600 lines

**Result:** Consistent patterns, testable components

### Phase 4: Reduce EcosystemManager Surface (Low Risk)
**Time: 1 session**

1. Remove 12 least-used property delegations
2. Update callers to use `ecosystem.tracker.property` pattern
3. Document the simplified API

**Result:** Smaller facade, more explicit access

---

## Design Principles to Maintain

### 1. Prefer Composition Over Inheritance
✓ You're doing this with Fish components. Extend to Plant.

### 2. Single Responsibility
Each component should have one reason to change. `EnergyComponent` handles energy, nothing else.

### 3. Explicit Over Implicit
The explicit phase ordering is good. Keep it. Don't auto-register systems by phase.

### 4. Protocol Interfaces
Continue using Protocols from `core/interfaces.py`. They enable flexibility without inheritance chains.

### 5. Fail Fast
`EntityMutationQueue` rejects duplicate operations. This is good defensive design.

---

## Questions for You to Answer

1. **Algorithm usage:** Which of the 14 food-seeking algorithms are actually used in production vs. experiments?

2. **Plant evolution:** Will plants get genetics and reproduction like fish? If yes, the component extraction becomes higher priority.

3. **Castle purpose:** Is Castle purely decorative? Could it be removed or simplified further?

4. **Migration scope:** How many tanks will be connected? This affects whether migration logic should be extracted to a service.

---

## Summary

**Strengths:**
- Good component composition (Fish)
- Clean protocol interfaces
- Defensive mutation queue
- Explicit phase ordering

**Focus Areas:**
1. Remove deprecated code (immediate win)
2. Extend component pattern to Plant
3. Simplify entity hierarchy
4. Reduce EcosystemManager surface area

The codebase is better than average. These improvements will make it easier to extend and debug as you add features.
