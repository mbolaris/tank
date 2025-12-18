# Code Quality Analysis Report - Tank Fish Simulation

## Executive Summary
This codebase is well-structured with good separation of concerns and comprehensive type hints in many places. However, there are opportunities for improvement in code deduplication, magic number management, and function complexity reduction.

---

## 1. MAGIC NUMBERS (High Priority)

### Issue: Hardcoded Constants in Calculations
Multiple files contain magic numbers that should be extracted to named constants.

### Examples:

**File: `/home/user/tank/core/entities.py`**
- **Line 116, 154**: Magic multiplier `0.15` for avoidance velocity
  ```python
  self.avoidance_velocity -= velocity_change * 0.15  # AVOIDANCE_SPEED_CHANGE
  ```
  Status: Comment explains intent, but should be extracted constant
  
- **Line 160**: Magic multiplier `0.1` for alignment
  ```python
  self.vel += difference.normalize() * 0.1  # ALIGNMENT_SPEED_CHANGE
  ```
  
- **Line 242**: Magic constant `0.5` for initial energy
  ```python
  self.energy: float = self.max_energy * 0.5  # Start with 50% energy
  ```
  
- **Line 329, 331**: Life stage multipliers (0.7, 1.2)
  ```python
  metabolism *= 0.7  # Babies need less energy
  metabolism *= 1.2  # Elders need more energy
  ```
  
- **Line 339**: Hardcoded starvation threshold `20.0`
  ```python
  return self.energy < 20.0
  ```
  Problem: Conflicts with `CRITICAL_ENERGY_THRESHOLD = 15.0` defined at line 261

**File: `/home/user/tank/fishtank.py`**
- **Lines 284, 290, 297, 302**: Magic numbers in poker notification styling
  ```python
  color = (255, 255, 100)  # Yellow for tie (line 284)
  color = (100, 255, 100)  # Green for wins (line 290)
  'duration': 180  # Show for 6 seconds at 30fps (line 297)
  if len(self.poker_notifications) > 5:  # Keep only last 5 (line 302)
  ```
  
- **Line 376-377**: Bar dimensions and colors
  ```python
  bar_width = 30
  bar_height = 4
  color = (50, 200, 50)  # Green (line 390)
  color = (200, 200, 50)  # Yellow (line 392)
  color = (200, 50, 50)   # Red (line 394)
  ```

### Recommendation
Create a constants file (`core/ui_constants.py`) with:
```python
# Animation/notification constants
POKER_NOTIFICATION_DURATION = 180  # 6 seconds at 30fps
POKER_NOTIFICATION_MAX_COUNT = 5
POKER_TIE_COLOR = (255, 255, 100)
POKER_WIN_COLOR = (100, 255, 100)

# Health bar constants
HEALTH_BAR_WIDTH = 30
HEALTH_BAR_HEIGHT = 4
HEALTH_CRITICAL_COLOR = (200, 50, 50)
HEALTH_LOW_COLOR = (200, 200, 50)
HEALTH_GOOD_COLOR = (50, 200, 50)

# Movement constants
AVOIDANCE_SPEED_MULTIPLIER = 0.15
ALIGNMENT_SPEED_MULTIPLIER = 0.1
```

---

## 2. CODE DUPLICATION (High Priority)

### Issue: Repeated Fish Death Recording Logic
The pattern for recording fish deaths is duplicated 3 times in `fishtank.py` with identical algorithm ID extraction logic.

**File: `/home/user/tank/fishtank.py`**

**Location 1** (Lines 100-113): When fish dies naturally
```python
if sprite.is_dead():
    if self.ecosystem is not None:
        algorithm_id = None
        if sprite.genome.behavioral.behavior_algorithm.value is not None:
            algorithm_id = get_algorithm_index(sprite.genome.behavioral.behavior_algorithm.value)
        self.ecosystem.record_death(
            sprite.fish_id,
            sprite.generation,
            sprite.age,
            sprite.get_death_cause(),
            sprite.genome,
            algorithm_id=algorithm_id
        )
    sprite.kill()
```

**Location 2** (Lines 186-200): When crab kills fish
```python
if self.ecosystem is not None:
    algorithm_id = None
    if fish.genome.behavioral.behavior_algorithm.value is not None:
        algorithm_id = get_algorithm_index(fish.genome.behavioral.behavior_algorithm.value)
    self.ecosystem.record_death(...)
```

**Location 3 & 4** (Lines 213-224, 228-240): When fish dies in poker game

### Recommendation
Extract to a helper method in `FishTankSimulator`:
```python
def record_fish_death(self, fish: agents.Fish, cause: str) -> None:
    """Record a fish's death in the ecosystem manager.
    
    Args:
        fish: Fish that died
        cause: Cause of death ('starvation', 'old_age', 'predation', etc.)
    """
    if self.ecosystem is None:
        return
    
    algorithm_id = None
    if fish.genome.behavioral.behavior_algorithm.value is not None:
        algorithm_id = get_algorithm_index(fish.genome.behavioral.behavior_algorithm.value)
    
    self.ecosystem.record_death(
        fish.fish_id,
        fish.generation,
        fish.age,
        cause,
        fish.genome,
        algorithm_id=algorithm_id
    )
```

**Same issue exists in `simulation_engine.py` (Lines 102-115, 224-236, 252-264, 267-279)**

---

## 3. LONG FUNCTIONS (Medium Priority)

### Issue: Over-Complex Function with Multiple Responsibilities

**File: `/home/user/tank/core/ecosystem.py`**
**Function: `get_algorithm_performance_report()` (Lines 543-678, 136 lines)**

This function has multiple responsibilities:
1. Collecting and sorting algorithms by reproduction rate
2. Collecting and sorting by survival rate
3. Collecting and sorting by lifespan
4. Collecting and sorting worst performers by starvation
5. Generating recommendations

### Recommendation
Split into smaller functions:
```python
def _format_algorithm_ranking_section(
    self, 
    title: str, 
    algorithms: List[Tuple[int, AlgorithmStats]], 
    stat_func,
    count: int = 10
) -> List[str]:
    """Format a generic ranking section for the report."""
    
def _get_reproduction_rate_section(self) -> List[str]:
    """Get top performers by reproduction rate."""
    
def _get_survival_rate_section(self) -> List[str]:
    """Get top performers by survival rate."""
    
def _get_lifespan_section(self) -> List[str]:
    """Get longest-lived algorithms."""
    
def _get_starvation_section(self) -> List[str]:
    """Get worst performers by starvation rate."""
    
def _get_recommendations(self) -> List[str]:
    """Generate recommendations based on data."""
```

---

## 4. LINE LENGTH VIOLATIONS (Low-Medium Priority)

**PEP 8 Standard: Maximum 100 characters per line**

### Violations Found:

**File: `/home/user/tank/core/entities.py`** (11 long lines)
- **Line 237** (103 chars):
  ```python
  self.max_age: int = int(self.BASE_MAX_AGE * self.genome.max_energy)  # Hardier fish live longer
  ```
  
- **Line 254** (104 chars):
  ```python
  self.food_memory: List[Tuple[Vector2, int]] = []  # (position, age_when_found) for food hotspots
  ```
  
- **Line 500** (101 chars)

**File: `/home/user/tank/core/ecosystem.py`** (9 long lines)
- **Line 300** (108 chars)
- **Line 356** (116 chars)
- **Line 357** (114 chars)

**File: `/home/user/tank/agents.py`** (4 long lines)
- **Line 189** (104 chars):
  ```python
  filenames: List[str], x: float, y: float, speed: float,
  ```
- **Line 387** (110 chars):
  ```python
  self._entity = core_entities.Crab(environment, genome, *INIT_POS['crab'], SCREEN_WIDTH, SCREEN_HEIGHT)
  ```

### Recommendation
Use line continuation or extract to multiple lines:
```python
# Instead of:
self._entity = core_entities.Crab(environment, genome, *INIT_POS['crab'], 
                                   SCREEN_WIDTH, SCREEN_HEIGHT)

# Better:
init_pos = INIT_POS['crab']
self._entity = core_entities.Crab(
    environment, 
    genome, 
    *init_pos, 
    SCREEN_WIDTH, 
    SCREEN_HEIGHT
)
```

---

## 5. REPEATED ENTITY FILTERING (Medium Priority)

### Issue: Multiple instances of the same filtering pattern

**File: `/home/user/tank/fishtank.py`**
- **Line 95**: `fish_count = len([a for a in self.agents if isinstance(a, agents.Fish)])`
- **Line 167**: `fish_list = [a for a in self.agents if isinstance(a, agents.Fish)]`
- **Line 258**: Same pattern in `handle_reproduction()`

### Recommendation
Create helper methods:
```python
def get_fish_list(self) -> List[agents.Fish]:
    """Get all fish agents."""
    return [a for a in self.agents if isinstance(a, agents.Fish)]

def get_fish_count(self) -> int:
    """Get count of all fish agents."""
    return len(self.get_fish_list())

def get_food_list(self) -> List[agents.Food]:
    """Get all food agents."""
    return [a for a in self.agents if isinstance(a, agents.Food)]
```

---

## 6. INCONSISTENT ENERGY THRESHOLD DEFINITIONS (Medium Priority)

**File: `/home/user/tank/core/entities.py`**

**Problem**: Conflicting starvation thresholds
- **Line 261**: `CRITICAL_ENERGY_THRESHOLD = 15.0`
- **Line 262**: `LOW_ENERGY_THRESHOLD = 30.0`
- **Line 339**: Hardcoded check: `return self.energy < 20.0` (in `is_starving()`)

The `is_starving()` check at line 339 uses `20.0`, which is between CRITICAL and LOW thresholds. This creates ambiguity about what "starving" means.

### Recommendation
Define and use consistently:
```python
CRITICAL_ENERGY_THRESHOLD = 15.0  # Imminent death
LOW_ENERGY_THRESHOLD = 20.0       # Actually starving (rename to STARVATION_THRESHOLD)
SAFE_ENERGY_THRESHOLD = 60.0      # Can explore/breed

def is_starving(self) -> bool:
    """Check if fish is starving (low energy)."""
    return self.energy < self.LOW_ENERGY_THRESHOLD
```

---

## 7. MISSING/INCOMPLETE DOCSTRINGS (Low Priority)

### Good Examples (Full Documentation):
- `FishTankSimulator` class (lines 14-27) - Well documented
- `Fish` class (lines 164-179) - Complete attribute documentation
- `get_algorithm_performance_report()` (lines 543-554) - Clear docstring

### Incomplete Examples:

**File: `/home/user/tank/fishtank.py`**
- **Line 366** `draw_health_bar()`: Good docstring but could detail parameter meanings
- **Line 366** `keep_sprite_on_screen()`: Missing detailed explanation of clamping behavior

**File: `/home/user/tank/core/poker_interaction.py`**
- **Line 1-8**: Module docstring is minimal; could explain game rules

### Recommendation
Improve docstring completeness:
```python
def draw_health_bar(self, fish: agents.Fish) -> None:
    """Draw energy status bar above a fish.
    
    The bar displays fish energy relative to max capacity:
    - Green: >60% energy (healthy)
    - Yellow: 30-60% energy (caution)
    - Red: <30% energy (critical)
    
    Args:
        fish: The fish to draw health bar for
        
    Returns:
        None (modifies screen in-place)
    """
```

---

## 8. PARAMETER VALIDATION MISSING (Medium Priority)

### Issue: Insufficient input validation in some functions

**File: `/home/user/tank/core/entities.py`**
- **Line 206-210** `Fish.__init__()`: Takes 10 parameters; some could be validated
- No checks for negative values in numeric parameters

### Recommendation
Add validation for critical parameters:
```python
def __init__(self, ..., speed: float, ...):
    if speed <= 0:
        raise ValueError(f"speed must be positive, got {speed}")
    if not isinstance(movement_strategy, MovementStrategy):
        raise TypeError(f"movement_strategy must be MovementStrategy, got {type(movement_strategy)}")
```

---

## 9. CYCLOMATIC COMPLEXITY (Medium Priority)

### Issue: Complex conditional logic in collision handling

**File: `/home/user/tank/fishtank.py`**
**Function: `handle_fish_collisions()` (Lines 176-240)**

The nested if-elif-else structure has multiple exit paths and high complexity:
```python
for fish in list(self.agents.sprites()):
    if isinstance(fish, agents.Fish):
        for collision_sprite in collisions:
            if isinstance(collision_sprite, agents.Crab):
                if collision_sprite.can_hunt():
                    if self.ecosystem is not None:
                        # ...long block...
            elif isinstance(collision_sprite, agents.Food):
                # ...
            elif isinstance(collision_sprite, agents.Fish):
                # ...complex block with nested ifs...
```

### Recommendation
Extract collision handlers:
```python
def handle_crab_collision(self, fish: agents.Fish, crab: agents.Crab) -> None:
    """Handle collision between fish and crab."""
    if not crab.can_hunt():
        return
    self.record_fish_death(fish, 'predation')
    crab.eat_fish(fish)
    fish.kill()

def handle_fish_poker_collision(self, fish1: agents.Fish, fish2: agents.Fish) -> None:
    """Handle poker interaction between two fish."""
    poker = PokerInteraction(fish1, fish2)
    if not poker.play_poker():
        return
    
    self.add_poker_notification(poker)
    # ... handle deaths ...

# Then in main loop:
if isinstance(collision_sprite, agents.Crab):
    self.handle_crab_collision(fish, collision_sprite)
elif isinstance(collision_sprite, agents.Food):
    fish.eat(collision_sprite)
elif isinstance(collision_sprite, agents.Fish):
    self.handle_fish_poker_collision(fish, collision_sprite)
```

---

## 10. TYPE HINT CONSISTENCY (Low Priority)

### Good Coverage:
Most functions have proper type hints (>90% coverage)

### Minor Issues:

**File: `/home/user/tank/core/entities.py`**
- Dictionary access on line 254 could be more explicit:
  ```python
  self.food_memory: List[Tuple[Vector2, int]] = []
  ```

**File: `/home/user/tank/fishtank.py`**
- Some variable type hints could be more specific
  ```python
  # Instead of:
  new_agents: List[agents.Agent] = []
  # Could specify more precisely (but current is acceptable)
  ```

### Recommendation
Type hints are generally good. Only minor cleanup needed in edge cases.

---

## SUMMARY OF RECOMMENDATIONS (by Impact)

### Critical (Do First)
1. **Extract magic numbers to constants** - Improves maintainability
2. **Remove death recording duplication** - Reduces bugs and maintenance burden (6+ locations)
3. **Create helper methods for entity filtering** - Reduces duplication in 5+ places

### Important (Should Do)
4. **Fix line length violations** - Improves code style/readability
5. **Extract complex collision handling** - Improves testability
6. **Split large report generation function** - Improves readability

### Nice to Have
7. **Add parameter validation** - Improves robustness
8. **Enhance docstrings** - Improves documentation
9. **Reconcile energy threshold definitions** - Reduces confusion

---

## Files Most Affected (Refactoring Priority)

1. **`/home/user/tank/fishtank.py`** - 5+ duplications, 4 long lines, magic numbers
2. **`/home/user/tank/core/entities.py`** - Magic multipliers, 11 long lines
3. **`/home/user/tank/core/ecosystem.py`** - 136-line function, 9 long lines
4. **`/home/user/tank/simulation_engine.py`** - Death recording duplications

