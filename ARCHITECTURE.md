# Tank Simulation - Architecture Documentation

## Executive Summary

Tank is an advanced artificial life (ALife) ecosystem simulation featuring 48 parametrizable behavior algorithms, neural network brains, genetics, evolution, and emergent population dynamics.

**Tech Stack:**
- **Backend**: Python with FastAPI + WebSocket
- **Frontend**: React 19 + TypeScript + Vite
- **Simulation**: Pure Python core with optional Pygame visualization

**Code Statistics:**
- ~6,400 lines of Python simulation logic
- 61% pure simulation code (no pygame dependencies)
- 48 behavior algorithms across 8 files
- Dual execution modes: graphical (pygame) and headless

## Project Structure

```
tank/
├── core/                          # Pure Python simulation (NO pygame)
│   ├── entities.py               # Fish, Plant, Crab, Food entities
│   ├── ecosystem.py              # Population tracking & statistics
│   ├── genetics.py               # Genome, mutation, crossover
│   ├── neural_brain.py           # Neural network AI
│   ├── behavior_algorithms.py   # Algorithm registry
│   ├── algorithms/               # 48 behavior implementations
│   │   ├── base.py
│   │   ├── food_seeking.py
│   │   ├── predator_avoidance.py
│   │   ├── schooling.py
│   │   ├── energy_management.py
│   │   └── territory.py
│   ├── environment.py            # Spatial queries
│   ├── time_system.py            # Day/night cycles
│   └── constants.py              # Configuration
│
├── backend/                       # FastAPI WebSocket server
│   ├── main.py                   # FastAPI app
│   ├── simulation_runner.py     # Background simulation thread
│   └── models.py                 # Data models
│
├── frontend/                      # React + TypeScript UI
│   ├── src/
│   │   ├── components/           # Canvas, StatsPanel, ControlPanel
│   │   ├── hooks/                # useWebSocket.ts
│   │   ├── types/                # TypeScript definitions
│   │   └── utils/                # renderer.ts
│   └── package.json
│
├── rendering/                     # Pygame sprite adapters
│   └── sprites.py                # Wrapper sprites for entities
│
├── agents.py                      # Legacy pygame wrapper (backward compat)
├── movement_strategy.py          # Movement behavior strategies
├── fishtank.py                   # Pygame graphical mode entry point
├── simulation_engine.py          # Headless simulation runner
└── main.py                        # Main entry point
```

## Architecture Layers

### 1. Pure Simulation Core (core/)

**Design Goal:** Zero pygame dependencies, fully testable

- **entities.py** (867 LOC): Fish, Plant, Crab, Food, Castle classes
  - Life cycle management
  - Energy consumption
  - Reproduction logic
  - Age progression

- **genetics.py** (201 LOC): Genetic system
  - Genome with 7 traits (speed, size, vision, metabolism, fertility, color, lifespan)
  - Mutation with configurable rates
  - Sexual reproduction via crossover
  - Brain/algorithm inheritance

- **behavior_algorithms.py** + **algorithms/*** (3,400+ LOC):
  - 48 parametrizable behavior algorithms
  - Categories: Food Seeking (12), Predator Avoidance (10), Schooling (10), Energy Management (8), Territory (8)
  - Each algorithm has tunable parameters that can mutate
  - Performance tracking per algorithm

- **neural_brain.py** (250 LOC): Simple 2-layer neural network

- **ecosystem.py** (678 LOC): Population tracking
  - Per-algorithm statistics
  - Generation statistics
  - Death cause tracking
  - Poker interaction stats
  - Event logging

### 2. Rendering Layer (rendering/)

**Design Goal:** Adapt pure entities to pygame sprites

- **sprites.py**: AgentSprite, FishSprite, CrabSprite, PlantSprite, FoodSprite
  - Wraps core entities
  - Handles animation frames
  - Applies genetic visual traits (color tinting, scaling)
  - Syncs entity state to visual representation

### 3. Web Backend (backend/)

**Design Goal:** Real-time web UI via WebSocket

- **main.py**: FastAPI application with WebSocket endpoint
- **simulation_runner.py**: Background thread running headless simulation
- **models.py**: Pydantic models for state serialization

### 4. Web Frontend (frontend/)

**Design Goal:** Modern React-based visualization

- Real-time canvas rendering
- Stats panel with population metrics
- Control panel for simulation parameters
- WebSocket communication with backend

## Execution Modes

### Graphical Mode (Pygame)

Entry: `fishtank.py`

```
pygame.init()
  ↓
FishTankSimulator
  ├─ setup_game()
  │   ├─ Create environment
  │   ├─ Create initial agents (fish, plants, crab)
  │   └─ Initialize pygame display
  │
  └─ run() - Main game loop
      ├─ handle_events() - User input (SPACE: spawn food, P: pause, H: toggle HUD)
      ├─ update() - Simulation tick
      │   ├─ Update time system (day/night)
      │   ├─ Update all agents
      │   ├─ Handle collisions
      │   ├─ Handle reproduction
      │   └─ Update ecosystem stats
      │
      ├─ render() - Draw to screen
      │   ├─ Fill background
      │   ├─ Apply day/night tint
      │   ├─ Draw all sprites
      │   ├─ Draw health bars (if HUD enabled)
      │   └─ Draw stats panel
      │
      └─ clock.tick(30) - Cap at 30 FPS
```

### Headless Mode

Entry: `simulation_engine.py`

- No rendering overhead
- Runs simulation-only logic
- Used by web backend
- Ideal for batch experiments

### Web Mode

Entry: `backend/main.py` + `frontend/`

- Backend runs headless simulation
- State serialized to JSON via WebSocket
- Frontend renders on HTML canvas
- Modern React UI with controls

## Key Algorithms

### 48 Behavior Algorithms

**Food Seeking (12 algorithms):**
1. GreedyFoodSeeker - Always move toward nearest food
2. EnergyAwareFoodSeeker - Seek food only when energy is low
3. OpportunisticFeeder - Balance exploration and exploitation
4. FoodQualityOptimizer - Prefer high-value food
5. AmbushFeeder - Wait for food to come close
6. PatrolFeeder - Follow patrol routes
7. SurfaceSkimmer - Stay near surface
8. BottomFeeder - Stay near bottom
9. ZigZagForager - Search in zigzag pattern
10. CircularHunter - Circle while searching
11. FoodMemorySeeker - Remember food locations
12. CooperativeForager - Share food information

**Predator Avoidance (10 algorithms):**
13-22. Various escape strategies (panic, stealth, freeze, spiral, etc.)

**Schooling/Social (10 algorithms):**
23-32. Flocking behaviors (alignment, cohesion, separation, etc.)

**Energy Management (8 algorithms):**
33-40. Energy conservation strategies (burst swimming, resting, balancing, etc.)

**Territory/Exploration (8 algorithms):**
41-48. Movement patterns (territorial, random, wall following, etc.)

### Movement Strategies

- **NeuralMovement**: Neural network controls velocity
- **AlgorithmicMovement**: Behavior algorithm controls velocity
- **SoloFishMovement**: Hand-coded rule-based AI
- **SchoolingFishMovement**: Boids-like flocking

## Statistics Tracked

### Per Fish
- ID, generation, age
- Energy (current/max)
- Life stage (Baby/Juvenile/Adult/Elder)
- Genome (all 7 traits + brain/algorithm)
- Position, velocity
- Size (affected by nutrition)

### Per Algorithm
- Total births/deaths
- Deaths by cause (starvation, old age, predation)
- Current population
- Average lifespan
- Survival rate
- Reproduction rate
- Food consumption
- Poker statistics

### Per Generation
- Population count
- Birth/death count
- Average age at death
- Average genetic traits

### Global
- Current time (day/night cycle)
- Total births/deaths
- Current generation
- Death causes histogram
- Event log (last 1000 events)

## Separation of Concerns Status

### ✓ Already Separated
- Pure entity logic in `core/entities.py`
- Pure genetics in `core/genetics.py`
- Pure ecosystem tracking in `core/ecosystem.py`
- All 48 algorithms are pure Python
- Neural brain is mostly pure
- Time system is pure
- Sprite adapters in `rendering/sprites.py`

### ⚠ Remaining Coupling
- **agents.py**: Backward compatibility wrapper (wraps core entities with pygame sprites)
- **movement_strategy.py**: Uses `pygame.sprite.collide_rect()`
- **fishtank.py**: Game loop mixes simulation and rendering

### Future Improvements
1. Complete migration away from `agents.py` wrapper
2. Abstract collision detection (remove pygame dependency from movement)
3. Further separate game loop from rendering logic
4. Add more comprehensive tests for pure simulation

## References

- Main README: See `README.md`
- Deployment: See `DEPLOYMENT_GUIDE.md`
- Algorithmic Evolution: See `ALGORITHMIC_EVOLUTION.md`
- Headless Mode: See `HEADLESS_MODE.md`
- Separation Guide: See `SEPARATION_GUIDE.md`
