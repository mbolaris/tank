# Tank Simulation - Architecture Documentation

## Executive Summary

Tank is an advanced artificial life (ALife) ecosystem simulation featuring parametrizable behavior algorithms, genetics, evolution, and emergent population dynamics.

**Tech Stack:**
- **Backend**: Python with FastAPI + WebSocket
- **Frontend**: React 19 + TypeScript + Vite
- **Simulation**: Pure Python core with no UI dependencies

**Code Statistics:**
- ~6,400 lines of Python simulation logic
- 100% pure simulation code (no visualization dependencies in core)
- 12+ behavior algorithms across multiple files
- Dual execution modes: web UI and headless

## Project Structure

```
tank/
├── core/                          # Pure Python simulation (no UI dependencies)
│   ├── entities/                 # Entity classes (Fish, Plant, Food, etc.)
│   ├── systems/                  # Simulation systems (BaseSystem pattern)
│   │   ├── base.py              # BaseSystem abstract class and Protocol
│   │   └── ...                  # Future system implementations
│   ├── ecosystem.py              # Population tracking & statistics
│   ├── genetics/                 # Genome, mutation, crossover
│   ├── behavior_algorithms.py   # Algorithm registry
│   ├── algorithms/               # 12+ behavior implementations
│   │   ├── base.py
│   │   ├── food_seeking.py
│   │   ├── predator_avoidance.py
│   │   ├── schooling.py
│   │   ├── energy_management.py
│   │   └── territory.py
│   ├── world.py                  # World and World2D Protocols
│   ├── interfaces.py             # SkillfulAgent and other Protocols
│   ├── environment.py            # Spatial queries (implements World Protocol)
│   ├── skills/                   # Skill game framework
│   │   ├── base.py              # SkillGame, SkillStrategy abstractions
│   │   ├── config.py            # Game configuration and registry
│   │   └── games/               # Game implementations
│   │       ├── rock_paper_scissors.py
│   │       ├── number_guessing.py
│   │       └── poker_adapter.py # Poker as SkillGame
│   ├── time_system.py            # Day/night cycles (extends BaseSystem)
│   ├── collision_system.py       # Collision detection (extends BaseSystem)
│   ├── reproduction_system.py    # Reproduction logic (extends BaseSystem)
│   ├── poker_system.py           # Poker events (extends BaseSystem)
│   ├── events.py                 # Event bus for decoupled communication
│   ├── simulators/               # Base simulator classes
│   │   └── base_simulator.py    # BaseSimulator abstract class
│   ├── simulation_engine.py      # Main engine with System Registry
│   └── constants.py              # Configuration
│
├── backend/                       # FastAPI WebSocket server
│   ├── main.py                   # FastAPI app with Tank World Net API
│   ├── tank_registry.py         # Multi-tank management (Tank World Net)
│   ├── simulation_manager.py    # Per-tank lifecycle management
│   ├── simulation_runner.py     # Background simulation thread
│   ├── state_payloads.py        # Serialization DTOs
│   └── models.py                 # Data models
│
├── frontend/                      # React + TypeScript UI
│   ├── src/
│   │   ├── components/           # TankView, Canvas, ControlPanel, etc.
│   │   ├── pages/                # NetworkDashboard
│   │   ├── hooks/                # useWebSocket.ts
│   │   ├── types/                # TypeScript definitions
│   │   ├── utils/                # renderer.ts, fractalPlant.ts
│   │   ├── App.tsx               # Router setup
│   │   └── config.ts             # Server configuration
│   └── package.json
│
├── simulation_engine.py          # Headless simulation runner
└── main.py                        # Main entry point
```

## Architecture Layers

### 1. Pure Simulation Core (core/)

**Design Goal:** Zero UI dependencies, fully testable

- **entities.py**: Fish, Plant, Food classes
  - Life cycle management
  - Energy consumption
  - Reproduction logic
  - Age progression

- **genetics.py**: Genetic system
  - Genome with traits (speed, size, vision, metabolism, color, lifespan)
  - Mutation with configurable rates
  - Sexual reproduction via crossover
  - Algorithm inheritance

- **behavior_algorithms.py** + **algorithms/**:
  - 12+ parametrizable behavior algorithms
  - Categories: Food Seeking, Predator Avoidance, Schooling, Energy Management, Territory
  - Each algorithm has tunable parameters that can mutate
  - Performance tracking per algorithm

- **ecosystem.py**: Population tracking
  - Per-algorithm statistics
  - Generation statistics
  - Death cause tracking
  - Poker interaction stats
  - Event logging

- **environment.py**: Spatial queries
  - Spatial grid for efficient proximity queries
  - Neighbor finding
  - Food/mate detection

- **collision_system.py**: Collision detection
  - Bounding box (AABB) collision detection
  - Pure Python implementation
  - Deterministic results

### 2. Web Backend (backend/)

**Design Goal:** Real-time web UI via WebSocket with Tank World Net support

- **main.py**: FastAPI application with WebSocket and REST endpoints
- **tank_registry.py**: TankRegistry class for multi-tank management
- **simulation_manager.py**: SimulationManager for per-tank lifecycle
- **simulation_runner.py**: Background thread running headless simulation
- **state_payloads.py**: Optimized DTOs for state serialization
- **models.py**: Pydantic models for API validation

**Tank World Net API:**
- `GET /api/tanks` - List all tanks with stats (fish count, generation, energy)
- `POST /api/tanks` - Create new tank
- `DELETE /api/tanks/{id}` - Remove tank
- `POST /api/tanks/{id}/pause` - Pause a running tank
- `POST /api/tanks/{id}/resume` - Resume a paused tank
- `POST /api/tanks/{id}/start` - Start a stopped tank
- `POST /api/tanks/{id}/stop` - Stop a running tank
- `WS /ws/{tank_id}` - Connect to specific tank for live updates

### 3. Web Frontend (frontend/)

**Design Goal:** Modern React-based visualization with multi-tank support

- **React Router** for multi-page navigation
- **TankView** component for reusable tank visualization
- **NetworkDashboard** for Tank World Net management with:
  - Live tank thumbnails with WebSocket streaming
  - Per-tank controls (pause/resume/start/stop)
  - Real-time stats (fish count, generation, energy)
  - Tank creation and deletion
  - Connection status monitoring
- Real-time canvas rendering
- Stats panel with population metrics
- Control panel for simulation parameters
- WebSocket communication with backend

**Routes:**
- `/` - Default tank view
- `/tank/:tankId` - Specific tank view
- `/network` - Tank World Net dashboard

## Execution Modes

### Web Mode (Default)

Entry: `main.py` (default mode)

```bash
python main.py
```

```
Backend (FastAPI)
  ↓
SimulationEngine
  ├─ setup()
  │   ├─ Create environment
  │   ├─ Create initial population
  │   └─ Initialize ecosystem manager
  │
  └─ update() - Simulation tick (called continuously)
      ├─ Update time system (day/night)
      ├─ Update all entities
      ├─ Handle collisions
      ├─ Handle reproduction
      ├─ Update ecosystem stats
      └─ Send state via WebSocket
            ↓
React Frontend (Canvas)
  ├─ Render fish, plants, food
  ├─ Display stats panel
  └─ Handle user interactions
```

### Headless Mode

Entry: `main.py --headless`

```bash
python main.py --headless --max-frames 10000
```

- No rendering overhead
- Runs simulation-only logic
- Stats printed to console
- 10-300x faster than realtime
- Ideal for batch experiments and testing

## Key Algorithms

### Behavior Algorithms

**Food Seeking:**
1. GreedyFoodSeeker - Always move toward nearest food
2. EnergyAwareFoodSeeker - Seek food only when energy is low
3. OpportunisticFeeder - Balance exploration and exploitation
4. And more...

**Predator Avoidance:**
- PanicEscape - Flee from threats
- StealthAvoidance - Subtle evasion
- FreezeResponse - Stop when threatened
- And more...

**Schooling/Social:**
- Boid-based flocking behaviors
- Alignment, cohesion, separation
- Leader following
- And more...

**Energy Management:**
- Burst swimming
- Resting strategies
- Energy balancing
- And more...

**Territory/Exploration:**
- Territorial behavior
- Random wandering
- Wall following
- And more...

### Movement Strategies

- **AlgorithmicMovement**: Behavior algorithm controls velocity
- **ConstantVelocityMovement**: Simple linear movement
- **StaticMovement**: No movement (plants)

## Statistics Tracked

### Per Fish
- ID, generation, age
- Energy (current/max)
- Genome (all 7 traits + algorithm)
- Position, velocity
- Size (affected by nutrition)

### Per Algorithm
- Total births/deaths
- Deaths by cause (starvation, old age)
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
- Event log (recent events)

## Design Patterns

### System Registry Pattern
The simulation uses a **System Registry** for consistent management of all simulation subsystems:

```
SimulationEngine
    │
    ├─ _systems: List[BaseSystem]  (registered in execution order)
    │   ├─ EntityLifecycleSystem - Birth/death tracking, emergency spawns
    │   ├─ TimeSystem            - Day/night cycle management
    │   ├─ CollisionSystem       - Collision detection and handling
    │   ├─ ReproductionSystem    - Asexual reproduction logic
    │   └─ PokerSystem           - Poker game events and history
    │
    ├─ get_systems()           - List all registered systems
    ├─ get_system(name)        - Get system by name
    ├─ get_systems_debug_info() - Debug info from all systems
    └─ set_system_enabled()    - Enable/disable systems at runtime
```

**Benefits:**
- **Uniform Interface**: All systems extend `BaseSystem` with consistent `update(frame)`, `get_debug_info()`, and `enabled` property
- **Easy Extension**: Add new systems by creating a class extending `BaseSystem` and registering it
- **Runtime Control**: Enable/disable systems without code changes
- **Debugging**: Unified debug info collection across all systems

### BaseSystem Abstract Class
All simulation systems inherit from `BaseSystem` (`core/systems/base.py`):

```python
class BaseSystem(ABC):
    """Abstract base class for all simulation systems."""

    @property
    def name(self) -> str: ...        # Human-readable name
    @property
    def enabled(self) -> bool: ...    # Runtime enable/disable
    def update(self, frame: int): ... # Per-frame logic
    def get_debug_info(self) -> Dict: # Debug statistics
    def _do_update(self, frame: int): # Subclass implementation
```

### Template Method Pattern
`BaseSimulator` defines the simulation algorithm skeleton:
- `handle_collisions()`: Collision detection and response
- `handle_reproduction()`: Mating and offspring creation
- `spawn_auto_food()`: Automatic food generation
- Subclasses implement specific methods like `check_collision()`

### Strategy Pattern
Different movement strategies for entities:
- `AlgorithmicMovement`: Uses genetic algorithm for behavior
- `ConstantVelocityMovement`: Simple linear movement
- `StaticMovement`: No movement (plants)

### Component-Based Architecture
Fish behavior is modular:
- Energy system (EnergyComponent)
- Reproduction system (ReproductionComponent)
- Lifecycle system (LifecycleComponent)
- Movement system

## Separation of Concerns

### ✓ Fully Separated
- Pure entity logic in `core/entities.py`
- Pure genetics in `core/genetics/`
- Pure ecosystem tracking in `core/ecosystem.py`
- All algorithms are pure Python
- Time system is pure
- Collision system is pure
- Environment system is pure
- Simulation core has zero UI dependencies

### Architecture Benefits
1. **Testability**: Pure Python simulation can be tested independently
2. **Performance**: Headless mode runs much faster
3. **Flexibility**: Can add new visualization layers easily
4. **Maintainability**: Clear separation of concerns

## Key Features

### Genetic Evolution
- Fish inherit traits from parents with mutation
- 12+ behavior algorithms compete for survival
- Natural selection based on survival and reproduction
- Genetic diversity tracking

### Energy System
- Fish consume energy over time
- Gain energy from eating food
- Poker games transfer energy between fish
- Death when energy reaches zero

### Reproduction System
- Fish must find compatible mates
- Cooldown periods prevent overpopulation
- Offspring inherit mixed parental traits
- Population cap management

### Skill Game System
- **Multiple game types**: Poker, Rock-Paper-Scissors, Number Guessing
- Fish play games when they encounter each other
- Winners gain energy from losers
- Strategies evolve through genetic algorithm

**Poker Integration:**
- `PokerSkillGame` adapter unifies poker with skill game framework
- Uses existing poker engine and strategy system
- Conforms to `SkillGame` interface like other games
- Fish use `SkillfulAgent` Protocol for uniform game interaction

### Protocol-Based Architecture
The simulation uses **Protocols** (PEP 544) for defining interfaces:

**World Protocol** (`core/world.py`):
- Defines what any simulation environment must provide
- `nearby_agents()`, `nearby_agents_by_type()` for spatial queries
- `get_bounds()`, `is_valid_position()` for boundary checking
- `dimensions` property for environment size
- Implemented by `Environment` class

**SkillfulAgent Protocol** (`core/interfaces.py`):
- Defines contract for agents that can play skill games
- `get_strategy(game_type)` - Get agent's strategy for a game
- `set_strategy(game_type, strategy)` - Set strategy
- `learn_from_game(game_type, result)` - Update from game outcomes
- `can_play_skill_games` - Check if agent is ready to play
- Implemented by `Fish` class

**Benefits:**
- **Structural subtyping**: Classes satisfy protocols without explicit inheritance
- **Runtime checking**: `isinstance(obj, Protocol)` works with `@runtime_checkable`
- **Future-proof**: Easy to add new environment types or agent types
- **Type safety**: IDE autocomplete and type checkers understand the contracts

## References

- Main README: See `../README.md`
- Deployment: See `DEPLOYMENT_GUIDE.md`
- Algorithmic Evolution: See `ALGORITHMIC_EVOLUTION.md`
- Headless Mode: See `HEADLESS_MODE.md`
- Cleanup Analysis: See `CLEANUP_ANALYSIS.md` (historical)
