# Code Cleanup Analysis Report

## Summary
This report identifies code cleanup opportunities across the Fish Tank simulation codebase. A total of **394 print statements** were found throughout the code, along with numerous magic numbers, structural improvements, and Python best practices violations.

---

## 1. DEBUG PRINT STATEMENTS (394 instances)

### 1.1 Production Code with Print Statements

#### `/home/user/tank/simulation_engine.py` (55 print statements)
**Lines:** 329-378, 387-415
- **Issue:** Extensive use of `print()` for statistics display instead of logging
- **Prints:** Status headers, population stats, death causes, reproduction stats, genetic diversity
- **Recommendation:** Convert to logger.info() calls with structured formatting

**Examples:**
```python
# Line 329-378: print statements in print_stats()
print("\n" + "=" * 60)
print(f"Frame: {stats.get('frame_count', 0)}")
print(f"Population: {stats.get('total_population', 0)}/{self.ecosystem.max_population if self.ecosystem else 'N/A'}")
# ... 50+ more print statements
```

#### `/home/user/tank/main.py` (12 print statements)
**Lines:** 18-33 in `run_web_server()`, Line 50 in `run_headless()`, Lines 107-109
- **Issue:** User-facing startup messages and configuration info using print()
- **Recommendation:** Use logging for consistent formatting

#### `/home/user/tank/scripts/run_until_generation.py` (56 print statements)
**Lines:** 26-120
- **Issue:** All stats output and reports use print() instead of logging
- **Recommendation:** Migrate to logging.info() with optional file output

#### `/home/user/tank/backend/test_integration.py` (22 print statements)
**Lines:** 11-212
- **Issue:** Test output uses print instead of proper test logging
- **Recommendation:** Use logging or test framework logging

#### `/home/user/tank/tests/` (Various test files with 130+ print statements)
- **Files:** test_fish_pause_fix.py, test_algorithmic_evolution.py, test_algorithm_tracking.py, test_evolution_fixes.py
- **Issue:** Test output and debugging uses print() extensively
- **Recommendation:** Use logging module with test-specific handlers

---

## 2. MAGIC NUMBERS THAT SHOULD BE CONSTANTS

### 2.1 In `simulation_engine.py`

**Line 55:** `max_population=100`
```python
self.ecosystem = EcosystemManager(max_population=100)
```
- **Fix:** Already extracted in constants.py or should be `MAX_ECOSYSTEM_POPULATION`

**Lines 227-293:** Multiple magic numbers
- **Line 227:** `range(10)` - should be `ALGORITHM_DIVERSITY_ATTEMPTS`
- **Line 238-239:** `100, SCREEN_WIDTH - 100` - should be `SPAWN_BOUNDARY_MARGIN`
- **Line 292-293:** `10` poker events limit - should be `MAX_RECENT_POKER_EVENTS`
- **Line 296:** `180` frames (6 seconds) - should be `RECENT_POKER_EVENTS_MAX_AGE`
- **Line 316:** `30` (frame rate divisor) - should use `FRAME_RATE` constant
- **Line 370:** `/48` algorithms hardcoded - should be `TOTAL_ALGORITHM_COUNT`

**Examples:**
```python
# Line 226
for _ in range(10):  # Magic number: should be MAX_DIVERSITY_ATTEMPTS

# Line 238-239
x = random.randint(100, SCREEN_WIDTH - 100)  # Magic number 100
y = random.randint(100, SCREEN_HEIGHT - 100)

# Line 293
if len(self.poker_events) > 10:  # Magic number: should be MAX_POKER_EVENTS

# Line 296
def get_recent_poker_events(self, max_age_frames: int = 180)  # Magic number: 180

# Line 370
print(f"  Unique Algorithms: {diversity_stats.get('unique_algorithms', 0)}/48")
```

### 2.2 In `core/entities.py`

**Lines 131, 860, and throughout**
- **Line 131:** `* 0.15` (AVOIDANCE_SPEED_CHANGE is used but hardcoded here)
- **Line 860:** `base_speed = 1.5` comment says "Much slower than before (was 2)" - should be named constant `CRAB_BASE_SPEED`
- Multiple floating-point multipliers (0.15, 0.2, 0.5) used inline

### 2.3 In `core/algorithms/` (Energy management)

**Lines with magic decimals:**
- `0.3`, `0.6`, `0.7`, `0.8`, `0.9`, `0.2`, `0.4` used throughout
- Examples: core/algorithms/energy_management.py, schooling.py, poker.py
- **Fix:** Extract to named constants with semantic meaning

**Examples from energy_management.py:**
```python
activity = 0.3  # Magic number (line ~152)
burst_duration *= 0.7  # Magic multiplier
rest_duration *= 0.8   # Magic multiplier
flee_speed = 0.9       # Magic speed modifier
activity = 0.3 + 0.9 * ((energy_ratio - self.parameters["min_energy_ratio"]) / ...  # Multiple magic numbers
```

### 2.4 In `core/simulators/base_simulator.py`

**Line 296+:** Time-related constants in method signatures
```python
max_age_frames: int = 180  # 6 seconds - should be constant
```

### 2.5 In `core/poker_interaction.py`

**Lines 56-59:** Card deck magic numbers
```python
rank_names = {2: '2', 3: '3', 4: '4', ..., 14: 'A'}  # Magic numbers
suit_names = {0: '♣', 1: '♦', 2: '♥', 3: '♠'}       # Magic numbers
for r in range(2, 15)  # Magic numbers 2 and 15
```
- **Fix:** Use Rank and Suit enums more consistently

---

## 3. CODE DUPLICATION

### 3.1 Print Statement Formatting (Separator Lines)

**Repeated Pattern:** `"=" * 60` and `"-" * 60` appear 50+ times
- **Files:** simulation_engine.py, main.py, scripts/run_until_generation.py, tests/
- **Fix:** Create utility function: `print_separator(char='=', width=60)`

**Examples:**
```python
# simulation_engine.py lines 329, 378, 387, 389, 392, 404, 406, 411, 413
print("=" * 60)
print("-" * 60)

# Same pattern repeated in: main.py, scripts/run_until_generation.py, backend/test_integration.py
print("=" * 80)
```

### 3.2 Fish Initialization Duplication

**Location:** /home/user/tank/core/entity_factory.py vs /home/user/tank/simulation_engine.py
- **Issue:** Initial population creation logic appears in multiple places
- **Fix:** Consolidate to single factory method

### 3.3 Separator String Width Inconsistency

**Issue:** Mixed use of 60, 80, and variable-width separators
- Lines with `"=" * 60`
- Lines with `"=" * 80` (scripts/run_until_generation.py)
- Should standardize to one width constant

### 3.4 Algorithm Parameter Mutation

**Multiple files:** core/algorithms/__init__.py, core/genetics.py
- **Issue:** Similar mutation logic is duplicated across multiple algorithm files
- **Recommendation:** Extract to base class or utility function

### 3.5 Stats Dictionary Retrieval

**Pattern:** `stats.get('key', default)` repeated extensively
```python
# Lines 330-343 in simulation_engine.py have similar patterns:
stats.get('frame_count', 0)
stats.get('time_string', 'N/A')
stats.get('total_population', 0)
stats.get('current_generation', 0)
# ... etc
```

---

## 4. UNUSED IMPORTS

### 4.1 In `backend/simulation_runner.py`
**Line 5:** `from typing import List, Optional, Dict, Any`
- Check if all are used (especially `Dict` and `Any` - verify usage)

### 4.2 In `core/entities.py`
- Verify all imported constants from core.constants are actually used

### 4.3 In `core/algorithms/__init__.py`
- **Line 14-15:** `import random` and `from typing import Optional`
- Check if actually used in the module's exported functions

---

## 5. COMMENTED-OUT CODE

### 5.1 Test Files with Comments
- **Location:** Multiple test files
- **Issue:** Commented debugging code and old test patterns still present
- **Examples:** Lines like `# print(...)` and `# if condition:` patterns
- **Recommendation:** Remove unless serving as documentation examples

### 5.2 Algorithm Documentation Comments
- **Files:** core/behavior_algorithms.py, core/algorithms/ files
- **Issue:** Some inline comments explain old implementations
- **Fix:** Clean up outdated explanations or formalize as docstrings

---

## 6. TODO COMMENTS

**Finding:** No explicit TODO/FIXME comments found using grep
- This is GOOD - codebase appears well-maintained in this regard

---

## 7. INCONSISTENT NAMING OR FORMATTING

### 7.1 Magic Number Parameter Names

**Inconsistency:** Parameters with magic number defaults
- `max_age_frames: int = 180` - should use named constant instead
- `max_frames: int = 10000` - should reference constant
- `stats_interval: int = 300` - should reference constant

### 7.2 Hard-coded Algorithm Count

**Locations:**
- `simulation_engine.py:370` - `/48` hardcoded
- `core/constants.py:182` - `TOTAL_ALGORITHM_COUNT = 48` defined
- **Issue:** Value used in print statement instead of using constant

**Example:**
```python
# Should be:
print(f"  Unique Algorithms: {diversity_stats.get('unique_algorithms', 0)}/{TOTAL_ALGORITHM_COUNT}")
# Instead of:
print(f"  Unique Algorithms: {diversity_stats.get('unique_algorithms', 0)}/48")
```

### 7.3 Inconsistent Frame Rate Usage

**Issue:** Frame rate (30 fps) hardcoded in multiple places
- `backend/simulation_runner.py:32` - `self.fps = 30`
- `simulation_engine.py:316` - `/ 30` divisor
- `core/constants.py:6` - `FRAME_RATE = 30` defined

Should consistently use `FRAME_RATE` constant

### 7.4 Variable Naming: `vx, vy` vs `velocity_x, velocity_y`

**Files:** core/algorithms/schooling.py, core/algorithms/territory.py
- Mixed use of shorthand and full names
- Should standardize to one style

### 7.5 Position Variable Names

**Issue:** Mixed naming patterns in different modules
- `Vector2` class used consistently (good)
- But some code uses `(x, y)` tuples while others use Vector2
- Should be more consistent

---

## 8. PYTHON BEST PRACTICES VIOLATIONS

### 8.1 Print-based Logging

**Critical Issue:** 394 print() statements should use logging module
- **Benefit:** Can control log levels, format, output destinations
- **Priority:** HIGH - affects debugging and production monitoring
- **Example Migration:**
```python
# Before:
print(f"Frame: {stats.get('frame_count', 0)}")

# After:
logger.info("Frame: %d", stats.get('frame_count', 0))
```

### 8.2 Magic Numbers in Code

**Impact:** Reduces readability and maintainability
- **Priority:** MEDIUM
- **Example:** Line 227 `range(10)` should be named constant

### 8.3 Inconsistent Docstring Format

Some modules use detailed docstrings while others are sparse
- Should enforce consistent docstring style across codebase

### 8.4 Type Hints

**Status:** Codebase uses type hints well (good practice)
- Could improve: some functions still missing return type hints

### 8.5 Code Organization

**Observation:** Core simulation logic duplicated between
- `simulation_engine.py` (headless)
- `core/simulators/base_simulator.py` (shared base class)
- Good: BaseSimulator exists to reduce duplication, but may not be complete

### 8.6 Constants Organization

**Issue:** Some constants scattered across files
- `core/constants.py` - good centralization
- But some algorithmic constants in algorithm files themselves
- Recommendation: Extract to core/algorithm_constants.py

### 8.7 Function Length

Several functions are quite long (print_stats, handle_reproduction, etc.)
- Should be refactored into smaller, focused functions

---

## 9. SPECIFIC PROBLEMATIC PATTERNS

### 9.1 Inline Statistics Dictionary Access

**Pattern:** Repeated `stats.get('key', default)` calls
- **Location:** simulation_engine.py:330-378
- **Fix:** Create helper function or cache commonly-accessed values

### 9.2 Hardcoded Port Numbers

**Location:** main.py:30 - `port=8000`
- **Fix:** Extract to constants: `BACKEND_PORT = 8000`, `FRONTEND_PORT = 3000`

**Line 30:**
```python
uvicorn.run(app, host="0.0.0.0", port=8000)  # Magic number
```

### 9.3 Hardcoded File Paths

**Location:** Various files referencing URLs
- `main.py:23-24` - hardcoded URLs should be constants or config

### 9.4 Repeated Separator Pattern

**Efficiency:** `"=" * 60` computed multiple times
- Should be a constant: `SEPARATOR_WIDE = "=" * 60`

---

## PRIORITY FIXES (Recommended Order)

### 🔴 HIGH PRIORITY
1. **Replace 394 print statements with logging calls**
   - Files: simulation_engine.py, main.py, scripts/run_until_generation.py, tests/
   - Impact: Essential for production code
   - Estimated lines to change: ~400

2. **Extract magic numbers to constants**
   - Files: simulation_engine.py, core/entities.py, core/algorithms/
   - Impact: Improves maintainability
   - Estimated lines to change: ~80

### 🟡 MEDIUM PRIORITY
3. **Remove/consolidate print formatting duplication**
   - Create utility: `print_separator()`, `print_stats_header()`
   - Impact: ~50 lines reduced
   
4. **Standardize frame rate usage**
   - Use FRAME_RATE constant everywhere
   - Files: simulation_engine.py, backend/simulation_runner.py

### 🟢 LOW PRIORITY
5. **Clean up commented code in test files**
   - Impact: Code clarity
   - Estimated lines: ~20

6. **Standardize variable naming conventions**
   - `vx, vy` → `velocity_x, velocity_y` (or keep consistent shorthand)
   - Impact: Code readability

---

## FILES REQUIRING CHANGES

**By Priority:**
1. `/home/user/tank/simulation_engine.py` - 55+ print statements, 10+ magic numbers
2. `/home/user/tank/scripts/run_until_generation.py` - 56+ print statements
3. `/home/user/tank/core/entities.py` - 5+ magic numbers, code clarity
4. `/home/user/tank/core/algorithms/` (all files) - multiple magic decimals
5. `/home/user/tank/tests/` (all test files) - 130+ print statements
6. `/home/user/tank/main.py` - 12 print statements, hardcoded values
7. `/home/user/tank/backend/` - logging setup improvements

---

## Summary Statistics

| Category | Count | Priority |
|----------|-------|----------|
| Print Statements | 394 | HIGH |
| Magic Numbers | 60+ | HIGH |
| Duplicated Code Patterns | 8+ | MEDIUM |
| Unused Imports | 3-5 | LOW |
| Commented Code | 20+ | LOW |
| TODO Comments | 0 | N/A |
| Inconsistent Naming | 10+ | MEDIUM |

**Total Issues Found:** 500+
**Estimated Cleanup Effort:** 3-4 hours for complete refactoring
