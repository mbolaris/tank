# 🐠 Artificial Life Fish Tank Simulation

An advanced artificial life ecosystem simulation featuring **48 parametrizable behavior algorithms**, genetics, evolution, energy systems, and emergent population dynamics with a **React-based web UI**.

## 🎯 Overview

This is a **cutting-edge ALife simulation** with a modern web interface that demonstrates complex ecosystem behaviors through **algorithmic evolution** and competitive dynamics. Fish evolve diverse survival strategies through genetic algorithms, with each fish inheriting and mutating behavior algorithms across generations. The simulation features:

- 🧬 **ALGORITHMIC EVOLUTION** - 48 unique parametrizable behavior strategies that evolve!
- 🦀 **Balanced Predator-Prey** - Crabs hunt fish with realistic hunting mechanics
- 🔬 **Genetic Evolution** - Traits and algorithms evolve across generations
- 🌐 **Modern Web UI** - React-based interface with real-time visualization
- 📊 **Live Statistics & LLM Export** - Track evolution and export data for AI analysis
- 🌍 **Rich Ecosystem** - Day/night cycles, living plants, population dynamics
- 🎴 **Poker Minigame** - Fish can play poker against each other for energy!
- ⚡ **Headless Mode** - Run 10-300x faster for data collection and testing

## 🌟 **Key Features**

### 🧬 **ALGORITHMIC EVOLUTION SYSTEM** 🚀

The simulation features **48 parametrizable behavior algorithms** that fish can inherit and evolve! This creates unprecedented diversity and sophistication in fish behavior.

**Key Features:**
- **48 Unique Algorithms** across 5 categories:
  - 🍔 Food Seeking (12 algorithms)
  - 🛡️ Predator Avoidance (10 algorithms)
  - 🐟 Schooling/Social (10 algorithms)
  - ⚡ Energy Management (8 algorithms)
  - 🗺️ Territory/Exploration (8 algorithms)

- **Parametrizable Behaviors**: Each algorithm has tunable parameters that mutate during reproduction
- **Inheritance**: Offspring inherit parent's algorithm type with parameter mutations
- **Natural Selection**: Better algorithms survive and spread through the population
- **High Interpretability**: Unlike neural networks, algorithm behaviors are clear and debuggable

**Example Algorithms:**
- `GreedyFoodSeeker` - Always move toward nearest food
- `AmbushFeeder` - Wait for food to come close
- `PanicFlee` - Escape from predators at maximum speed
- `TightSchooler` - Stay very close to school members
- `BurstSwimmer` - Alternate between bursts and rest
- `TerritorialDefender` - Defend territory from intruders
- ...and 42 more!

### 🎴 **Fish Poker Minigame**
Fish can play poker against each other for energy rewards!

- **Automatic**: Fish play when they collide and have >10 energy
- **5-Card Draw**: Standard poker hand rankings
- **Energy Stakes**: Winner takes energy from loser (with house cut)
- **Live Events**: See poker games happen in real-time in the UI
- **Statistics**: Track total games, wins/losses, best hands

### 🧬 **Pure Algorithmic Evolution**
The ecosystem focuses on **algorithmic evolution** with all fish competing using parametrizable behavior algorithms:

- **48 Different Algorithms** across 5 categories (food seeking, predator avoidance, schooling, energy management, territory)
- **Parameter Tuning**: Each algorithm has parameters that mutate during reproduction
- **Natural Selection**: Better algorithms survive and reproduce, spreading through the population
- **High Interpretability**: Unlike black-box neural networks, algorithm behaviors are clear and analyzable
- **Competition**: All fish compete for the same resources, creating evolutionary pressure for optimal strategies

### 🌐 **Modern Web UI**
Built with **React + FastAPI + WebSocket**:

- **Real-time Visualization**: HTML5 Canvas rendering at 30 FPS
- **Parametric Fish**: SVG-based fish with genetic visual traits
- **Live Stats Panel**: Population, generation, births, deaths, energy
- **Poker Events**: See live poker games and results
- **Control Panel**: Pause/resume, add food, reset simulation
- **Responsive Design**: Works on desktop and mobile

## 🚀 Running the Simulation

### Installation

```bash
# Install Python dependencies
pip install -e .

# Install frontend dependencies (in frontend/ directory)
cd frontend
npm install
```

### Start the Simulation (Web UI)

**⚠️ IMPORTANT:** You need to run **BOTH** backend and frontend servers!

**Option 1: Automatic (Recommended)**
```bash
# Run the startup script (starts both servers)
./start-app.sh

# Then open http://localhost:3000 in your browser
```

**Option 2: Manual (Two Terminals)**
```bash
# Terminal 1: Start the backend server
python main.py

# Terminal 2: Start the React frontend (in frontend/ directory)
cd frontend
npm run dev

# Then open http://localhost:3000 in your browser
```

**📍 Access Points:**
- **Frontend UI**: http://localhost:3000 ← **Use this in your browser!**
- **Backend API**: http://localhost:8000 (WebSocket endpoint for frontend)

The backend runs on port 8000, frontend on port 3000. The frontend connects to the backend via WebSocket for real-time updates.

**🐛 Troubleshooting:** If you see a blank page, see [QUICK_START.md](./QUICK_START.md) for detailed setup instructions.

### Headless Mode (Fast, Stats-Only)

Run simulations 10-300x faster than realtime without visualization for testing or data collection:

```bash
# Quick test run
python main.py --headless --max-frames 1000

# Long simulation with periodic stats
python main.py --headless --max-frames 100000 --stats-interval 3000

# Deterministic simulation (for testing)
python main.py --headless --max-frames 1000 --seed 42

# Export comprehensive stats for LLM analysis
python main.py --headless --max-frames 10000 --export-stats results.json
```

**Benefits of headless mode:**
- 10-300x faster than realtime
- Perfect for data collection and long simulations
- No display required
- Identical simulation behavior to web UI
- **LLM-friendly stats export**: Export comprehensive JSON data including algorithm performance, evolution trends, and population dynamics for AI-assisted analysis

## 📁 Project Structure

```
tank/
├── main.py                  # Entry point (web server or headless)
├── tank_world.py            # TankWorld wrapper with config & RNG management
├── simulation_engine.py     # Core headless simulation engine
├── backend/                 # FastAPI backend
│   ├── main.py             # WebSocket server
│   ├── simulation_runner.py # Threaded simulation runner
│   └── models.py           # Pydantic data models
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── hooks/          # Custom hooks (WebSocket)
│   │   └── utils/          # Rendering utilities
│   └── package.json
├── core/                   # Shared simulation logic
│   ├── entities.py         # Fish, Plant, Food, Crab entities
│   ├── genetics.py         # Genome system & inheritance
│   ├── ecosystem.py        # Population tracking & statistics
│   ├── enhanced_statistics.py # Comprehensive stats for LLM export
│   ├── time_system.py      # Day/night cycle management
│   ├── environment.py      # Spatial queries & collision detection
│   ├── movement_strategy.py # AlgorithmicMovement implementation
│   ├── fish_poker.py       # Poker minigame system
│   ├── algorithms/         # Behavior algorithm library
│   │   ├── food_seeking.py # 12 food-seeking algorithms
│   │   ├── predator_avoidance.py # 10 predator avoidance algorithms
│   │   ├── schooling.py    # 10 schooling algorithms
│   │   ├── energy_management.py # 8 energy management algorithms
│   │   └── territory.py    # 8 territory/exploration algorithms
│   └── constants.py        # Configuration parameters
├── tests/                  # Test suite
│   ├── test_simulation.py  # Integration test
│   ├── test_parity.py      # Determinism test
│   └── ...
├── docs/                   # Additional documentation
│   ├── ARCHITECTURE.md     # Architecture details
│   ├── ALGORITHMIC_EVOLUTION.md # Algorithm evolution guide
│   ├── DEPLOYMENT_GUIDE.md # Deployment instructions
│   └── HEADLESS_MODE.md    # Headless mode documentation
├── BEHAVIOR_DEVELOPMENT_GUIDE.md # Guide for creating behaviors
├── EVOLUTION_EXAMPLE.md    # Example evolution scenarios
├── QUICK_REFERENCE.md      # Quick command reference
└── README.md               # This file
```

## 🎮 Web UI Controls

- **Add Food** button - Drop food into the tank
- **Pause/Resume** button - Pause or resume the simulation
- **Reset** button - Reset the simulation to initial state

## 🔧 Configuration

Key parameters in `core/constants.py`:

```python
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FRAME_RATE = 30
NUM_SCHOOLING_FISH = 6

# Automatic food spawning
AUTO_FOOD_SPAWN_RATE = 180  # Spawn food every 6 seconds
AUTO_FOOD_ENABLED = True  # Enable/disable automatic food

# Poker settings
POKER_ENABLED = True
POKER_MIN_ENERGY = 10.0  # Minimum energy to play poker
POKER_BASE_STAKE = 5.0   # Base energy stake for poker
POKER_HOUSE_CUT_PERCENTAGE = 10  # House takes 10% of winnings
```

Key entity parameters in `core/entities.py`:

```python
# Fish
BASE_MAX_ENERGY = 100.0
ENERGY_FROM_FOOD = 40.0
BASE_METABOLISM = 0.015
BABY_AGE = 300  # 10 seconds
ADULT_AGE = 1800  # 1 minute
BASE_MAX_AGE = 5400  # 3 minutes

# Plants
BASE_FOOD_PRODUCTION_RATE = 150  # 5 seconds
MAX_FOOD_CAPACITY = 8  # per plant
```

## 🧪 Ecosystem Dynamics Observed

### Sustainable Population
- **Population**: Stable at 7-15 fish with balanced predation
- **Birth rate**: ~10 births per 90 seconds
- **Generation transitions**: Continuous evolution across generations
- **Energy flow**: Plants → Food → Fish → Predators

### Algorithmic Evolution in Action
- **Algorithm diversity**: Population develops mix of strategies over time
- **Trait selection**: Better algorithms = more offspring
- **Parameter optimization**: Algorithm parameters fine-tune through mutation
- **Emergent strategies**: Fish discover optimal foraging and survival patterns
- **Performance tracking**: Stats export shows which algorithms dominate

### Poker Economy
- **Energy redistribution**: Poker transfers energy between fish
- **Fitness signaling**: Better poker players accumulate more energy
- **Risk/reward**: Fish must balance poker with survival needs

### Population Dynamics
- **Carrying capacity**: Max 100 fish prevents overpopulation
- **Birth-death balance**: Sustainable with 3 food-producing plants
- **Predator-prey cycles**: Crab population affects fish numbers
- **Starvation**: Rare with proper plant density

## 🧬 Genetics & Evolution

### Heritable Traits
- **Physical traits**: Speed, size, vision range, metabolism, max energy, fertility
- **Visual traits**: Body shape, fin size, tail size, color pattern
- **Behavior algorithm**: One of 48 parametrizable algorithms (inherited from parent)
- **Algorithm parameters**: Tunable values that control algorithm behavior

### Mutation
- **Trait mutations**: Small random variations in physical traits during reproduction
- **Parameter tuning**: Algorithm parameters mutate slightly to explore nearby strategies
- **Algorithm switching**: Rare mutations can change to a completely different algorithm
- **Visual variations**: Color and shape traits evolve independently

### Natural Selection
- **Survival pressure**: Fish with better-adapted genetics survive longer
- **Reproductive success**: Better algorithms reproduce more, spreading through population
- **Competition**: Limited food creates selection pressure for efficient foraging
- **Generational evolution**: Population average fitness improves over time
- **Algorithm diversity**: Multiple successful strategies can coexist

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run specific test
python tests/test_simulation.py

# Test determinism
python tests/test_parity.py
```

## 🎓 Educational Value

This simulation demonstrates:
- **Genetics & Heredity**: Mendelian inheritance with mutations
- **Natural Selection**: Survival of the fittest in action
- **Algorithmic Evolution**: Genetic algorithms with parametrizable behaviors
- **Predator-Prey Dynamics**: Balanced hunting and evasion
- **Population Dynamics**: Carrying capacity, birth/death rates
- **Energy Flow**: Producers (plants) → Consumers (fish) → Predators
- **Emergent Behavior**: Complex ecosystem from simple rules
- **Evolutionary Computation**: Parameter optimization through natural selection
- **Game Theory**: Poker interactions and strategic play
- **Interpretable AI**: Clear, debuggable algorithm behaviors vs black-box approaches
- **Data Science**: LLM-friendly stat exports for AI-assisted analysis

## 🔬 Recent Improvements & Future Enhancements

Recently Completed: ✅
- [✅] 48 parametrizable behavior algorithms
- [✅] TankWorld class for clean simulation management
- [✅] LLM-friendly JSON stats export
- [✅] Comprehensive behavior evolution tracking
- [✅] Predator-prey balance improvements
- [✅] Headless mode (10-300x faster)
- [✅] Deterministic seeding for reproducibility
- [✅] React-based web UI
- [✅] Fish poker minigame
- [✅] Removed pygame dependencies (pure Python core)

Potential Future Additions:
- [ ] Neural network option (as alternative to algorithmic evolution)
- [ ] Save/load ecosystem states
- [ ] Replay system to watch evolution over time
- [ ] More predator species (different hunting strategies)
- [ ] Seasonal variations and environmental events
- [ ] Water quality parameters affecting survival
- [ ] Disease/parasites system
- [ ] Enhanced territorial behavior
- [ ] Sexual dimorphism (male/female traits)
- [ ] Real-time evolution graphs in UI
- [ ] Downloadable simulation data CSV export
- [ ] Multi-threaded population simulation
- [ ] Cloud-based long-term evolution experiments

## 🏗️ Architecture

The simulation uses a clean architecture with separation of concerns:

- **TankWorld** (`tank_world.py`): Simulation wrapper
  - Clean interface for configuration management
  - Random number generator (RNG) management for deterministic behavior
  - Unified API for both headless and web modes
  - Wraps SimulationEngine with easy-to-use controls

- **Core Logic** (`core/`): Pure Python simulation engine
  - No UI dependencies (pygame removed)
  - Fully testable and reproducible
  - Used by both web and headless modes
  - Algorithm-based evolution system

- **Backend** (`backend/`): FastAPI WebSocket server
  - Runs simulation in background thread
  - Broadcasts state at 30 FPS via WebSocket
  - Handles commands (add food, pause, reset, spawn fish)
  - REST API for state queries

- **Frontend** (`frontend/`): React + TypeScript
  - HTML5 Canvas rendering
  - Parametric SVG fish templates
  - Real-time stats and controls
  - Responsive design
  - WebSocket connection for live updates

## 📜 License

This project is open source. Feel free to modify and extend!

## 🙏 Credits

Built with:
- **Python 3.8+**: Core simulation language
- **React + TypeScript**: Frontend framework with type safety
- **FastAPI**: Modern backend API framework
- **NumPy**: Numerical computations
- **HTML5 Canvas**: Real-time visualization
- **WebSocket**: Real-time client-server communication
- **Uvicorn**: High-performance ASGI server
- **Love for ALife**: Inspired by Conway's Life, Tierra, and evolutionary algorithms

## 📚 Additional Resources

For more information:
- **Architecture details**: See `docs/ARCHITECTURE.md`
- **Algorithmic evolution**: See `docs/ALGORITHMIC_EVOLUTION.md`
- **Behavior development**: See `BEHAVIOR_DEVELOPMENT_GUIDE.md`
- **Evolution examples**: See `EVOLUTION_EXAMPLE.md`
- **Quick reference**: See `QUICK_REFERENCE.md`
- **Deployment guide**: See `docs/DEPLOYMENT_GUIDE.md`
- **Headless mode**: See `docs/HEADLESS_MODE.md`

---

**Enjoy watching algorithmic life evolve! 🌊🐠✨🧬**
