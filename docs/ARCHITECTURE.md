# Tank Simulation - Architecture Documentation

## Executive Summary

Tank is an advanced artificial life (ALife) ecosystem simulation featuring parametrizable behavior algorithms, genetics, evolution, and emergent population dynamics.

**Tech Stack:**
- **Backend**: Python with FastAPI + WebSocket
- **Frontend**: React 19 + TypeScript + Vite
- **Simulation**: Pure Python core with no UI dependencies

**Architecture highlights:**
- 58 registered behavior strategies across food seeking, predator avoidance, schooling, energy, territory, and poker interaction (see `core/algorithms/registry.py`)
- BaseSystem-driven simulation loop with a registered execution order for lifecycle, time, spawning, collisions, reproduction, and poker
- Dual execution modes: web UI and headless

## Living Architecture Sources

- **Authoritative layout:** [README – Project Structure](../README.md#project-structure) is the canonical tree and should be kept in sync with this document.
- **Diagrams:** Add links here if new diagrams are published; no standalone architecture diagrams are currently tracked in the repo.

## Project Structure (overview)

```
tank/
├── core/                          # Pure Python simulation (no UI dependencies)
│   ├── algorithms/                # Behavior strategy library + registry
│   ├── entities/                  # Fish, plant, predator, and resource models
│   ├── fish/                      # Componentized fish systems (energy, lifecycle, reproduction, poker stats)
│   ├── genetics/                  # Genomes, mutation, crossover
│   ├── poker/                     # Poker engine (core, betting, evaluation, strategy)
│   ├── systems/                   # BaseSystem, entity lifecycle, deterministic food spawning
│   ├── collision_system.py        # Collision detection (BaseSystem)
│   ├── reproduction_system.py     # Reproduction logic (BaseSystem)
│   ├── poker_system.py            # Poker events + history (BaseSystem)
│   ├── time_system.py             # Day/night cycles (BaseSystem)
│   ├── skill_game_system.py       # Skill game orchestration (BaseSystem)
│   ├── environment.py             # Spatial queries (implements World Protocol)
│   ├── simulation_engine.py       # Main engine and system registry
│   └── tank_world.py              # Simulation wrapper with config + RNG
├── backend/                       # FastAPI WebSocket server
│   ├── main.py                    # FastAPI app with Tank World Net API
│   ├── tank_registry.py           # Multi-tank management (Tank World Net)
│   ├── simulation_manager.py      # Per-tank lifecycle management
│   ├── simulation_runner.py       # Background simulation thread
│   ├── state_payloads.py          # Serialization DTOs
│   └── models.py                  # Data models
├── frontend/                      # React + TypeScript UI
│   ├── src/                       # Components, hooks, rendering utilities
│   └── package.json
├── simulation_engine.py           # Headless simulation runner
└── main.py                        # Main entry point
```

## Architecture Layers

### 1. Pure Simulation Core (core/)

**Design Goal:** Zero UI dependencies, fully testable

- **entities/**: Fish, Plant, predator, and resource classes with deterministic IDs
- **fish/**: Componentized fish systems (energy, lifecycle, reproduction, poker stats)
- **genetics/**: Genome definitions, mutation, crossover, adaptive inheritance helpers
- **algorithms/**: Behavior strategy library with registry + adaptive mutation
  - 58 strategies registered in `core/algorithms/registry.py`
  - Categories: 14 food seeking, 10 predator avoidance, 10 schooling, 8 energy, 8 territory, 8 poker interaction
  - Composable behaviors (`composable.py`) expose sub-behavior knobs for hybrids
- **environment.py**: Spatial grid for efficient proximity queries
- **ecosystem.py / ecosystem_population.py / ecosystem_stats.py**: Population tracking, death cause tallies, and reproduction stats
- **fish_communication.py / fish_memory.py**: Shared memory and communication helpers for strategies
- **tank_world.py**: Entry wrapper that wires config, RNG, and engine setup
- **simulation_engine.py**: Central loop with system registry, event bus, plant management, and deterministic RNG plumbing

### Behavior Algorithms & Registry

`core/algorithms/registry.py` is the authoritative source for behavior strategies:
- Deterministic list (`ALL_ALGORITHMS`) for serialization and indexing
- Adaptive mutation utilities (`inherit_algorithm_with_mutation`, `calculate_adaptive_mutation_factor`)
- Sub-behavior controls in `composable.py` for hybrid behaviors (threat response, food approach, energy style, social mode, poker engagement)

### Poker Systems

- **core/poker/**: Engine, betting, strategy, and evaluation packages used by simulation and mixed poker.
- **core/poker_system.py**: BaseSystem that tracks poker events, throttles mixed games, and exposes UI-facing history.
- **core/mixed_poker/** + **core/plant_poker.py**: Plant vs. fish poker integration, including plant-triggered reproduction rules.
- **skill_game_system.py** + **skills/games/**: Skill game orchestration with adapters (e.g., poker adapter in `skills/games/poker_adapter.py`).

### Systems & Registry

`BaseSystem` lives in `core/systems/base.py`. The simulation engine registers systems in deterministic order:

1. `EntityLifecycleSystem` (`core/systems/entity_lifecycle.py`) – per-frame lifecycle coordination
2. `TimeSystem` (`core/time_system.py`) – day/night cycle management
3. `FoodSpawningSystem` (`core/systems/food_spawning.py`) – deterministic food spawning using engine RNG
4. `CollisionSystem` (`core/collision_system.py`) – proximity detection and interaction hooks
5. `ReproductionSystem` (`core/reproduction_system.py`) – mating, offspring creation, and trait inheritance
6. `PokerSystem` (`core/poker_system.py`) - poker history, throttling, and stats

All systems expose `update(frame)`, `get_debug_info()`, and runtime enable/disable controls via the engine registry.

### Determinism Policy

- Core simulation randomness must flow through `SimulationEngine.rng` or `Environment.rng`.
- No global RNG calls (`random.*`) in core simulation paths; use injected RNGs or per-instance `Random`.
- The engine does not seed the global random module; determinism is explicit via seed/RNG injection.

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
      ├─ Update ecosystem stats and telemetry
      ├─ Consume telemetry events emitted by entities
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

Algorithms are defined in `core/algorithms/` and registered in `registry.py`:
- **Food seeking (14)**: e.g., GreedyFoodSeeker, FoodQualityOptimizer, SpiralForager
- **Predator avoidance (10)**: e.g., PanicFlee, StealthyAvoider, BorderHugger
- **Schooling/social (10)**: e.g., BoidsBehavior, LeaderFollower, PerimeterGuard
- **Energy management (8)**: e.g., EnergyConserver, MetabolicOptimizer, AdaptivePacer
- **Territory/exploration (8)**: e.g., TerritorialDefender, RoutePatroller, NomadicWanderer
- **Poker interaction (8)**: e.g., PokerStrategist, PokerOpportunist, PokerBluffer
- **Composable hybrids**: Configure threat response, food approach, energy style, social mode, and poker engagement via `composable.py`

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
- Poker outcomes are recorded via value objects (e.g., `PokerOutcomeRecord`, `MixedPokerOutcomeRecord`)

## Design Patterns

### System Registry Pattern
The simulation uses a **System Registry** for consistent management of all simulation subsystems:

```
SimulationEngine
    │
    ├─ _systems: List[BaseSystem]  (registered in execution order)
    │   ├─ EntityLifecycleSystem - Per-frame lifecycle coordination
    │   ├─ TimeSystem            - Day/night cycle management
    │   ├─ FoodSpawningSystem    - Deterministic food spawning
    │   ├─ CollisionSystem       - Collision detection and handling
    │   ├─ ReproductionSystem    - Reproduction logic and inheritance
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

### Phase-Based Update Loop
`SimulationEngine` uses explicit phase methods for the simulation loop:
- `_phase_frame_start()`: Reset counters, increment frame
- `_phase_time_update()`: Day/night cycle advancement
- `_phase_entity_act()`: Update all entities
- `_phase_lifecycle()`: Process deaths, add/remove entities
- `_phase_collision()`: Handle all collisions via CollisionSystem
- `_phase_reproduction()`: Handle reproduction via ReproductionSystem
Note: Entity spawns/removals are requested by systems and applied by the engine
between phases via the mutation queue (no mid-phase collection mutation).

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
- Pure entity logic in `core/entities/`
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
- 58 registered behavior algorithms compete for survival across six categories
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

- Main README: See `../README.md` (Project Structure is canonical)
- Vision & Philosophy: See `VISION.md`
- Architecture Decisions: See `adr/` directory

> Historical analysis docs have been archived to `archive/`.

## Change Log

- **2025-12-25**: Pruned stale documentation, archived historical analysis docs.
- **2025-12-23**: Aligned architecture doc with current module layout (algorithm registry counts, system registry order, poker systems) and linked to README structure section for ongoing authority.
