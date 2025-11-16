# Fish Tank Simulation - Codebase Architecture Analysis

## Executive Summary

The fish tank simulation has **6,421 lines** of Python code organized into **18 main files**. The architecture shows **TIGHT COUPLING** between pure simulation logic and pygame rendering code, making it difficult to test, extend, or reuse the simulation engine independently.

### Key Findings

1. **Pure Simulation Logic (~1,600 lines)**: Already isolated and decoupled from pygame
   - `behavior_algorithms.py` (2,731 lines) - Pure algorithms, no pygame
   - `genetics.py`, `neural_brain.py`, `ecosystem.py`, `environment.py`, `time_system.py` - All pure

2. **Main Coupling Points (3 files)**:
   - **agents.py** (778 lines) - CRITICAL: Mixes entity logic with pygame.sprite.Sprite
   - **fishtank.py** (558 lines) - HEAVY: Mixes simulation with rendering
   - **movement_strategy.py** (128 lines) - MODERATE: Uses pygame.sprite.collide_rect

3. **Rendering Code (~800 lines)**: Tightly integrated into simulation classes
   - Image loading, animation, and rendering mixed into entity classes
   - Game loop and rendering interleaved in fishtank.py

---

## Current Architecture Overview

```
MONOLITHIC STRUCTURE (Current):
────────────────────────────────

pygame (library) 
    ↑ (tightly coupled)
    │
┌───┴───────────────────────────────────────────┐
│        FISHTANK.PY (Game Loop)                │
│  - Simulation logic (update)                  │
│  - Rendering (render, draw_health_bar, etc)  │
│  - Event handling                             │
│  - All mixed together                         │
└───┬───────────────────────────────────────────┘
    │
    ├─→ agents.py (778 lines)
    │   ├─ Entity logic (life cycle, energy, reproduction)
    │   └─ Pygame rendering (extends Sprite, handles images)
    │   └─ Animation management
    │
    ├─→ movement_strategy.py (128 lines)
    │   ├─ Movement algorithms (pure)
    │   └─ pygame.sprite.collide_rect() (coupled)
    │
    ├─→ evolution_viz.py (275 lines)
    │   └─ All pygame rendering
    │
    └─→ PURE LOGIC (buried in imports)
        ├─ behavior_algorithms.py (no pygame)
        ├─ genetics.py (no pygame)
        ├─ neural_brain.py (minimal pygame)
        ├─ ecosystem.py (no pygame)
        ├─ environment.py (no pygame)
        ├─ time_system.py (no pygame)
        └─ constants.py (no pygame)
```

**Problem**: Cannot test or run simulation without pygame

---

## File Inventory

### Core Simulation Files (Pure Logic - No Pygame)
- `behavior_algorithms.py` (2,731 lines) - 48 parametrizable behavior algorithms
- `genetics.py` (201 lines) - Genome class with mutation/crossover
- `neural_brain.py` (250 lines) - Neural network AI (minimal pygame dependency)
- `ecosystem.py` (525 lines) - Population tracking and statistics
- `environment.py` (77 lines) - Spatial queries for agents
- `time_system.py` (130 lines) - Day/night cycle system
- `constants.py` (111 lines) - Game configuration

**Total: ~3,925 lines of pure simulation logic**

### Coupled Files (Simulation + Pygame)
- `agents.py` (778 lines) - CRITICAL COUPLING POINT
  - Base Agent class extends `pygame.sprite.Sprite`
  - Fish, Crab, Plant, Food entity classes
  - Mixes entity logic with image handling and animation
  
- `movement_strategy.py` (128 lines) - MODERATE COUPLING
  - Movement behavior classes
  - Uses `pygame.sprite.collide_rect()` for collision detection
  
- `fishtank.py` (558 lines) - HEAVY COUPLING
  - Main game controller and entry point
  - Mixes simulation update loop with pygame rendering
  - Handles pygame events

### Rendering/Visualization Files
- `image_loader.py` (18 lines) - Pygame image loading wrapper
- `evolution_viz.py` (275 lines) - Real-time visualization of evolution

### Wrappers/Interfaces
- `fishtank_pz.py` (60 lines) - PettingZoo-style environment wrapper (incomplete)

### Test Files
- `test_*.py` files in `/tests` directory

---

## Critical Coupling Points

### 1. **AGENTS.PY - THE BOTTLENECK**

**Problem**: Inherits from `pygame.sprite.Sprite`

```python
class Agent(pygame.sprite.Sprite):  # Line 30
    def __init__(self, ..., filenames: List[str], ...):
        super().__init__()
        self.animation_frames: List[Surface] = [
            ImageLoader.load_image(...) for filename in filenames  # Loads images
        ]
        self.image: Surface = self.get_current_image()
        self.rect: pygame.Rect = self.image.get_rect()
```

**Consequences**:
- Cannot instantiate entities without pygame
- Cannot test entity logic in isolation
- Cannot run simulation without rendering
- Image loading tied to pygame

**Impact on child classes**:
- `Fish` (162-525): Life cycle, energy, reproduction logic mixed with `pygame.transform.scale()` and color tinting
- `Crab` (532-618): Hunting logic tied to sprite
- `Plant` (619-707): Food production tied to sprite animation
- `Food` (708-778): Physics and sinking tied to sprite animation

### 2. **FISHTANK.PY - MIXED CONCERNS**

**Problem**: Simulation and rendering not separated

```python
class FishTankSimulator:
    def update(self):              # Simulation logic
        """Update the state of the simulation."""
        # ... simulation logic ...
        
    def render(self):              # Rendering logic
        """Render the current state to screen."""
        self.screen.fill((10, 30, 50))
        self.agents.draw(self.screen)
        pygame.display.flip()
        
    def run(self):
        while self.handle_events():
            self.update()
            self.render()          # Coupled together in game loop
```

**Consequences**:
- Cannot test simulation without rendering
- Cannot run simulation at different speed than rendering
- Cannot skip rendering
- Hard to add alternative renderers

### 3. **MOVEMENT_STRATEGY.PY - COLLISION COUPLING**

```python
def check_collision_with_food(self, sprite: 'Fish') -> None:
    for food in sprite.environment.get_agents_of_type(Food):
        if pygame.sprite.collide_rect(sprite, food):  # Pygame-specific
            sprite.vel = Vector2(0, 0)
```

**Problem**: Collision detection hardcoded to pygame sprites

**Solution**: Inject collision detection function

---

## Where Separation Would Be Beneficial

### 1. **Extract Pure Entity Classes** (Highest Priority)

**Current**: All in `agents.py` with pygame coupling
```python
# From agents.py
class Fish(Agent):
    def consume_energy(self):  # Pure logic
    def update_life_stage(self):  # Pure logic
    def can_reproduce(self):  # Pure logic
    def get_current_image(self):  # Rendering (pygame.transform.scale)
```

**Proposed**: Separate into `core/entities.py`
```python
# core/entities.py - pure, no pygame
class Fish:
    def consume_energy(self): ...
    def update_life_stage(self): ...
    def can_reproduce(self): ...
    # NO rendering logic
```

**Benefits**:
- Test entity logic without pygame
- Run simulation in tests
- Use entities with different renderers

### 2. **Extract Game Logic from Rendering**

**Current**: `fishtank.py` has `update()` + `render()` mixed

**Proposed**: Separate concerns
```python
# core/simulation_engine.py
class SimulationEngine:
    def tick(self):  # Pure simulation update
        
# rendering/game_renderer.py
class GameRenderer:
    def render(self, state):  # Pure rendering
```

**Benefits**:
- Simulation can run without rendering
- Different rendering backends possible
- Headless operation possible
- Multiple simulations parallel

### 3. **Inject Collision Detection**

**Current**: `pygame.sprite.collide_rect()` hardcoded

**Proposed**: Interface-based
```python
class MovementStrategy:
    def __init__(self, collision_detector):
        self.collision_detector = collision_detector
        
    def check_collision(self, sprite, others):
        return self.collision_detector.collides(sprite, others)
```

**Benefits**:
- Swappable collision systems
- No pygame dependency in movement logic
- Testable without sprites

---

## Proposed New Architecture

```
MODULAR STRUCTURE (Proposed):
─────────────────────────────

core/                          ← PURE SIMULATION ENGINE (no pygame)
├── entities.py               ← Entity classes (no pygame.sprite.Sprite)
├── genetics.py               ← Already pure
├── behavior_algorithms.py    ← Already pure
├── neural_brain.py           ← Already pure
├── ecosystem.py              ← Already pure
├── environment.py            ← Already pure
├── time_system.py            ← Already pure
├── collision_system.py       ← NEW: abstract collision detection
└── constants.py              ← Configuration

rendering/                     ← PYGAME RENDERING LAYER
├── sprites.py                ← Sprite adapters for entities (pygame.sprite.Sprite)
├── animation.py              ← Animation system
├── visualizer.py             ← Evolution visualization
├── renderer.py               ← Game renderer
└── image_loader.py           ← Image loading

input/                         ← INPUT HANDLING
└── event_handler.py          ← Input processing

game/                          ← GAME CONTROLLER
├── game_controller.py        ← Main game loop
└── game_state.py             ← State management

fishtank.py                   ← THIN WRAPPER (pygame.init + main loop)
fishtank_pz.py               ← PettingZoo wrapper

tests/                         ← TEST SUITE
├── test_entities.py          ← Test without pygame!
├── test_simulation.py        ← Pure simulation tests
├── test_rendering.py         ← Rendering tests (with pygame)
└── ...
```

**Benefits**:
1. Pure simulation testable without pygame
2. Multiple rendering backends possible
3. Headless operation (batch simulations)
4. Web/CLI rendering possible
5. Better code organization
6. Reusable simulation engine

---

## Refactoring Roadmap

### PHASE 1: Extract Entity Classes (2-3 hours)
**Priority**: CRITICAL - Unblocks everything else

1. Create `core/entities.py`
2. Move `Agent`, `Fish`, `Crab`, `Plant`, `Food` classes
3. Remove `pygame.sprite.Sprite` inheritance
4. Remove image loading from `__init__`
5. Keep all pure logic

**Result**: Entities testable without pygame

### PHASE 2: Extract Collision System (1 hour)
**Priority**: HIGH - Unblocks movement_strategy

1. Create `core/collision_system.py`
2. Define `CollisionDetector` interface
3. Update `movement_strategy.py` to use injected detector
4. Remove `pygame.sprite.collide_rect()`

**Result**: Movement logic testable, pluggable collision

### PHASE 3: Separate Simulation from Rendering (2-3 hours)
**Priority**: HIGH - Core refactoring

1. Create `game/simulation_engine.py` with `tick()` method
2. Create `rendering/renderer.py` for all drawing
3. Extract `update()` logic from `fishtank.py`
4. Extract rendering code from `fishtank.py`
5. Keep `fishtank.py` as thin wrapper

**Result**: Simulation independent of rendering

### PHASE 4: Create Sprite Adapters (1-2 hours)
**Priority**: MEDIUM - Cleanup

1. Create `rendering/sprites.py`
2. Implement `FishSprite`, `CrabSprite`, etc. as wrappers
3. Move pygame-specific rendering here
4. Adapter pattern between `core.entities` and pygame

**Result**: Clean separation between data and presentation

### PHASE 5: Extract Input Handling (1 hour)
**Priority**: MEDIUM - Extensibility

1. Create `input/event_handler.py`
2. Move pygame event handling here
3. Return action dictionaries instead of direct logic
4. Update main game loop

**Result**: Input handling pluggable, mockable

---

## Coupling Severity Matrix

| Component | Severity | Issue | Fix Difficulty | Time |
|-----------|----------|-------|-----------------|------|
| agents.py (base) | CRITICAL | Extends pygame.sprite.Sprite | Easy | 2h |
| agents.py (Fish) | CRITICAL | Mixed logic + rendering | Moderate | 2h |
| agents.py (Crab/Plant/Food) | CRITICAL | Mixed logic + rendering | Easy | 1h each |
| fishtank.py | CRITICAL | Mixed simulation + rendering | Moderate | 2h |
| movement_strategy.py | MODERATE | Uses pygame.sprite.collide_rect | Easy | 30m |
| evolution_viz.py | MINOR | Pure visualization (ok to keep) | Easy | 1h |
| image_loader.py | MINOR | Simple wrapper (ok to keep) | Easy | 30m |
| behavior_algorithms.py | NONE | Pure (already isolated) | N/A | 0 |
| genetics.py | NONE | Pure (already isolated) | N/A | 0 |
| ecosystem.py | NONE | Pure (already isolated) | N/A | 0 |

---

## Code Statistics

| Metric | Value |
|--------|-------|
| Total Lines | 6,421 |
| Pure Simulation | ~3,925 (61%) |
| Pygame Coupled | ~2,000+ (31%) |
| Test Files | ~1,000+ (15%) |
| Files with pygame | 8 |
| Files without pygame | 7 |
| Critical bottlenecks | 2 (agents.py, fishtank.py) |

---

## Key Insights

### 1. Good News
- Pure simulation logic is already well-isolated (61% of codebase)
- Core algorithms (behavior_algorithms.py, genetics.py) are pure
- Ecosystem and environment modules are decoupled
- Clear separation potential

### 2. Bad News
- agents.py blocks all other refactoring (CRITICAL)
- Entity logic mixed with pygame rendering
- Game loop couples simulation to rendering
- Cannot test without pygame

### 3. Quick Wins
- Extract collision system from movement_strategy.py (30 mins, high value)
- Move evolution_viz logic to rendering/ (1 hour, high value)
- Reorganize pure logic into core/ package (1 hour, organizational benefit)

### 4. Biggest Payoff
- Separating agents.py (3-4 hours) enables:
  - All other refactoring
  - Pure simulation testing
  - Alternative renderers
  - Headless operation
  - Code reuse

---

## Next Steps

1. **Review this analysis** with team
2. **Prioritize Phase 1** (entity extraction) - it unblocks everything
3. **Create core/ package structure** with pure simulation
4. **Extract entities.py** - remove pygame.sprite.Sprite
5. **Update tests** to run without pygame
6. **Gradually refactor** remaining phases

---

## Files to Review

- `/home/user/tank/agents.py` - Focus on removing pygame.sprite.Sprite
- `/home/user/tank/fishtank.py` - Focus on separating update() from render()
- `/home/user/tank/movement_strategy.py` - Focus on collision detection injection

