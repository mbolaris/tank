# Architecture Refactoring Roadmap

This document tracks architectural improvements made to the simulation codebase.

**Last Updated**: December 2024

---

## ✅ COMPLETED

### Priority 1: Inline BaseSimulator into SimulationEngine

**Status**: ✅ Complete
**Completed**: December 2024
**Impact**: High (removed unnecessary abstraction layer)

The `BaseSimulator` class has been completely removed. All logic was:
- Collision iteration → Moved to `CollisionSystem._do_update()`
- Post-poker reproduction → Moved to `PokerSystem`
- Fish death handling → Moved to `EntityLifecycleSystem`
- Screen bounds → Inlined into `SimulationEngine`

The `core/simulators/` folder has been deleted.

---

### Priority 2: Pure Delegation Methods

**Status**: ✅ Intentionally Kept
**Decision**: Keep delegation methods for API stability

Methods like `handle_reproduction()` and `handle_mixed_poker_games()` were kept
because they provide a stable public API. Callers don't need to know about
internal system organization.

---

### Priority 3: Phase-Based Update Loop

**Status**: ✅ Complete
**Completed**: December 2024

The `update()` method was refactored into explicit phase methods:
- `_phase_frame_start()` - Reset counters, increment frame
- `_phase_time_update()` - Advance day/night cycle
- `_phase_environment()` - Update ecosystem and detection
- `_phase_entity_act()` - Update all entities
- `_phase_lifecycle()` - Process deaths, add/remove entities
- `_phase_spawn()` - Auto-spawn food
- `_phase_collision()` - Handle collisions
- `_phase_reproduction()` - Asexual reproduction and emergency spawns
- `_phase_frame_end()` - Stats and cache updates

The main `update()` is now ~30 lines showing phase order clearly.

---

### Priority 4: Extract EnergyTracker from EcosystemManager

**Status**: ✅ Complete

`EnergyTracker` exists at `core/services/energy_tracker.py` (273 lines).
`EcosystemManager` delegates to `EnergyTracker` for all energy accounting.

---

### Priority 5: HeadlessSimulator Wrapper

**Status**: ✅ Removed / Not Needed

`SimulationEngine` now handles headless mode directly via config:
```python
engine = SimulationEngine(config=SimulationConfig.production(headless=True))
engine.run_headless(max_frames=300, stats_interval=100)
```

---

## Previously Completed Refactorings

### ✅ SimulationEngine Decomposition (Dec 2024)
- Split monolith into `core/simulation/` package
- Created `EntityManager` for entity lifecycle
- Created `SystemRegistry` for system management
- Maintained backward compatibility via re-exports

### ✅ Poker System Consolidation (Dec 2024)
- Organized scattered poker files into `core/poker/` package
- Clear separation: core/, evaluation/, strategy/

### ✅ Stats System Refactoring (Dec 2024)
- Extracted `GeneticStats` into `core/services/stats/`

### ✅ FishVisualState Extraction (Dec 2024)
- Separated rendering concerns into `core/entities/visual_state.py`
- Fish class no longer has visual timer logic inline

### ✅ EnergyState Value Object (Dec 2024)
- Created `core/fish/energy_state.py` for consistent energy checking
- Single source of truth for energy thresholds

### ✅ Dead Mating Code Removal (Dec 2024)
- Removed `attempt_mating()` from ReproductionComponent (always returned False)
- Removed `calculate_mate_attraction()` from ReproductionComponent
- Sexual reproduction only occurs via poker games

---

## Future Considerations

### Optional: Extract SpatialGrid
`environment.py` (761 lines) contains both `SpatialGrid` and `Environment`.
Could extract `SpatialGrid` to `core/spatial_grid.py` for cleaner separation.

### Optional: Split poker_system.py
At 899 lines, `poker_system.py` handles fish-fish, fish-plant, and plant-plant
poker. Could extract `MixedPokerHandler` for fish-plant logic.

### Optional: TankWorld Wrapper Audit
`TankWorld` is a thin wrapper around `SimulationEngine`. Consider deprecating
if only legacy code uses it.

---

## Architecture Summary

```
SimulationEngine (coordinator)
├── EntityManager (entity CRUD)
├── SystemRegistry (system lifecycle)
├── Systems
│   ├── CollisionSystem (all collision detection/resolution)
│   ├── PokerSystem (poker games + post-poker reproduction)
│   ├── ReproductionSystem (asexual + emergency spawning)
│   ├── EntityLifecycleSystem (birth/death tracking)
│   ├── TimeSystem (day/night cycle)
│   └── FoodSpawningSystem (auto food spawning)
├── Managers
│   ├── PlantManager
│   └── EcosystemManager
└── Services
    ├── StatsCalculator
    └── EnergyTracker
```

The architecture follows these principles:
1. **Slim Orchestrator**: Engine coordinates but doesn't contain business logic
2. **Phase-Based Execution**: Explicit, ordered update phases prevent timing bugs
3. **Protocol-First Design**: Runtime-checkable protocols for decoupling
4. **Component Composition**: Fish uses EnergyComponent, LifecycleComponent, etc.
