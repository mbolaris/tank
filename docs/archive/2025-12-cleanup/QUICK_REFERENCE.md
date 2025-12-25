# Quick Reference: Code Issues by File

## File-by-File Issues Summary

### 🔴 HIGH PRIORITY

#### simulation_engine.py (849 lines via core/simulation/engine.py)
- Status: Clean ✅ - refactored into orchestrator pattern
- Delegates to systems: CollisionSystem, PokerSystem, ReproductionSystem

#### backend/simulation_runner.py (302 lines)
- **Line 32**: `self.fps = 30` (use `FRAME_RATE` constant instead)
- **Line 264**: Local `SPAWN_MARGIN = 50` (use `SPAWN_MARGIN_PIXELS` constant)
- **Lines 255-287**: Duplicates `spawn_emergency_fish()` from ReproductionSystem
- **Line 147**: Undefined `elapsed_time` attribute access (with fallback)


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
- ✅ Self-contained: no longer inherits from BaseSimulator
- ✅ Phase-based execution with explicit UpdatePhase enum
- ✅ Delegates to specialized systems (CollisionSystem, PokerSystem, etc.)
- ✅ Independent of pygame/visualization
- ✅ Thread-safe with SimulationRunner

### Simulation Determinism
- ✅ RNG passed explicitly to all systems
- ✅ Collision processing order is deterministic
- ✅ Same seed produces identical runs

### Code Organization
- **SimulationEngine** (coordinator):
  - Owns systems and managers
  - Runs update phases in order
  - Does NOT contain business logic

- **Systems** (business logic):
  - `CollisionSystem` - all collision detection and resolution
  - `PokerSystem` - poker games and post-poker reproduction
  - `ReproductionSystem` - asexual reproduction and emergency spawning
  - `EntityLifecycleSystem` - birth/death tracking

### No Pygame
- ✅ All pygame imports removed
- ✅ Uses Vector2, Rect from core modules
- ✅ Pure Python simulation


---

## Magic Numbers Found

| File | Line | Value | Should Be | Type |
|------|------|-------|-----------|------|
| simulation_runner.py | 32 | 30 | FRAME_RATE | fps |
| simulation_runner.py | 264 | 50 | SPAWN_MARGIN_PIXELS | spawn margin |

*Note: Most magic numbers have been extracted to config modules.*

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

