# Architectural Review: Tank Simulation

## Executive Summary

Your simulation has a **solid architectural foundation** with excellent use of protocols, component composition, and phase-based execution. However, there are several areas where simplification would improve maintainability and reduce future bugs.

**Key Strengths:**
- Protocol-first design (`EnergyHolder`, `PokerPlayer`, `BehaviorStrategy`)
- Component composition in Fish (energy, lifecycle, reproduction, skills)
- Phase-based simulation loop with explicit ordering
- Clean frontend/backend/core separation

**Key Concerns:**
- 5 files over 1,000 lines each (god classes)
- Visual state mixed with entity logic
- Duplicate energy-checking patterns
- Some foundational code not actively used

---

## Part 1: What's Working Well

### 1.1 Protocol-Based Decoupling (Excellent)
**Location:** `core/interfaces.py`

```python
@runtime_checkable
class EnergyHolder(Protocol):
    @property
    def energy(self) -> float: ...
    def modify_energy(self, amount: float) -> float: ...
```

This allows the poker system, collision system, and reproduction system to work with **any** entity that holds energy, without coupling to concrete classes.

### 1.2 Component Composition in Fish (Good)
**Location:** `core/entities/fish.py:125-170`

```python
self._lifecycle_component = LifecycleComponent(max_age, size_modifier)
self._energy_component = EnergyComponent(max_energy, base_metabolism)
self._reproduction_component = ReproductionComponent()
self._skill_game_component = SkillGameComponent()
```

This is the right pattern. Each component has a single responsibility.

### 1.3 Phase-Based Update Loop (Excellent)
**Location:** `core/update_phases.py`

The explicit phase ordering prevents timing bugs:
```
FRAME_START → TIME_UPDATE → ENVIRONMENT → ENTITY_ACT →
LIFECYCLE → SPAWN → COLLISION → INTERACTION → REPRODUCTION → FRAME_END
```

### 1.4 Composable Behaviors (Innovative)
**Location:** `core/algorithms/composable.py`

The new composable system with 5 discrete choices × continuous parameters creates 1,152+ behavioral combinations from a simple, evolvable encoding. This is superior to the 48 monolithic algorithms.

---

## Part 2: Critical Issues

### 2.1 God Classes (Files Over 1,000 Lines)

| File | Lines | Classes | Concern |
|------|-------|---------|---------|
| `algorithms/food_seeking.py` | 1,380 | 14 | Too many algorithms in one file |
| `services/stats_calculator.py` | 1,276 | 1 | Single class doing too much |
| `entities/fish.py` | 1,152 | 1 | Visual state mixed with logic |
| `poker/strategy/implementations.py` | 1,031 | 13 | Too many strategies in one file |
| `simulation_engine.py` | 1,024 | 3 | Acceptable for orchestrator |

**Impact:** Large files are harder to understand, test, and modify without introducing bugs.

### 2.2 Visual State in Entity Logic
**Location:** `core/entities/fish.py:206-216`

```python
# Visual effects for poker
self.poker_effect_state: Optional[Dict[str, Any]] = None
self.poker_effect_timer: int = 0
self.poker_cooldown: int = 0

# Visual effects for births
self.birth_effect_timer: int = 0

# Visual effects for deaths
self.death_effect_state: Optional[Dict[str, Any]] = None
self.death_effect_timer: int = 0
```

**Problem:** These are **rendering concerns** living in the **domain entity**. This violates separation of concerns and makes the Fish class larger than necessary.

**Solution:** Extract to `FishVisualState` that the frontend owns.

### 2.3 EcosystemManager Has 61 Methods
**Location:** `core/ecosystem.py`

The EcosystemManager tracks:
- Population stats
- Generation stats
- Death causes
- Algorithm stats
- Poker stats (delegated)
- Reproduction stats (delegated)
- Genetic diversity
- Enhanced statistics
- Lineage tracking
- Energy sources (fish)
- Energy sources (plants)
- Energy burns
- Energy snapshots

**Some of these should be separate services.**

---

## Part 3: Code Removal Candidates

### 3.1 Duplicate MigrationHandler Protocol
**Files:**
- `core/migration_protocol.py` (27 lines)
- `core/interfaces.py:566-623` (duplicate definition)

The same protocol is defined in two places. Keep only `interfaces.py`.

**Action:** Delete `core/migration_protocol.py`, update imports in `environment.py`.

### 3.2 Migration Infrastructure Not Actively Used
**Files:**
- `core/migration_protocol.py`
- `core/interfaces.py:607-623` (MigrationCapable)
- `environment.py:470-473` (migration_handler, tank_registry, etc.)

These are placeholders for multi-tank migration that isn't implemented yet.

**Recommendation:** Keep if you plan to use it soon. Delete if not.

### 3.3 Redundant Algorithm Files vs Composable
**Context:** You have 48+ monolithic algorithms AND a composable behavior system.

If ComposableBehavior is the future, the individual algorithm classes become redundant.

**Files to potentially consolidate:**
- `algorithms/food_seeking.py` (14 classes)
- `algorithms/energy_management.py` (8 classes)
- `algorithms/predator_avoidance.py` (10 classes)
- `algorithms/schooling.py` (10 classes)
- `algorithms/territory.py` (many classes)
- `algorithms/poker.py` (8 classes)

**Recommendation:** If ComposableBehavior can express all these, deprecate the monolithic algorithms gradually.

### 3.4 StatsCalculator is 1,276 Lines
**Location:** `core/services/stats_calculator.py`

A single class doing all stats calculation is a maintenance burden.

**Recommendation:** Consider if all these stats are actually displayed/used. Remove unused metrics.

---

## Part 4: Recommended Refactoring (Priority Order)

### Priority 1: Extract Visual State from Fish

**Current (fish.py:206-216):**
```python
class Fish(Agent):
    # ... domain logic ...
    self.poker_effect_state: Optional[Dict[str, Any]] = None
    self.poker_effect_timer: int = 0
    self.birth_effect_timer: int = 0
    self.death_effect_state: Optional[Dict[str, Any]] = None
    self.death_effect_timer: int = 0
```

**Proposed:**
```python
# In frontend/src/fish_renderer.ts or core/fish/visual_state.py
@dataclass
class FishVisualState:
    poker_effect_state: Optional[Dict[str, Any]] = None
    poker_effect_timer: int = 0
    birth_effect_timer: int = 0
    death_effect_state: Optional[Dict[str, Any]] = None
    death_effect_timer: int = 0

# Frontend maintains: Dict[int, FishVisualState] keyed by fish_id
```

**Benefit:** Fish class shrinks, frontend owns its concerns.

### Priority 2: Consolidate Migration Protocol

**Action:**
1. Delete `core/migration_protocol.py`
2. Update `core/environment.py:13` to import from `interfaces.py`

**Diff:**
```python
# environment.py
- from core.migration_protocol import MigrationHandler
+ from core.interfaces import MigrationHandler
```

### Priority 3: Split food_seeking.py (1,380 lines → 14 files)

**Current:** 14 algorithm classes in one file.

**Proposed structure:**
```
core/algorithms/food_seeking/
├── __init__.py          # Re-exports all for backwards compatibility
├── greedy.py            # GreedyFoodSeeker
├── energy_aware.py      # EnergyAwareFoodSeeker
├── opportunistic.py     # OpportunisticFeeder
├── quality.py           # FoodQualityOptimizer
├── ambush.py            # AmbushFeeder
├── patrol.py            # PatrolFeeder
├── surface.py           # SurfaceSkimmer
├── bottom.py            # BottomFeeder
├── zigzag.py            # ZigZagForager
├── circular.py          # CircularHunter
├── memory.py            # FoodMemorySeeker
├── aggressive.py        # AggressiveHunter
├── spiral.py            # SpiralForager
└── cooperative.py       # CooperativeForager
```

**Benefit:** Each algorithm is independently testable and modifiable.

### Priority 4: Extract Energy Statistics from EcosystemManager

**Current (ecosystem.py):** 20+ methods for energy tracking.

**Proposed:**
```python
# core/services/energy_tracker.py
class EnergyTracker:
    """Tracks energy flow in the simulation."""
    def record_energy_gain(self, source: str, amount: float) -> None: ...
    def record_energy_burn(self, source: str, amount: float) -> None: ...
    def get_recent_breakdown(self, window_frames: int) -> Dict[str, float]: ...
    def get_energy_delta(self, window_frames: int) -> Dict[str, Any]: ...

# In EcosystemManager.__init__:
self.energy_tracker = EnergyTracker()
```

**Benefit:** EcosystemManager delegates, becomes smaller, and EnergyTracker is reusable.

### Priority 5: Standardize Energy State Checking

**Current (scattered across files):**
```python
# In algorithms/base.py
def _get_energy_state(self, fish) -> EnergyState: ...

# In fish/energy_component.py
def is_critical_energy(self) -> bool: ...
def is_low_energy(self) -> bool: ...

# In entities/fish.py (property delegation)
@property
def energy_ratio(self) -> float: ...
```

**Proposed:**
```python
# core/fish/energy_state.py
@dataclass
class EnergyState:
    energy: float
    max_energy: float

    @property
    def ratio(self) -> float:
        return self.energy / self.max_energy if self.max_energy > 0 else 0.0

    @property
    def is_critical(self) -> bool:
        return self.ratio < 0.15

    @property
    def is_low(self) -> bool:
        return self.ratio < 0.35

    @property
    def is_starving(self) -> bool:
        return self.ratio < 0.05

# Usage everywhere:
state = fish.get_energy_state()
if state.is_critical:
    ...
```

**Benefit:** Single source of truth for energy thresholds.

---

## Part 5: What NOT to Change

### Keep: SimulationEngine as Orchestrator
At 1,024 lines, it's large but acceptable. Game loop orchestrators naturally coordinate many systems.

### Keep: Protocol-Based Interfaces
Your use of `@runtime_checkable` protocols is excellent. Continue using this pattern.

### Keep: Component Composition in Fish
The EnergyComponent, LifecycleComponent pattern is correct. Just extract visual state.

### Keep: Phase-Based Execution
The UpdatePhase enum and explicit ordering prevents timing bugs.

### Keep: Composable Behaviors
This is your best abstraction. Consider making it the **only** behavior system.

---

## Part 6: Architectural Principles for Future Development

### 6.1 One Class, One File (for substantial classes)
When a class exceeds 200 lines, consider giving it its own file.

### 6.2 Prefer Composition Over Inheritance
You're already doing this well with Fish components. Continue.

### 6.3 Protocols for External Dependencies
Any class that other classes depend on should have a Protocol interface.

### 6.4 Separate Domain Logic from Presentation
Visual effects, timers, rendering state → Frontend
Energy, lifecycle, reproduction → Core

### 6.5 Extract When There's Duplication
If you see the same pattern in 3+ places, extract it.

---

## Summary: Action Items

| Priority | Action | Effort | Impact |
|----------|--------|--------|--------|
| 1 | Extract visual state from Fish | 2h | High - cleaner entity |
| 2 | Delete migration_protocol.py | 15min | Low - removes duplication |
| 3 | Split food_seeking.py | 3h | Medium - better organization |
| 4 | Extract EnergyTracker | 2h | Medium - smaller EcosystemManager |
| 5 | Standardize energy state | 2h | Medium - removes duplication |
| Consider | Deprecate monolithic algorithms | varies | High - if composable is complete |
| Consider | Audit StatsCalculator usage | 1h | Medium - remove unused metrics |

The codebase is well-architected. These changes are refinements, not rewrites.
