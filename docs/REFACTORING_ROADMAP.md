# Architecture Refactoring Roadmap

This document tracks remaining architectural improvements to be made to the simulation codebase.

## Priority 1: Inline BaseSimulator into SimulationEngine

**Status**: Not Started  
**Effort**: 2-3 hours  
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

**Status**: Not Started  
**Effort**: 2-3 hours  
**Impact**: High (cleaner update loop, easier to add phases)

### Problem
The `update()` method has ~150 lines of inline phase logic. We built `PhaseRunner` but don't use it.

### Current State
```python
def update(self):
    # ===== PHASE: FRAME_START =====
    self._current_phase = UpdatePhase.FRAME_START
    self.frame_count += 1
    self.lifecycle_system.update(self.frame_count)
    # ... 150 more lines
```

### Proposed Solution
1. Each phase becomes a method: `_phase_frame_start()`, `_phase_time_update()`, etc.
2. Or better: each phase's logic moves into a System that declares its phase
3. `update()` becomes: `self._phase_runner.run_all(context)`

### Benefits
- Adding a new phase = adding a new system
- Phases are self-documenting
- Easier to test individual phases

---

## Priority 4: Extract EnergyTracker from EcosystemManager

**Status**: Not Started (mentioned in ARCHITECTURE_REVIEW.md)  
**Effort**: 1-2 hours  
**Impact**: Medium

### Problem
`EcosystemManager` (650+ lines, 67 methods) has too many responsibilities including energy tracking.

### Proposed Solution
Create `core/services/energy_tracker.py` with:
- `record_energy_snapshot()`
- `record_energy_burn()`
- Energy delta calculations
- Energy flow statistics

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
