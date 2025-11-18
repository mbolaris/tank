# 🐠 Artificial Life Fish Tank Simulation

An advanced artificial life ecosystem simulation featuring **48 parametrizable behavior algorithms**, **neural network brains**, genetics, evolution, energy systems, and emergent population dynamics with a **React-based web UI**.

## 🎯 Overview

This is a **cutting-edge ALife simulation** with a modern web interface that demonstrates complex ecosystem behaviors, **algorithmic evolution**, **neuroevolution**, and competitive dynamics. Fish can evolve with different AI systems including parametrizable algorithms, neural networks, or rule-based behavior. The simulation features:

- 🧬 **ALGORITHMIC EVOLUTION** - 48 unique parametrizable behavior strategies!
- 🧠 **Neural Network Brains** - Fish with evolving AI that learn survival strategies
- 🦀 **Balanced Predator-Prey** - Crabs hunt fish with realistic hunting mechanics
- 🐠 **Multiple Competing Species** - Algorithmic vs Neural vs Rule-based AI
- 🧬 **Genetic Evolution** - Traits, algorithms, AND brains evolve across generations
- 🌐 **Modern Web UI** - React-based interface with real-time visualization
- 📊 **Live Statistics** - Watch population dynamics and genetics evolve
- 🌍 **Rich Ecosystem** - Day/night cycles, living plants, population dynamics
- 🎴 **Poker Minigame** - Fish can play poker against each other for energy!

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

### 🧠 **Neural Network Brains**
Fish can have **evolving neural network brains** that control their behavior:

- **Architecture**: 12 inputs → 8 hidden neurons → 2 outputs (velocity X/Y)
- **Inputs**: Distance/angle to food, allies, predators, energy level, speed, life stage
- **Outputs**: Desired swimming direction
- **Evolution**: Neural weights inherit from parents with mutation
- **Learning**: Better brains survive and reproduce, improving over generations

### 🎴 **Fish Poker Minigame**
Fish can play poker against each other for energy rewards!

- **Automatic**: Fish play when they collide and have >10 energy
- **5-Card Draw**: Standard poker hand rankings
- **Energy Stakes**: Winner takes energy from loser (with house cut)
- **Live Events**: See poker games happen in real-time in the UI
- **Statistics**: Track total games, wins/losses, best hands

### 🐠 **Multiple Competing Species**
The ecosystem supports **4 different AI approaches** competing for resources:

1. **Algorithmic Fish** - 48 different parametrizable behavior algorithms
2. **Neural Schooling Fish** - AI-controlled with evolving neural network brains
3. **Traditional Schooling Fish** - Rule-based flocking behavior
4. **Solo Fish** - Rule-based AI, traditional behavior

**Competition**: All species compete for the same food, creating evolutionary pressure for better strategies!

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

```bash
# Terminal 1: Start the backend server
python main.py

# Terminal 2: Start the React frontend (in frontend/ directory)
cd frontend
npm start

# Open http://localhost:3000 in your browser
```

The backend runs on port 8000, frontend on port 3000. The frontend connects to the backend via WebSocket for real-time updates.

### Headless Mode (Fast, Stats-Only)

Run simulations 10-300x faster than realtime without visualization for testing or data collection:

```bash
# Quick test run
python main.py --headless --max-frames 1000

# Long simulation with periodic stats
python main.py --headless --max-frames 100000 --stats-interval 3000

# Deterministic simulation (for testing)
python main.py --headless --max-frames 1000 --seed 42
```

**Benefits of headless mode:**
- 10-300x faster than realtime
- Perfect for data collection and long simulations
- No display required
- Identical simulation behavior to web UI

## 📁 Project Structure

```
tank/
├── main.py                  # Entry point (web server or headless)
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
│   ├── entities.py         # Fish, Plant, Food, Crab, Castle
│   ├── genetics.py         # Genome system & inheritance
│   ├── neural_brain.py     # Neural network brain system
│   ├── ecosystem.py        # Population tracking & statistics
│   ├── time_system.py      # Day/night cycle management
│   ├── environment.py      # Spatial queries
│   ├── movement_strategy.py # Fish movement behaviors
│   ├── fish_poker.py       # Poker minigame system
│   ├── behavior_algorithms.py # 48 parametrizable algorithms
│   └── constants.py        # Configuration parameters
├── tests/                  # Test suite
│   ├── test_simulation.py  # Integration test
│   ├── test_parity.py      # Determinism test
│   └── ...
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

### Neuroevolution in Action
- **Neural fish**: Learn to avoid predators over generations
- **Trait selection**: Better brains = more offspring
- **Competitive dynamics**: Neural vs traditional AI competing
- **Emergent strategies**: Fish discover optimal foraging patterns

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
- Speed modifier (swimming speed)
- Size modifier (visual size)
- Vision range (detection radius)
- Metabolism rate (energy consumption)
- Max energy (stamina and lifespan)
- Fertility (reproduction rate)
- Visual traits (body shape, fin size, tail size, pattern)
- Behavior algorithm (48 choices)
- Neural network brain (optional)

### Mutation
- Small random variations during reproduction
- Parameter tuning for algorithms
- Weight mutations for neural networks
- Visual trait variations

### Natural Selection
- Fish with better-adapted genetics survive longer
- Better algorithms and brains reproduce more
- Weak strategies are selected out
- Population evolves over generations

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
- **Neuroevolution**: Evolving neural networks through natural selection
- **Competitive Coevolution**: Multiple species competing for resources
- **Predator-Prey Dynamics**: Balanced hunting and evasion
- **Population Dynamics**: Carrying capacity, birth/death rates
- **Energy Flow**: Producers (plants) → Consumers (fish)
- **Emergent Behavior**: Complex ecosystem from simple rules
- **Artificial Intelligence**: Neural networks vs rule-based AI
- **Evolutionary Computation**: Genetic algorithms with neural networks
- **Game Theory**: Poker interactions and strategic play

## 🔬 Future Enhancements

Completed: ✅
- [✅] Neural network fish brains (learning)
- [✅] Predator-prey balance improvements
- [✅] Multiple species with different niches
- [✅] Headless mode with full parity
- [✅] Deterministic seeding for testing
- [✅] React-based web UI
- [✅] Fish poker minigame

Potential additions:
- [ ] LSTM/Recurrent neural networks (fish with memory)
- [ ] Save/load ecosystem states
- [ ] Replay system to watch evolution over time
- [ ] More predator species (different hunting strategies)
- [ ] Seasonal variations
- [ ] Water quality parameters
- [ ] Disease/parasites system
- [ ] Territorial behavior implementation
- [ ] Sexual dimorphism (male/female)
- [ ] Multi-agent reinforcement learning
- [ ] Graph neural networks for social interactions
- [ ] Real-time evolution graphs in UI
- [ ] Downloadable simulation data/stats

## 🏗️ Architecture

The simulation uses a clean architecture with separation of concerns:

- **Core Logic** (`core/`): Pure Python simulation engine
  - No UI dependencies
  - Fully testable
  - Used by both web and headless modes

- **Backend** (`backend/`): FastAPI WebSocket server
  - Runs simulation in background thread
  - Broadcasts state at 30 FPS via WebSocket
  - Handles commands (add food, pause, reset)

- **Frontend** (`frontend/`): React + TypeScript
  - HTML5 Canvas rendering
  - Parametric SVG fish templates
  - Real-time stats and controls
  - Responsive design

## 📜 License

This project is open source. Feel free to modify and extend!

## 🙏 Credits

Built with:
- **React**: Frontend framework
- **FastAPI**: Backend API framework
- **Python 3.8+**: Core language
- **TypeScript**: Frontend type safety
- **HTML5 Canvas**: Real-time rendering
- **WebSocket**: Real-time communication
- **Love for ALife**: Inspired by Conway's Life, Tierra, and evolutionary algorithms

---

**Enjoy watching life evolve! 🌊🐠✨**

For more information, visit the `docs/` directory (if available) or explore the codebase!
