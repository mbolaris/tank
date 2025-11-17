# Architecture Documentation

## Recent Architectural Improvements

This document describes the major architectural improvements made to the codebase to improve code quality, reduce duplication, and enhance maintainability.

### 1. BaseSimulator Abstraction (2025-11-17)

**Problem**: The codebase had two simulation implementations (`FishTankSimulator` and `SimulationEngine`) with approximately 200+ lines of duplicated logic including:
- Collision handling
- Reproduction logic
- Fish death recording
- Entity boundary checking
- Auto-food spawning

**Solution**: Created `core/simulators/base_simulator.py` with a `BaseSimulator` abstract base class that contains all shared simulation logic.

**Benefits**:
- **Eliminated ~200 lines of duplicate code**
- **Single source of truth** for simulation logic
- **Easier maintenance** - bug fixes only need to be applied once
- **Consistent behavior** between graphical and headless modes

**Architecture**:
```
BaseSimulator (Abstract)
├── handle_collisions()
├── handle_fish_collisions()
├── handle_food_collisions()
├── handle_reproduction()
├── record_fish_death()
├── spawn_auto_food()
├── keep_entity_on_screen()
└── handle_poker_result()

FishTankSimulator (Pygame)
├── Implements abstract methods for pygame sprites
└── check_collision() using pygame.sprite.collide_rect

SimulationEngine (Headless)
├── Implements abstract methods for pure entities
└── check_collision() using bounding box math
```

**Files Modified**:
- Created: `core/simulators/__init__.py`
- Created: `core/simulators/base_simulator.py`
- Modified: `fishtank.py` - Now extends BaseSimulator
- Modified: `simulation_engine.py` - Now extends BaseSimulator

### 2. UI Rendering Separation (2025-11-17)

**Problem**: `FishTankSimulator` had rendering logic mixed with game logic, violating separation of concerns:
- `draw_health_bar()` - 46 lines
- `draw_stats_panel()` - 64 lines
- `draw_poker_notifications()` - 33 lines

**Solution**: Created `rendering/ui_renderer.py` with a dedicated `UIRenderer` class responsible for all UI rendering.

**Benefits**:
- **Separation of concerns** - Rendering logic is now isolated
- **Reusability** - UI components can be reused in other visualizations
- **Testability** - UI rendering can be tested independently
- **Cleaner code** - `FishTankSimulator` is now more focused on simulation logic

**Architecture**:
```
UIRenderer
├── draw_health_bar(fish)
├── draw_stats_panel(ecosystem, time_system, paused)
└── draw_poker_notifications(notifications)
```

**Usage**:
```python
# In FishTankSimulator
self.ui_renderer = UIRenderer(self.screen, self.stats_font)
self.ui_renderer.set_frame_count(self.frame_count)
self.ui_renderer.draw_health_bar(fish)
self.ui_renderer.draw_stats_panel(self.ecosystem, self.time_system, self.paused)
self.ui_renderer.draw_poker_notifications(self.poker_notifications)
```

**Files Modified**:
- Created: `rendering/ui_renderer.py`
- Modified: `fishtank.py` - Now uses UIRenderer instead of inline rendering

## Code Quality Metrics

### Before Improvements
- **Duplicate Code**: ~200 lines duplicated between fishtank.py and simulation_engine.py
- **Large Files**:
  - `fishtank.py`: 597 lines
  - `simulation_engine.py`: 436 lines
  - `core/entities.py`: 931 lines
  - `core/ecosystem.py`: 800 lines
- **Mixed Concerns**: UI rendering mixed with simulation logic

### After Improvements
- **Duplicate Code**: Eliminated ~200 lines of duplication
- **Better Organization**:
  - Shared logic: `core/simulators/base_simulator.py` (262 lines)
  - UI rendering: `rendering/ui_renderer.py` (200 lines)
  - Simulation implementations: Significantly reduced
- **Clear Separation**: Simulation logic, rendering, and UI are now properly separated

## Design Patterns Used

### 1. Template Method Pattern
`BaseSimulator` uses the template method pattern:
- Defines the skeleton of algorithms (`handle_collisions`, `handle_reproduction`)
- Subclasses implement specific steps (`check_collision`, `add_entity`, `remove_entity`)

### 2. Strategy Pattern
Different collision detection strategies:
- **Pygame mode**: Uses `pygame.sprite.collide_rect()`
- **Headless mode**: Uses bounding box mathematics

### 3. Dependency Injection
`UIRenderer` receives dependencies through constructor:
```python
def __init__(self, screen: pygame.Surface, stats_font: pygame.font.Font):
    self.screen = screen
    self.stats_font = stats_font
```

## Future Improvements

Based on the code analysis, recommended future improvements include:

### High Priority
1. **Refactor EcosystemManager** (800 lines)
   - Split into specialized managers: `PopulationManager`, `AlgorithmTracker`, `PokerStatsManager`
   - Current: God object anti-pattern
   - Target: Multiple focused managers

2. **Component-based Fish Architecture**
   - Current: Fish class is 463 lines with mixed concerns
   - Target: Split into `EnergyComponent`, `ReproductionComponent`, `MemoryComponent`

### Medium Priority
3. **Replace Magic Numbers**
   - Extract hardcoded values (15.0, 360, 220, etc.) to named constants
   - Improve code readability and maintainability

4. **Event System**
   - Implement observer pattern for ecosystem events
   - Replace direct method calls with event publishing/subscribing

### Low Priority
5. **Reorganize Root Directory**
   - Move simulation files to `core/simulators/`
   - Better project structure

6. **Custom Exception Hierarchy**
   - Define `SimulationError`, `EntityError`, `CollisionError`
   - Consistent error handling

## Best Practices Followed

1. **DRY (Don't Repeat Yourself)**: Eliminated code duplication through abstraction
2. **Single Responsibility**: Each class now has a clearer, more focused purpose
3. **Open/Closed Principle**: Base classes are open for extension, closed for modification
4. **Dependency Inversion**: High-level modules depend on abstractions, not concrete implementations
5. **Type Hints**: All new code includes comprehensive type hints
6. **Documentation**: All new classes and methods include docstrings

## Testing Recommendations

To verify these architectural improvements:

1. **Run both simulators** to ensure behavior is consistent:
   ```bash
   python main.py  # Graphical mode
   python backend/simulation_runner.py  # Headless mode
   ```

2. **Verify collision handling** works identically in both modes
3. **Check UI rendering** still works correctly in graphical mode
4. **Ensure no regressions** in existing functionality

## Conclusion

These architectural improvements have:
- **Reduced code duplication by ~200 lines**
- **Improved separation of concerns**
- **Made the codebase more maintainable**
- **Established patterns for future refactoring**

The changes maintain backward compatibility while significantly improving code quality and maintainability.
