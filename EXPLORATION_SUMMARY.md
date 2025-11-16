# Fish Tank Simulation - Complete Architecture Exploration

## QUICK REFERENCE

**Repository:** /home/user/tank
**Total Lines of Code:** ~4,752 lines across 19 files
**Main Language:** Python 3
**Key Framework:** pygame (for visualization/rendering)
**Main Entry Point:** `python fishtank.py` (fishtank.py::main())

---

## 1. ARCHITECTURE AT A GLANCE

### Three-Layer Architecture
```
PYGAME RENDERING (visualization)
    ↓
FISHTANK.PY (Game loop - COUPLED)
    ↓
CORE MODULES (Pure simulation logic)
```

**Status:** Partially decoupled - Pure logic layer exists but is wrapped in pygame-dependent classes

---

## 2. HOW IT WORKS: THE 30-SECOND VERSION

1. **User runs:** `python fishtank.py`
2. **Initialization:**
   - pygame initializes
   - FishTankSimulator creates agents (7 fish of 4 species + plants + crab)
   - Environment (spatial queries) and EcosystemManager (statistics) created
3. **Main Loop (30 FPS):**
   - **Update:** Each agent moves, consumes energy, ages. Collisions trigger (predation, eating, poker). Reproduction happens. Statistics tracked.
   - **Render:** Draw water, sprites, health bars, stats panel, day/night overlay
4. **Fish Lifecycle:**
   - Born → Juvenile → Adult → Elder → Death (from starvation, old age, or predation)
   - Each fish has a genome (inherited traits), a movement strategy, and optional neural AI or behavior algorithm
5. **Evolution:**
   - Fish reproduce when energy > threshold and age is adult
   - Offspring inherit and mutate parent genes
   - 48 different behavior algorithms can evolve

---

## 3. KEY FILES RANKED BY IMPORTANCE

### Tier 1: Core Simulation (Must understand these)
1. **fishtank.py** (559 lines) - Main game loop, entry point
2. **core/ecosystem.py** (632 lines) - Population & statistics tracking
3. **core/entities.py** (844 lines) - Pure entity logic (no pygame)
4. **agents.py** (603 lines) - Pygame sprite wrappers (pygame-dependent)

### Tier 2: Behavior & Genetics
5. **movement_strategy.py** (155 lines) - Movement AI strategies
6. **core/genetics.py** (201 lines) - Genetic system
7. **core/behavior_algorithms.py** (97 lines) - 48 algorithm registry
8. **core/neural_brain.py** (250 lines) - Neural network AI

### Tier 3: Supporting Systems
9. **core/environment.py** (79 lines) - Spatial queries
10. **core/time_system.py** (130 lines) - Day/night cycle
11. **rendering/sprites.py** (226 bytes) - Sprite adapters (new separation layer)
12. **evolution_viz.py** (275 lines) - Extra visualization
13. **core/constants.py** (111 lines) - Game configuration

### Tier 4: Algorithms (8 files in core/algorithms/)
- base.py - Base class & parameter bounds
- food_seeking.py - 12 algorithms
- predator_avoidance.py - 10 algorithms
- schooling.py - 10 algorithms
- energy_management.py - 8 algorithms
- territory.py - 8 algorithms
- poker.py - 5 algorithms

---

## 4. WHAT THE SIMULATION TRACKS

### Per-Fish Metrics
- ID, generation, age, energy level, life stage
- Genome (speed, size, vision, metabolism, fertility, color)
- Movement strategy type
- Behavior algorithm (if applicable)
- Position, velocity, size

### Per-Algorithm Metrics (48 algorithms tracked)
- Total births and deaths
- Deaths by cause (starvation, old age, predation)
- Current population
- Average lifespan
- Survival rate: alive / born
- Reproduction rate: babies / born
- Poker statistics: wins, losses, energy gained/lost

### Per-Generation Metrics
- Population count
- Births and deaths
- Average trait values (speed, size, energy)
- Average age at death

### Global Metrics
- Current simulation day/night time
- Total births and deaths
- Current generation
- Frame count (30 FPS)
- Death causes histogram
- Event log (last 1000 events)

**Access:** Press 'R' during simulation to generate algorithm_performance_report.txt

---

## 5. THE MAIN SIMULATION LOOP (fishtank.py::update)

Each frame (1/30 second):

1. **Update time system** (day/night cycle) → get_activity_modifier
2. **For each agent:**
   - **Fish:** movement_strategy.move() → energy consumption → aging → check death
   - **Plants:** grow and occasionally spawn food
   - **Others:** Crab, Food, Castle update normally
3. **Handle collisions:**
   - Fish + Crab = death (predation)
   - Fish + Food = eating
   - Fish + Fish = poker game (energy transfer)
4. **Handle reproduction:**
   - Find adult fish ready to reproduce (energy > threshold)
   - Mate nearby compatible fish
   - Genome.crossover() → mutation → newborn
5. **Update ecosystem stats:**
   - Record births, deaths, population per generation
   - Track algorithm performance
   - Update event log

**Rendering happens separately** in render() method (day/night tint, sprite animation, health bars, stats panel)

---

## 6. THE 4 FISH SPECIES

Each has a different movement strategy:

| Species | Count | Movement | AI Type | Evolution |
|---------|-------|----------|---------|-----------|
| Solo Fish | 1 | SoloFishMovement | Rule-based | None |
| Algorithmic | 2 | AlgorithmicMovement | 1 of 48 algorithms | Algorithm + params mutate |
| Neural | 2 | NeuralMovement | Neural network | Brain weights evolve |
| Schooling | 2 | SchoolingFishMovement | Rule-based flocking | None |

**All species have:**
- Energy system (consume, gain from food)
- Age-based life stages
- Reproduction with genetic inheritance
- Can be eaten by crab or starve to death
- Participate in poker games with each other

---

## 7. COUPLING ANALYSIS

### TIGHT COUPLING (Hard to test/decouple)
- **agents.py**: Extends pygame.sprite.Sprite
  - Can't instantiate Fish without pygame
  - Mixes entity logic with image rendering
  - Problem: Makes headless testing impossible

- **fishtank.py**: Game loop + rendering intertwined
  - update() and render() tightly coupled
  - Problem: Can't run pure simulation without display

### MODERATE COUPLING
- **movement_strategy.py**: Uses pygame.sprite.collide_rect()
  - Only collision detection dependency
  - Easy to replace with pure collision

### ALREADY DECOUPLED
- **core/entities.py**: Pure logic (NO pygame)
- **core/ecosystem.py**: Statistics only (NO pygame)
- **core/genetics.py**: Genetics only (NO pygame)
- **core/behavior_algorithms/*.py**: All 48 algorithms (NO pygame)
- **core/neural_brain.py**: Neural AI (NO pygame)
- **core/environment.py**: Spatial queries (NO pygame)
- **core/time_system.py**: Time simulation (NO pygame)

---

## 8. HOW SIMULATION & VISUALIZATION ARE COUPLED

### Coupling Point 1: agents.py
```python
class Fish(Agent(pygame.sprite.Sprite)):  # COUPLED!
    def __init__(self, ...):
        super().__init__()  # pygame.sprite.Sprite init
        self.animation_frames = [ImageLoader.load_image(f) for f in filenames]  # Images
        self.image = self.get_current_image()  # Visualization
        self.rect = self.image.get_rect()  # pygame Rect
        self._entity = core_entities.Fish(...)  # Pure logic wrapped inside
```

**Problem:** Can't use Fish without pygame. Rendering code mixed with logic.

### Coupling Point 2: fishtank.py
```python
while self.handle_events():
    self.update()      # Simulation step
    self.render()      # Drawing step
    self.clock.tick()  # Frame rate control (pygame)
```

**Problem:** Can't run update() without render(). UI drawing mixed in.

### Coupling Point 3: movement_strategy.py
```python
collisions = pygame.sprite.spritecollide(fish, self.agents, False, pygame.sprite.collide_mask)
```

**Problem:** Depends on pygame collision API. Easy to replace.

---

## 9. DECOUPLING PROGRESS & RECOMMENDATIONS

### What's Already Separated
- Pure entity logic in core/entities.py
- Statistics in core/ecosystem.py
- Genetics system
- All 48 algorithms
- Environment/spatial queries
- Time system

### What Still Needs Decoupling
1. **agents.py** - Create core/agents.py (pure), make agents.py an adapter
2. **fishtank.py** - Split into:
   - core/simulator.py (pure update loop)
   - fishtank.py (pygame event handler + rendering)
3. **movement_strategy.py** - Replace pygame.sprite.collide_rect() with pure collision

### Benefits of Full Decoupling
- Run simulation without display (headless testing)
- Swap rendering engines (console output, web, VR, etc.)
- Test logic without pygame overhead
- Reuse simulation in other projects

---

## 10. KEY STATISTICS EXPLAINED

### Survival Rate
`Formula: current_population / total_births`
Higher = algorithm keeps fish alive better

### Reproduction Rate
`Formula: total_reproductions / total_births`
Higher = algorithm's fish breed successfully

### Average Lifespan
`Formula: sum_of_all_ages / total_deaths`
Higher = algorithm's fish live longer

### Death Causes
- **Starvation**: energy <= 0
- **Old Age**: age >= max_age
- **Predation**: eaten by crab

---

## 11. HOW TO RUN & INTERACT

**Start simulation:**
```bash
cd /home/user/tank
python fishtank.py
```

**Controls:**
- SPACE: Drop food manually
- P: Pause/Resume
- H: Toggle HUD (health bars + stats)
- R: Generate algorithm performance report
- ESC: Quit

**Performance Report (press R):**
- Saves to: `algorithm_performance_report.txt`
- Contains: Each algorithm's survival, reproduction, lifespan, poker stats

---

## 12. COMPLETE FILE REFERENCE

```
ROOT DIRECTORY
├─ fishtank.py                    # MAIN ENTRY POINT (559 lines)
├─ agents.py                      # Pygame wrapper classes (603 lines) [COUPLED]
├─ movement_strategy.py           # Movement behaviors (155 lines) [COUPLED]
├─ evolution_viz.py               # Extra visualization (275 lines)
├─ image_loader.py                # Image loading (18 lines)
│
├─ core/
│  ├─ __init__.py                 # (0 lines)
│  ├─ constants.py                # Configuration (111 lines)
│  ├─ environment.py              # Spatial queries (79 lines)
│  ├─ entities.py                 # PURE entity logic (844 lines)
│  ├─ ecosystem.py                # Stats tracking (632 lines)
│  ├─ genetics.py                 # Genetic system (201 lines)
│  ├─ neural_brain.py             # Neural AI (250 lines)
│  ├─ time_system.py              # Day/night cycles (130 lines)
│  ├─ collision_system.py          # Collision detection (91 lines)
│  ├─ behavior_algorithms.py      # Algorithm registry (97 lines)
│  ├─ fish_poker.py               # Poker mechanics (277 lines)
│  ├─ poker_interaction.py        # Poker games (167 lines)
│  │
│  └─ algorithms/                 # 48 behavior algorithms
│     ├─ __init__.py
│     ├─ base.py                  # Base class
│     ├─ food_seeking.py          # 12 algorithms
│     ├─ predator_avoidance.py    # 10 algorithms
│     ├─ schooling.py             # 10 algorithms
│     ├─ energy_management.py     # 8 algorithms
│     ├─ territory.py             # 8 algorithms
│     └─ poker.py                 # 5 algorithms
│
├─ rendering/
│  ├─ __init__.py
│  └─ sprites.py                  # Sprite adapters (226 bytes)
│
├─ images/                        # Game graphics
├─ tests/                         # Unit tests
│
└─ DOCUMENTATION
   ├─ README.md
   ├─ ARCHITECTURE_ANALYSIS.md
   ├─ SEPARATION_GUIDE.md
   ├─ ALGORITHMIC_EVOLUTION.md
   └─ SEPARATION_README.md
```

---

## CONCLUSION

The simulation is **well-structured at its core** with pure logic properly separated, but **pygame rendering is tightly coupled** at the application layer (fishtank.py, agents.py). 

The system tracks comprehensive statistics about fish evolution, allowing researchers to analyze which behaviors (from 48 algorithms) survive and reproduce best under different environmental conditions. This is the key innovation: **algorithmic evolution** - algorithms themselves are genetic traits that can be inherited and mutated across generations.

Full decoupling is achievable in 2-3 refactoring phases without changing the core simulation logic.
