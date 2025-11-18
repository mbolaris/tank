# Architecture Documentation

## Overview

The Fish Tank Simulation is a web-based artificial life ecosystem where fish evolve behaviors through genetic algorithms. The architecture follows a clean separation between simulation logic and visualization.

## System Architecture

```
┌─────────────────┐
│  React Frontend │ (Port 3000)
│   (TypeScript)  │
└────────┬────────┘
         │ WebSocket
         │ + REST API
┌────────┴────────┐
│  FastAPI Backend│ (Port 8000)
└────────┬────────┘
         │
┌────────┴────────┐
│ SimulationEngine│
│   (Pure Python) │
└─────────────────┘
```

### Frontend (React + TypeScript)
- **Location**: `frontend/src/`
- **Purpose**: Web-based UI for visualizing the simulation
- **Key Components**:
  - Canvas renderer for fish, plants, and food
  - Stats panel showing population metrics
  - Control panel for simulation controls
  - Real-time updates via WebSocket

### Backend (FastAPI)
- **Location**: `backend/`
- **Purpose**: REST API and WebSocket server
- **Endpoints**:
  - `GET /api/state` - Get current simulation state
  - `WebSocket /ws` - Real-time simulation updates
  - `POST /api/spawn-fish` - Spawn a new fish
  - `POST /api/spawn-food` - Spawn food

### Simulation Core
- **Location**: `core/` and `simulation_engine.py`
- **Purpose**: Pure Python simulation logic without any UI dependencies
- **Key Features**:
  - Headless operation for testing and benchmarking
  - Genetic algorithms and evolution
  - Collision detection and spatial partitioning
  - Ecosystem management

## Core Modules

### simulation_engine.py
The main simulation engine that runs the fish tank ecosystem:
- **SimulationEngine**: Headless simulation without visualization
- **HeadlessSimulator**: Simplified wrapper for testing

### core/entities.py
Entity classes for all simulation objects:
- **Agent**: Base class for all entities
- **Fish**: Evolving fish with genetics, energy, and behavior
- **Food**: Food particles that fish consume
- **Plant**: Stationary plants that spawn food

### core/ecosystem.py
- **EcosystemManager**: Tracks population stats, births, deaths
- Genetic diversity metrics
- Algorithm performance tracking
- Species distribution

### core/genetics.py
- **Genome**: Genetic representation of fish traits
- Mutation and crossover for evolution
- Color, speed, size, vision, and behavior genes

### core/algorithms/
Behavior algorithms for fish:
- **BoidAlgorithm**: Flocking behavior
- **HunterAlgorithm**: Aggressive food seeking
- **CautiousAlgorithm**: Defensive behavior
- **WandererAlgorithm**: Exploratory movement
- 12+ other specialized algorithms

### core/environment.py
- **Environment**: Spatial queries for nearby entities
- **SpatialGrid**: Efficient spatial partitioning for collision detection

## Design Patterns

### 1. Template Method Pattern
`BaseSimulator` (in `core/simulators/base_simulator.py`) defines the simulation algorithm skeleton:
- `handle_collisions()`: Collision detection and response
- `handle_reproduction()`: Mating and offspring creation
- `spawn_auto_food()`: Automatic food generation
- Subclasses implement specific methods like `check_collision()`

### 2. Strategy Pattern
Different movement strategies for entities:
- `AlgorithmicMovement`: Uses genetic algorithm for behavior
- `ConstantVelocityMovement`: Simple linear movement
- `StaticMovement`: No movement (plants)

### 3. Component-Based Architecture
Fish behavior is modular:
- Energy system
- Reproduction system
- Memory system
- Movement system

## Simulation Loop

```
1. Update time system (day/night cycle)
2. For each entity:
   - Update entity state
   - Handle reproduction (Fish)
   - Handle food spawning (Plant)
   - Check for death conditions
3. Update spatial grid for efficient queries
4. Handle collisions:
   - Fish-Food: Feeding
   - Fish-Fish: Poker games for energy transfer
5. Handle reproduction (mate finding)
6. Update ecosystem statistics
7. Auto-spawn food and emergency fish
8. Send state to frontend (web mode)
```

## Running Modes

### Web Mode (Default)
```bash
python main.py
```
- React frontend at http://localhost:3000
- FastAPI backend at http://localhost:8000
- Real-time visualization
- Interactive controls

### Headless Mode
```bash
python main.py --headless --max-frames 10000
```
- No visualization
- Stats printed to console
- Faster than realtime (10-300x speedup)
- Useful for testing and benchmarking

## Data Flow

### Web Mode
```
SimulationEngine → Backend API → WebSocket → React Frontend
     ↓                                            ↓
  Statistics                                  Rendering
```

### Headless Mode
```
SimulationEngine → Console Output
     ↓
  Statistics
     ↓
  Reports (algorithm_performance_report.txt)
```

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

### Poker System
- Fish "play poker" when they collide
- Winner gains energy from loser
- Hand rankings determine outcomes
- 5% house cut on energy transfers

## Performance Optimizations

### Spatial Partitioning
- Grid-based spatial indexing for O(1) proximity queries
- Reduces collision checks from O(n²) to O(n)
- Configurable cell size for different population densities

### Caching
- Cached nearby entity queries
- Cached movement calculations
- Reduces redundant computations

## Testing

### Unit Tests
```bash
pytest tests/
```

### Headless Testing
```bash
python main.py --headless --max-frames 1000 --seed 42
```

## File Structure

```
tank/
├── main.py                    # Entry point
├── simulation_engine.py       # Headless simulation engine
├── backend/                   # FastAPI backend
│   ├── main.py               # API server
│   └── simulation_runner.py  # Backend simulation wrapper
├── core/                      # Pure simulation logic
│   ├── entities.py           # Fish, Food, Plant
│   ├── ecosystem.py          # Population management
│   ├── genetics.py           # Genetic algorithms
│   ├── environment.py        # Spatial queries
│   ├── collision_system.py   # Collision detection
│   ├── algorithms/           # Behavior algorithms
│   └── simulators/           # Base simulator classes
├── frontend/                  # React UI
│   └── src/
│       ├── components/       # React components
│       └── utils/            # Frontend utilities
└── tests/                     # Test suite
```

## Future Improvements

### High Priority
1. **Refactor EcosystemManager** (~800 lines)
   - Split into PopulationManager, AlgorithmTracker, StatsManager
   - Reduce complexity of god object

2. **Component-based Fish Architecture**
   - Split Fish class (~463 lines) into components
   - EnergyComponent, ReproductionComponent, MemoryComponent

### Medium Priority
3. **Event System**
   - Observer pattern for ecosystem events
   - Decoupled event handling

4. **Configuration System**
   - YAML/JSON config files for simulation parameters
   - Easy parameter tuning

### Low Priority
5. **Custom Exception Hierarchy**
   - SimulationError, EntityError, CollisionError
   - Better error handling

## Best Practices

1. **Type Hints**: All code uses comprehensive type hints
2. **Pure Functions**: Core logic is pure Python without visualization dependencies
3. **Separation of Concerns**: Simulation logic separate from UI
4. **Testability**: Headless mode enables automated testing
5. **Documentation**: Comprehensive docstrings

## Conclusion

The architecture is designed for:
- **Modularity**: Clear separation between simulation and visualization
- **Testability**: Headless mode for automated testing
- **Performance**: Spatial partitioning and caching
- **Extensibility**: Easy to add new behaviors and features
- **Web-first**: Modern React-based UI with real-time updates
