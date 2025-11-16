# Fish Tank Simulation - Complete Architecture Overview

## 1. OVERALL STRUCTURE

The codebase is organized into 3 main layers:

```
ENTRY POINT
└─ fishtank.py (559 lines)
   ├─ FishTankSimulator class
   │  ├─ setup_game() - Initialize pygame, create environment
   │  ├─ create_initial_agents() - Spawn fish with different AI types
   │  ├─ update() - Main simulation loop (LOGIC)
   │  ├─ render() - Drawing to screen (VISUALIZATION)
   │  ├─ handle_events() - User input
   │  └─ handle_collisions(), handle_reproduction()
   │
   └─ main() - pygame.init() → FishTankSimulator.run()
```

## 2. SIMULATION vs VISUALIZATION COUPLING

### Current Coupling Architecture:
```
SIMULATION LOGIC (Mixed into pygame structure):
├─ agents.py (603 lines) - CRITICAL COUPLING POINT
│  ├─ Wraps core/entities.py classes (pure logic)
│  ├─ Extends pygame.sprite.Sprite
│  ├─ Handles animation & image rendering
│  └─ Classes: Fish, Plant, Crab, Food, Castle
│
├─ movement_strategy.py (155 lines) - MODERATE COUPLING
│  ├─ NeuralMovement - Neural network-based control
│  ├─ AlgorithmicMovement - Behavior algorithm control
│  ├─ SoloFishMovement - Rule-based AI
│  └─ SchoolingFishMovement - Flocking behavior
│  └─ Uses pygame.sprite.collide_mask()
│
└─ PURE LOGIC LAYER (Already decoupled):
   ├─ core/entities.py (844 lines) - Pure entity logic
   │  └─ Fish, Plant, Crab, Food, Castle (no pygame)
   ├─ core/ecosystem.py (632 lines) - Population tracking
   ├─ core/genetics.py (201 lines) - Genetics & mutation
   ├─ core/neural_brain.py (250 lines) - Neural AI
   ├─ core/behavior_algorithms.py (97 lines) - Algorithm registry
   ├─ core/algorithms/*.py (8 files) - 48 behavior algorithms
   ├─ core/environment.py (79 lines) - Spatial queries
   ├─ core/time_system.py (130 lines) - Day/night cycles
   └─ core/constants.py (111 lines) - Configuration

VISUALIZATION (Already somewhat separated):
└─ rendering/sprites.py (8076 bytes) - NEW sprite adapters
   ├─ AgentSprite - Wrapper for Agent entities
   ├─ FishSprite - Fish with genetic coloring & scaling
   ├─ CrabSprite, PlantSprite, FoodSprite, CastleSprite
   └─ Syncs entity state to pygame visuals
```

## 3. SIMULATION LOOP (fishtank.py::FishTankSimulator)

### Main Update Cycle (fishtank.py lines 160-254):
```
update():
├─ Update time_system (day/night cycle)
├─ For each agent:
│  ├─ Fish.update()
│  │  ├─ Apply movement strategy
│  │  ├─ Consume energy
│  │  ├─ Age and reproduction logic
│  │  └─ Return potential newborn
│  │
│  ├─ Plant.update() - Grow and produce food
│  └─ Other agents (Crab, Food, Castle)
│
├─ Handle collisions (fish-food, fish-crab, fish-fish)
├─ Handle reproduction (mate finding)
├─ Track new births/deaths
└─ Update ecosystem statistics

render():
├─ Fill background with water color
├─ Apply day/night tint overlay
├─ Draw all sprites (agents.draw())
├─ Draw health bars (if HUD enabled)
├─ Draw stats panel
└─ pygame.display.flip()
```

### Entry Points:
- **main()** (line 549): pygame.init() → FishTankSimulator() → game.run()
- **run()** (line 504): Infinite loop calling update() → render() → clock.tick()

### Game Loop Controls:
- SPACE: Drop food manually
- P: Pause/Resume
- H: Toggle HUD (health bars, stats)
- R: Generate algorithm performance report
- ESC: Quit

## 4. AGENT CREATION & SPECIES

Initial population (fishtank.py::create_initial_agents):
```
Species 1: Solo Fish (1 fish)
├─ Movement: SoloFishMovement (rule-based)
├─ Image: george1.png, george2.png
└─ No genome or neural brain

Species 2: Algorithmic Fish (2 fish) ← NEW ALGORITHMIC EVOLUTION
├─ Movement: AlgorithmicMovement
├─ Genome: use_brain=False, use_algorithm=True
├─ 48 different behavior algorithms available
└─ Parameters can mutate across generations

Species 3: Neural Fish (2 fish)
├─ Movement: NeuralMovement
├─ Genome: use_brain=True, use_algorithm=False
└─ Neural network AI that can learn

Species 4: Schooling Fish (2 fish)
├─ Movement: SchoolingFishMovement (flocking)
├─ Genome: use_brain=False, use_algorithm=False
├─ Pure rule-based flocking behavior
└─ Simple AI (avoid crabs, seek food)

Static Agents:
├─ Plants (3) - Produce food over time
├─ Castle (1) - Decoration/environmental
├─ Crab (1) - Predator
└─ Food (spawned) - Auto-spawn every 45 frames
```

## 5. STATISTICS & METRICS TRACKED

### Ecosystem Manager (core/ecosystem.py)
Tracks per-algorithm statistics:
```
AlgorithmStats:
├─ total_births & total_deaths
├─ deaths_by_cause (starvation, old_age, predation)
├─ current_population
├─ average_lifespan
├─ survival_rate
└─ reproduction_rate

GenerationStats:
├─ Population per generation
├─ Births/deaths per generation
├─ Average age at death
├─ Average traits (speed, size, energy)

PokerStats (fish-fish interactions):
├─ Total games played
├─ Win/loss rates
├─ Energy gained/lost
└─ Best/average hand ranks

EventLog:
└─ Last 1000 events (births, deaths, deaths-by-cause)
```

### Display Stats (fishtank.py::draw_stats_panel):
- Time of day
- Current population / max capacity
- Current generation
- Total births & deaths
- Death causes breakdown

### Algorithm Performance Report:
Accessible via 'R' key - comprehensive analysis of each algorithm's:
- Survival rates
- Reproduction success
- Lifespan averages
- Energy efficiency
- Poker interaction stats

## 6. KEY FILES & THEIR ROLES

| File | Lines | Role |
|------|-------|------|
| fishtank.py | 559 | Main simulator + game loop |
| agents.py | 603 | Agent wrapper classes (pygame sprites) |
| core/entities.py | 844 | Pure entity logic (NO pygame) |
| core/ecosystem.py | 632 | Population tracking & statistics |
| core/genetics.py | 201 | Genetic system & inheritance |
| movement_strategy.py | 155 | Movement behavior strategies |
| core/behavior_algorithms.py | 97 | Algorithm registry (backwards compat) |
| core/algorithms/ | ~8 files | 48 behavior algorithms |
| core/neural_brain.py | 250 | Neural network AI |
| evolution_viz.py | 275 | Extra visualization |
| rendering/sprites.py | 226 | Sprite adapters (NEW separation) |
| core/environment.py | 79 | Spatial query interface |
| core/time_system.py | 130 | Day/night cycle system |

## 7. HOW SIMULATION & VISUALIZATION ARE COUPLED

### Direct Coupling in agents.py:
1. **Inheritance**: `class Fish(Agent(pygame.sprite.Sprite))`
   - Agents ARE pygame sprites, not just wrapped by them
   - Can't instantiate Fish without pygame

2. **Image Handling**:
   - Animation frames loaded in __init__
   - get_current_image() applies color tints
   - image_index updated during update()

3. **Animation Data**:
   - animation_frames: List[Surface]
   - image_index tracks current frame
   - Update rate tied to elapsed_time (pygame clock)

### Coupling in movement_strategy.py:
1. `pygame.sprite.collide_rect()` for collision detection
2. Directly manipulates sprite.vel (which is pygame Vector2)

### Coupling in fishtank.py:
1. **Game Loop** mixes update() and render():
   ```python
   while self.handle_events():
       self.update()      # Simulation step
       self.render()      # Drawing step
       self.clock.tick()  # Frame rate control
   ```
2. **Rendering deeply embedded**:
   - draw_health_bar() - draws per-fish UI
   - draw_stats_panel() - draws ecosystem info
   - Tint overlay for day/night cycle
   - Health color based on energy level

## 8. DECOUPLING PROGRESS

### Already Separated:
✓ core/entities.py - Pure entity logic (NO pygame dependencies)
✓ core/ecosystem.py - Population tracking (NO pygame)
✓ core/genetics.py - Genetic system (NO pygame)
✓ core/behavior_algorithms/*.py - All 48 algorithms (NO pygame)
✓ core/neural_brain.py - Neural AI (minimal pygame)
✓ core/environment.py - Spatial queries (NO pygame)
✓ core/time_system.py - Time simulation (NO pygame)
✓ rendering/sprites.py - NEW sprite adapters (separation layer)

### Still Coupled:
✗ agents.py - Extends pygame.Sprite, handles animation
✗ movement_strategy.py - Uses pygame.sprite.collide_rect()
✗ fishtank.py - Game loop + rendering mixed

### Coupling Points Summary:
1. **agents.py** (CRITICAL): Extends pygame.sprite.Sprite
   - Prevents pure Python testing
   - Makes code harder to refactor

2. **fishtank.py** (HEAVY): Game loop + rendering in one class
   - Update and render tightly intertwined
   - UI drawing mixed with simulation

3. **movement_strategy.py** (MODERATE): pygame collision API
   - Only collision detection import
   - Easy to replace

## 9. ARCHITECTURE RECOMMENDATIONS

### For Decoupling Simulation from Visualization:

**Phase 1 (DONE)**: Create pure logic layer
- ✓ core/entities.py exists (pure)
- ✓ rendering/sprites.py exists (adapters)

**Phase 2 (PARTIAL)**: Separate agents.py
- Create core/agents.py (pure, no pygame)
- agents.py becomes adapter wrapper only
- Update fishtank.py to use core.agents

**Phase 3**: Separate game loop
- Create core/simulator.py (pure simulation)
- fishtank.py becomes pygame event handler only
- Allow headless simulation testing

**Phase 4**: Decouple movement strategies
- Replace pygame.sprite.collide_rect()
- Use pure collision detection

