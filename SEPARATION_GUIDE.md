# Pygame/Simulation Separation - Quick Reference Guide

## TL;DR

**Current Problem**: Simulation logic is tightly coupled to pygame rendering, making it impossible to test or run without pygame.

**Root Cause**: `agents.py` extends `pygame.sprite.Sprite` and mixes entity logic with rendering.

**Solution**: Extract pure entity classes to `core/entities.py` (no pygame dependency).

---

## Critical Files to Fix (Priority Order)

### 1. **agents.py** (CRITICAL - Blocks Everything)
- **Issue**: Extends `pygame.sprite.Sprite`
- **Location**: Line 30 (`class Agent(pygame.sprite.Sprite)`)
- **Impact**: All entity logic requires pygame
- **Fix**: Extract to `core/entities.py`, remove Sprite inheritance
- **Time**: 3-4 hours
- **Payoff**: Unblocks all other refactoring

### 2. **fishtank.py** (CRITICAL - Mixed Logic)
- **Issue**: `update()` and `render()` in same class
- **Location**: Lines 160-464
- **Impact**: Cannot test simulation without rendering
- **Fix**: Extract to `game/simulation_engine.py` and `rendering/renderer.py`
- **Time**: 2-3 hours
- **Payoff**: Enables headless operation

### 3. **movement_strategy.py** (MODERATE - Collision Tied)
- **Issue**: `pygame.sprite.collide_rect()` hardcoded
- **Location**: Line 25
- **Impact**: Movement logic depends on pygame sprites
- **Fix**: Inject collision detection function
- **Time**: 30 minutes
- **Payoff**: Movement testable independently

---

## Current Coupling Points

```
ENTRY POINT: fishtank.py
    ↓
    Main game loop (pygame event loop)
    ↓
    ├─ update() - SIMULATION LOGIC
    │   └─ agents.update()
    │       └─ entities mixed with pygame rendering
    │
    └─ render() - RENDERING LOGIC
        └─ pygame.draw.*, blit, etc.

PROBLEM: update() and render() are tightly coupled
```

---

## Files That Are Already Pure (61% of Code)

These do NOT need changes:
- `behavior_algorithms.py` - Pure algorithms
- `genetics.py` - Pure genetics
- `neural_brain.py` - Pure neural network (only uses Vector2)
- `ecosystem.py` - Pure statistics
- `environment.py` - Pure spatial queries
- `time_system.py` - Pure time system
- `constants.py` - Configuration

**Action**: Move to `core/` package for organization

---

## Proposed Refactoring Steps

### STEP 1: Create Core Package Structure
```bash
mkdir -p /home/user/tank/core
mkdir -p /home/user/tank/rendering
mkdir -p /home/user/tank/input
mkdir -p /home/user/tank/game
```

### STEP 2: Move Pure Logic to Core
```bash
mv genetics.py core/
mv behavior_algorithms.py core/
mv neural_brain.py core/
mv ecosystem.py core/
mv environment.py core/
mv time_system.py core/
mv constants.py core/
```

### STEP 3: Extract Entities (CRITICAL)
Create `core/entities.py`:
1. Copy `Agent` class from `agents.py`
2. Change `class Agent(pygame.sprite.Sprite):` → `class Agent:`
3. Remove `self.image`, `self.rect`, animation frames
4. Remove image loading from `__init__`
5. Keep all pure logic: position, velocity, energy, reproduction

Copy `Fish`, `Crab`, `Plant`, `Food` classes similarly.

### STEP 4: Create Sprite Adapters
Create `rendering/sprites.py`:
1. `class FishSprite(pygame.sprite.Sprite):` wraps `core.entities.Fish`
2. Handle `self.image`, `self.rect`, animation
3. Convert entity data to pygame rendering

### STEP 5: Separate Game Logic
Create `game/simulation_engine.py`:
1. Extract `FishTankSimulator.update()` logic
2. Create `SimulationEngine.tick()` method
3. Remove pygame dependency

Create `rendering/renderer.py`:
1. Extract `render()`, `draw_health_bar()`, etc.
2. Create `GameRenderer.render(state)` method
3. Takes simulation state, returns nothing (just draws)

### STEP 6: Update Main Game Loop
Keep `fishtank.py` minimal:
```python
def main():
    pygame.init()
    engine = SimulationEngine()
    renderer = GameRenderer()
    controller = GameController(engine, renderer)
    controller.run()  # Game loop here

if __name__ == "__main__":
    main()
```

---

## Quick Test: Before/After

### BEFORE (Current - Cannot Do This)
```python
# This fails without pygame
from agents import Fish
fish = Fish(...)  # ImportError: pygame not installed
```

### AFTER (With Separation)
```python
# This works without pygame!
from core.entities import Fish
fish = Fish(...)  # Works fine, pure Python

# Pygame is only needed for rendering
from rendering.sprites import FishSprite
sprite = FishSprite(fish)  # Requires pygame for display
```

---

## Dependency Tree (Current)

```
fishtank.py
├─ agents.py (pygame + simulation)
│  ├─ image_loader.py (pygame)
│  ├─ genetics.py (pure)
│  └─ [embedded: Fish, Crab, Plant, Food]
├─ movement_strategy.py (pygame + simulation)
├─ evolution_viz.py (pygame rendering)
├─ behavior_algorithms.py (pure)
├─ ecosystem.py (pure)
└─ environment.py (pure)
```

## Dependency Tree (Proposed)

```
fishtank.py (thin wrapper)
├─ game/
│  └─ game_controller.py
│     ├─ core/simulation_engine.py (pure simulation)
│     │  ├─ core/entities.py (pure, no pygame)
│     │  ├─ core/genetics.py (pure)
│     │  ├─ core/behavior_algorithms.py (pure)
│     │  ├─ core/ecosystem.py (pure)
│     │  └─ core/environment.py (pure)
│     └─ rendering/renderer.py (pygame only)
│        └─ rendering/sprites.py (pygame.sprite.Sprite)
└─ input/
   └─ event_handler.py (pygame events)
```

---

## Code Snippets for Each Phase

### Phase 1: Extract Entity Classes

**Before (agents.py)**:
```python
class Agent(pygame.sprite.Sprite):
    def __init__(self, environment, filenames, x, y, speed):
        super().__init__()
        self.animation_frames = [ImageLoader.load_image(...)]
        self.image = self.get_current_image()
        self.rect = self.image.get_rect()
        self.pos = Vector2(x, y)
```

**After (core/entities.py)**:
```python
class Agent:
    def __init__(self, environment, x, y, speed):
        self.pos = Vector2(x, y)
        self.vel = Vector2(0, 0)
        self.environment = environment
        # NO image, rect, animation, ImageLoader
```

### Phase 2: Create Sprite Adapter

**New (rendering/sprites.py)**:
```python
class AgentSprite(pygame.sprite.Sprite):
    def __init__(self, entity, image_loader):
        super().__init__()
        self.entity = entity
        self.image_loader = image_loader
        self.image = self._get_image()
        self.rect = self.image.get_rect()
    
    def _get_image(self):
        # Get image based on entity.vel
        # Apply entity-based transformations
        return self.image_loader.load(...)
```

### Phase 3: Separate Simulation

**New (game/simulation_engine.py)**:
```python
class SimulationEngine:
    def __init__(self, config):
        self.agents = []
        self.ecosystem = EcosystemManager()
        self.environment = Environment(self.agents)
    
    def tick(self):
        # Pure simulation update, NO pygame
        for agent in self.agents:
            agent.update()
        self.handle_collisions()
        self.handle_reproduction()
```

**New (rendering/renderer.py)**:
```python
class GameRenderer:
    def __init__(self, screen, font):
        self.screen = screen
        self.font = font
        self.sprites = {}
    
    def render(self, state):
        # Takes SimulationEngine state
        # Only renders, no logic
        self.screen.fill((10, 30, 50))
        for agent in state.agents:
            sprite = self.sprites[agent]
            self.screen.blit(sprite.image, sprite.rect)
```

---

## Testing Strategy

### Before (Current - All tests need pygame)
```python
# conftest.py
import pytest
import pygame

@pytest.fixture
def fish():
    pygame.init()
    return Fish(environment, ...)  # Requires pygame
```

### After (Pure tests without pygame)
```python
# tests/test_entities.py
from core.entities import Fish

def test_fish_energy_consumption():
    fish = Fish(environment)  # NO pygame required!
    fish.consume_energy()
    assert fish.energy < max_energy

# tests/test_rendering.py
import pygame
from rendering.sprites import FishSprite

@pytest.fixture
def fish_sprite():
    pygame.init()
    return FishSprite(fish, image_loader)
```

---

## Impact Analysis

### What Gets Better
- Pure logic testable without pygame (61% of codebase)
- Headless operation possible
- Alternative renderers possible
- Parallel simulations possible
- Code more modular and maintainable

### What Doesn't Change
- Game behavior - same algorithms, same physics
- Visual output - same rendering
- Performance - similar (might improve with headless)

### Migration Risk
- LOW - Changes are additive, not destructive
- Tests can be run during refactoring
- Git history preserved for rollback

---

## Estimated Effort

| Phase | Task | Time | Difficulty | Payoff |
|-------|------|------|-----------|--------|
| 1 | Extract entities | 3-4h | Easy | CRITICAL |
| 2 | Extract collision system | 1h | Easy | High |
| 3 | Separate simulation/rendering | 2-3h | Moderate | High |
| 4 | Create sprite adapters | 1-2h | Easy | Medium |
| 5 | Extract input handling | 1h | Easy | Medium |
| 6 | Package restructuring | 1h | Trivial | Low |
| **Total** | **Full Separation** | **8-12h** | **Moderate** | **HUGE** |

---

## Success Criteria

After refactoring, you should be able to:

1. ✓ Run tests without pygame installed
2. ✓ Run simulation headless (no rendering)
3. ✓ Use simulation engine in another project
4. ✓ Swap rendering backends
5. ✓ Run multiple simulations in parallel
6. ✓ Test entity logic in isolation
7. ✓ Test rendering independently

---

## Resources

- See `ARCHITECTURE_ANALYSIS.md` for detailed analysis
- See existing test files for testing patterns
- Review `behavior_algorithms.py` as example of pure code

