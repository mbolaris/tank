# Quick Reference: Code Issues by File

## File-by-File Issues Summary

### 🔴 HIGH PRIORITY

#### simulation_engine.py (513 lines)
- **Lines 339, 275**: Magic `radius=100` hardcoded (should be `COLLISION_QUERY_RADIUS`)
- **Lines 238-304**: `spawn_emergency_fish()` duplicates backend code
- Status: Otherwise clean ✅

#### backend/simulation_runner.py (302 lines)
- **Line 32**: `self.fps = 30` (use `FRAME_RATE` constant instead)
- **Line 264**: Local `SPAWN_MARGIN = 50` (use `SPAWN_MARGIN_PIXELS` constant)
- **Lines 255-287**: Duplicates `spawn_emergency_fish()` from simulation_engine.py
- **Line 147**: Undefined `elapsed_time` attribute access (with fallback)

#### core/simulators/base_simulator.py (405 lines)
- **Lines 202, 239, 277**: Magic radius values `100`, `150` hardcoded
- Should define constants: `COLLISION_QUERY_RADIUS`, `MATING_QUERY_RADIUS`

### 🟡 MEDIUM PRIORITY

#### tests/ (All test files)
- **test_parity.py**: Marked `xfail` - non-deterministic behavior
- **test_parity.py, test_*.py**: 130+ print() statements should use logging
- **test_parity.py:18,26,36,41-45,48,57**: Lines with print()

#### core/ecosystem.py (1,340 lines)
- **God object**: Too many responsibilities
- Should refactor into:
  - PopulationManager
  - AlgorithmTracker
  - StatsCollector
  - DiversityAnalyzer

#### core/entities.py (1,366 lines)
- **Fish class (463 lines)**: Should be split into components
- Currently functional but large

### 🟢 LOW PRIORITY

#### scripts/run_until_generation.py (56+ print statements)
- Should use logging module instead of print()

#### All files
- **266 remaining print() statements** across codebase
- Main.py and simulation_engine.py partially converted ✅
- Tests and scripts still need conversion

---

## Code Duplication Hotspots

### Fish Spawning (3 implementations)
1. `simulation_engine.py:238-304` - Emergency spawning
2. `backend/simulation_runner.py:255-287` - Command spawning
3. `core/entity_factory.py` - Initial population

**Solution**: Create `FishSpawner` utility class

### Separator Formatting
- Used 50+ times with pattern `"=" * SEPARATOR_WIDTH`
- Already extracted to constant ✅

### Spatial Query Radii
- `100` used in collision checks
- `150` used in mating checks
- `radius=100` appears 3+ times

**Solution**: Extract to constants

---

## Architecture Verification Checklist

### Headless Mode (SimulationEngine)
- ✅ Inherits from BaseSimulator
- ✅ Implements required abstract methods
- ✅ Uses shared collision/reproduction logic
- ✅ Independent of pygame/visualization
- ✅ Thread-safe with SimulationRunner

### Graphical Mode Equivalence
- ✅ Both use BaseSimulator for core logic
- ✅ Collision detection identical
- ✅ Reproduction identical
- ✅ Entity updates identical
- ⚠️ Non-deterministic: Different runs may vary even with same seed

### Code Sharing
- **Shared (BaseSimulator)**:
  - `handle_collisions()`
  - `handle_reproduction()`
  - `spawn_auto_food()`
  - `record_fish_death()`
  - All spatial grid operations

- **Headless-Only**:
  - `run_headless()`
  - `print_stats()`
  - `add_poker_event()`

### No Pygame
- ✅ All pygame imports removed
- ✅ Uses Vector2, Rect from core modules
- ✅ Pure Python simulation

---

## Magic Numbers Found

| File | Line | Value | Should Be | Type |
|------|------|-------|-----------|------|
| simulation_engine.py | 339, 275 | 100 | COLLISION_QUERY_RADIUS | radius |
| simulation_engine.py | 264 | 50 | SPAWN_MARGIN_PIXELS | spawn margin |
| base_simulator.py | 202, 277 | 100 | COLLISION_QUERY_RADIUS | radius |
| base_simulator.py | 239, 277 | 150 | MATING_QUERY_RADIUS | radius |
| simulation_runner.py | 32 | 30 | FRAME_RATE | fps |
| simulation_runner.py | 264 | 50 | SPAWN_MARGIN_PIXELS | spawn margin |

---

## Print Statement Locations (266 total)

| File | Count | Status |
|------|-------|--------|
| simulation_engine.py | 55+ | ✅ Converted to logger |
| main.py | 12 | ✅ Converted to logger |
| scripts/run_until_generation.py | 56+ | ❌ Still print() |
| tests/test_parity.py | 30+ | ❌ Still print() |
| tests/test_*.py | 100+ | ❌ Still print() |
| backend/test_integration.py | 22 | ❌ Still print() |
| Other test files | 30+ | ❌ Still print() |

**Note**: Logger already set up in simulation_engine.py, just need to migrate remaining files

---

## Constants Already Defined (Good!)

✅ `SEPARATOR_WIDTH` - used correctly
✅ `SPAWN_MARGIN_PIXELS` - defined in constants.py:240
✅ `FRAME_RATE` - defined in constants.py:6
✅ `SCREEN_WIDTH`, `SCREEN_HEIGHT` - defined and used
✅ `MAX_DIVERSITY_SPAWN_ATTEMPTS` - defined in constants.py:239
✅ `TOTAL_ALGORITHM_COUNT` - defined in constants.py:182
✅ All energy/reproduction thresholds defined

---

## Testing & Verification Commands

```bash
# Run all tests
pytest tests/ -v

# Run headless mode
python main.py --headless --max-frames 1000

# Run with seed for reproducibility (note: not fully deterministic)
python main.py --headless --max-frames 1000 --seed 42

# Run parity test (marked xfail)
pytest tests/test_parity.py -v

# Check specific test
pytest tests/test_simulation.py -v

# Run test that spawns emergency fish
python -c "from simulation_engine import SimulationEngine; e = SimulationEngine(); e.setup(); e.spawn_emergency_fish()"
```

---

## Estimated Effort to Fix

| Task | Files | Time |
|------|-------|------|
| Extract magic numbers | 3 | 30 min |
| Consolidate spawn logic | 3 | 1 hour |
| Fix print statements | 7 | 1 hour |
| Extract spatial constants | 1 | 15 min |
| Refactor EcosystemManager | 1 | 4+ hours |
| Refactor Fish class | 1 | 2+ hours |
| Fix test non-determinism | 1 | 2+ hours |

**Quick Wins (2 hours total)**:
1. Fix magic numbers in backend (30 min)
2. Extract spatial constants (15 min)
3. Create FishSpawner utility (45 min)

