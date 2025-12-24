# Architecture Refactoring Roadmap

This document tracks remaining architectural improvements to be made to the simulation codebase.

## Priority 1: Inline BaseSimulator into SimulationEngine

**Status**: Documented (see design note in base_simulator.py)  
**Effort**: 2-3 hours for full inline  
**Impact**: High (removes unnecessary abstraction layer)

### Problem
`BaseSimulator` (932 lines) is an ABC with only ONE concrete implementation (`SimulationEngine`). The docstring says it's "shared between graphical and headless simulators" but the graphical simulator no longer exists.

### Current Issues
- Unnecessary inheritance adds complexity
- Logic split between two files
- Abstract methods that only have one implementation
- Hard to see the full picture of the engine

### Proposed Solution
1. Move state (`frame_count`, `paused`) directly to `SimulationEngine`
2. Move collision handling to a `CollisionHandler` module or `CollisionSystem`  
3. Move post-poker reproduction logic to `ReproductionSystem`
4. Delete `BaseSimulator` and `core/simulators/` folder

### Change Steps
1. Create `core/simulation/collision_handler.py` with collision logic from `BaseSimulator`
2. Move `_attempt_post_poker_reproduction` to `ReproductionSystem` or `PokerSystem`
3. Inline remaining methods into `SimulationEngine`
4. Remove inheritance from `SimulationEngine`
5. Delete `core/simulators/` folder
6. Update all imports

---

## Priority 2: Remove Pure Delegation Methods

**Status**: Not Started  
**Effort**: 30 minutes  
**Impact**: Medium (simpler API, less code)

### Problem
`SimulationEngine` has several methods that are pure pass-throughs to systems:

```python
def handle_reproduction(self):
    self.reproduction_system.update(self.frame_count)

def handle_mixed_poker_games(self):
    self.poker_system.handle_mixed_poker_games()
```

### Proposed Solution
Either:
1. Remove these methods and have callers access systems directly
2. OR keep them for API stability if backwards compatibility is important

### Blocked By
- Priority 1 (BaseSimulator uses these delegation methods via inheritance)

---

## Priority 3: Use PhaseRunner in update()

**Status**: ✅ Partially Complete (Phase Methods Extracted)  
**Effort**: 2-3 hours for full PhaseRunner integration  
**Impact**: High (cleaner update loop, easier to add phases)

### Problem
The `update()` method had ~150 lines of inline phase logic. We built `PhaseRunner` but don't use it.

### What We've Done
Extracted each phase into its own method:
- `_phase_frame_start()` - Reset counters, increment frame
- `_phase_time_update()` - Advance day/night cycle
- `_phase_environment()` - Update ecosystem and detection
- `_phase_entity_act()` - Update all entities
- `_phase_lifecycle()` - Process deaths, add/remove entities
- `_phase_spawn()` - Auto-spawn food
- `_phase_collision()` - Handle collisions
- `_phase_reproduction()` - Mating and emergency spawns
- `_phase_frame_end()` - Stats and cache updates

The main `update()` is now ~30 lines showing phase order clearly.

### Future Work
The next step would be to convert these phase methods into proper System classes
that declare their phase via `@runs_in_phase`, then use PhaseRunner for execution.

### Benefits Achieved
- ✅ Readability - phase order is immediately visible
- ✅ Testability - individual phases can be unit tested
- ✅ Documentation - each phase has its own docstring

---

## Priority 4: Extract EnergyTracker from EcosystemManager

**Status**: ✅ Already Complete  
**Impact**: N/A (was already done)

### What Was Done
`EnergyTracker` already exists at `core/services/energy_tracker.py` (273 lines).

Features include:
- `record_energy_gain()` / `record_energy_burn()`
- `record_energy_delta()` for signed deltas
- `record_energy_snapshot()` for historical tracking
- `get_energy_delta()` for time-window comparisons
- Separate tracking for fish and plant energy pools
- Per-frame buffering with automatic rollup

`EcosystemManager` delegates to `EnergyTracker` for all energy accounting.

---

## Priority 5: Consider Removing HeadlessSimulator Wrapper

**Status**: Not Started  
**Effort**: 15 minutes  
**Impact**: Low

### Problem
`HeadlessSimulator` is a thin wrapper that just sets defaults on `SimulationEngine`.

### Current Usage
Only 2 scripts use it:
- `scripts/run_headless_test.py`  
- `scripts/verify_plants.py`

### Proposed Solution
Replace usages with:
```python
engine = SimulationEngine(config=SimulationConfig.headless_fast())
engine.run_headless(max_frames=300, stats_interval=100)
```

This is slightly more verbose but removes a wrapper class.

---

## Completed Refactorings

### ✅ SimulationEngine Decomposition (Dec 2024)
- Split 971-line monolith into `core/simulation/` package
- Created `EntityManager` for entity lifecycle
- Created `SystemRegistry` for system management
- Maintained backward compatibility via re-exports

### ✅ Poker System Consolidation (Dec 2024)
- Organized scattered poker files into `core/poker/` package
- Clear separation: core/, evaluation/, strategy/

### ✅ Stats System Refactoring (Dec 2024)
- Extracted `GeneticStats` into `core/services/stats/`
