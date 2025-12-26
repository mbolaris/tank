# Tank World

**A framework for AI-driven automated Artificial Life research.**

Tank World is an open-source platform where AI agents conduct Alife research autonomously. The simulation runs, collects data, and then an AI agent analyzes results and improves the underlying algorithms—creating a continuous, closed-loop research cycle that runs without human intervention.

The fish tank visualization is just the beginning. It makes the research **entertaining enough to watch**, which matters because entertaining simulations can drive distributed compute contributions. In future versions, the AI will evolve the visualizations themselves to maximize engagement.

> **See [docs/VISION.md](docs/VISION.md) for the full project vision and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for technical details.**

---

## The Core Idea: Two-Layer Evolution

### Layer 1: Population Evolution (Inside the Tank)

Traditional evolutionary computation. Fish compete for survival using behavior algorithms:
- 58 parametrizable behavior strategies across 6 categories
- Natural selection optimizes algorithm parameters over generations
- Better strategies = more reproduction and survival

### Layer 2: Algorithmic Evolution (Outside the Tank)

After simulation runs complete, an AI agent (like Claude) analyzes performance data and improves the algorithms themselves:
- Identify underperforming behaviors and why they fail
- Generate improved algorithm code
- Create new behavior strategies
- Remove ineffective approaches

**The loop**: Evolve Population → Collect Data → AI Improves Code → Evolve Again

This is what makes Tank World different: the rules of evolution themselves evolve.

---

## Long-Term Goals

Tank World aims to be the **infrastructure for automated Alife research**:

1. **Closed-loop research**: Fully automated improvement cycles running 24/7 without human intervention
2. **Legitimate research platform**: Alife research with measurable results and publishable findings
3. **Distributed compute network**: Users contribute compute by running entertaining simulations on their devices
4. **Evolving visualization**: AI evolves not just behaviors but the visual representation itself—optimizing for engagement
5. **Self-improving framework**: The system discovers what questions to ask, proposes experiments, and expands its own capabilities

The ultimate vision: a research framework that conducts Alife experiments autonomously, learns from results, improves its own algorithms, and scales across a distributed network—all while being genuinely entertaining to watch.

**Current status**: Phase 1 (Foundation) complete. Layer 2 evolution proven but not yet fully automated.

---

## AI Oceanographer & Documentary Layer (Planned)

Today, Tank World already combines an Alife engine with an AI code-evolution loop. A future layer is an AI “oceanographer” that
 sits on top of all of this and talks to the user.

The idea is to have an AI narrator – think Jacques Cousteau or a slightly stranger Steve Zissou cousin – whose job is to:

- Explain what experiment is currently running in your tank
- Point out interesting behaviors and evolutionary events as they happen
- Connect visible behavior (“these blue predators discovered ambush tactics”) to underlying algorithm changes and fitness signal
  s
- Frame each tank run as a “mission” toward some goal, even if it’s a proxy task like optimizing an algorithm on a benchmark

Over time, the tank becomes AI-generated documentary content about artificial ecosystems. Users aren’t just donating compute; th
ey’re watching an ongoing nature series where the “creatures” are candidate algorithms and policies.

We are deliberately conservative in claims here: most tanks will be working on proxy problems (e.g., algorithm tuning, synthetic
 tasks), not directly curing diseases. The long-term goal is to make it easy, engaging, and honest to run Alife experiments tha
t can gradually be mapped to real-world problem domains.

---

## Current Features

- **Algorithmic Evolution** - 58 unique parametrizable behavior strategies that evolve
- **AI Code Evolution** - Automated coding agent improves algorithms between generations
- **Predator-Prey Dynamics** - Crabs hunt fish in the ecosystem
- **Fractal Plants** - L-system plants with genetic evolution and nectar production
- **Genetic Evolution** - Traits and algorithms evolve across generations
- **Modern Web UI** - React-based interface with real-time visualization
- **Live Statistics & LLM Export** - Track evolution and export data for AI analysis
- **Rich Ecosystem** - Day/night cycles, living plants, population dynamics
- **Poker Minigame** - Fish can play poker against each other for energy
- **Headless Mode** - Run 10-300x faster for data collection and testing

## Detailed Feature Breakdown

### Algorithmic Evolution System

The simulation features **58 parametrizable behavior algorithms** that fish can inherit and evolve! This creates unprecedented diversity and sophistication in fish behavior.

**Key Features:**
- **58 Unique Algorithms** across 6 categories:
  - 🍔 Food Seeking (14 algorithms)
  - 🛡️ Predator Avoidance (10 algorithms)
  - 🐟 Schooling/Social (10 algorithms)
  - ⚡ Energy Management (8 algorithms)
  - 🗺️ Territory/Exploration (8 algorithms)
  - 🎴 Poker Interactions (8 algorithms)

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
- `PokerChallenger` - Actively seek poker games
- `PokerDodger` - Avoid poker encounters
- `PokerStrategist` - Uses opponent modeling for strategic poker play
- `PokerBluffer` - Varies behavior unpredictably to confuse opponents
- ...and 48 more!

### Fish Poker Minigame
Fish can play poker against each other and against plants for energy rewards!

- **Automatic**: Fish play when they collide and have >10 energy
- **Texas Hold'em**: Full poker rules with community cards and betting rounds
- **Energy Stakes**: Winner takes energy from loser (house cut only for fish-vs-fish)
- **Mixed Games**: Fish and plants can play together (requires at least 1 fish per game)
- **Energy Flow Tracking**: Stats panel shows 🌱⚡→🐟 indicator for net plant-to-fish energy transfers
- **Evolving Poker Strategies**: Fish use genome-based poker aggression that evolves across generations!
  - Each fish's poker playing style is determined by their genome's aggression trait
  - Evolutionary pressure: Fish with optimal poker aggression win more energy and reproduce more
  - 8 specialized poker behavior algorithms (Challenger, Dodger, Gambler, Strategist, Bluffer, Conservative, and more)
- **Live Events**: See poker games happen in real-time in the UI with animated energy transfer arrows
- **Statistics**: Track total games, wins/losses, best hands, and plant-fish energy flow

### Fractal Plants with L-System Genetics
Plants in the ecosystem are procedurally generated using **L-system fractals** with genetic inheritance:

- **Genetic Diversity**: Each plant has a unique genome controlling branch angles, growth patterns, and colors
- **Energy Collection**: Plants passively collect energy from the environment
- **Nectar Production**: When plants accumulate enough energy, they produce nectar (food) with floral patterns
- **Plant Poker**: Plants can play poker against fish - winning fish gain energy from plants
- **Root Spots**: Plants grow from fixed anchor points at the tank bottom
- **Visual Evolution**: Plant shapes and colors evolve across generations

### Pure Algorithmic Evolution
The ecosystem focuses on **algorithmic evolution** with all fish competing using parametrizable behavior algorithms:

- **58 Different Algorithms** across 6 categories (food seeking, predator avoidance, schooling, energy management, territory, poker interactions)
- **Parameter Tuning**: Each algorithm has parameters that mutate during reproduction
- **Natural Selection**: Better algorithms survive and reproduce, spreading through the population
- **High Interpretability**: Unlike black-box neural networks, algorithm behaviors are clear and analyzable
- **Competition**: All fish compete for the same resources, creating evolutionary pressure for optimal strategies

### Modern Web UI
Built with **React + FastAPI + WebSocket**:

- **Real-time Visualization**: HTML5 Canvas rendering at 30 FPS
- **Parametric Fish**: SVG-based fish with genetic visual traits
- **Live Stats Panel**: Population, generation, births, deaths, energy
- **Poker Events**: See live poker games and results
- **Control Panel**: Pause/resume, add food, reset simulation
- **Responsive Design**: Works on desktop and mobile
- **View Toggle**: Switch between Single Tank and Network views via a central pill-style toggle
- **Tank Navigator**: Cycle through tanks with ← → arrow buttons or keyboard shortcuts

## Running the Simulation

### Prerequisites

- **Python 3.8+**
- **Node 18+** (for the React/Vite frontend)
- Recommended: create a virtual environment before installing Python dependencies

### Install dependencies

#### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Core + developer tooling (pytest, black, ruff, mypy)
python -m pip install --upgrade pip
python -m pip install -e .[dev]

# OPTIONAL: AI Code Evolution dependencies
python -m pip install -e .[ai]

# Frontend dependencies (run from the frontend/ directory)
cd frontend
npm install
```

#### Linux/Mac

```bash
python3 -m venv .venv
source .venv/bin/activate

# Core + developer tooling (pytest, black, ruff, mypy)
pip install -e .[dev]

# OPTIONAL: AI Code Evolution dependencies
pip install -e .[ai]

# Frontend dependencies (run from the frontend/ directory)
cd frontend
npm install
```

### Start the Simulation (Web UI)

```bash
# Terminal 1: Start the backend server (FastAPI + WebSockets)
python main.py

# Terminal 2: Start the React frontend (from frontend/)
cd frontend
npm run dev

# Open http://localhost:3000
```

The backend listens on port **8000** by default; the frontend proxies WebSocket traffic to it during development.

You can also launch the backend via the installed console script:

```bash
fishtank
```

### Headless Mode (Fast, Stats-Only)

Run simulations 10-300x faster than realtime without visualization for testing or data collection. Defaults: `--max-frames 10000`, `--stats-interval 300`.

```bash
# Quick test run
python main.py --headless --max-frames 1000

# Long simulation with periodic stats
python main.py --headless --max-frames 100000 --stats-interval 1000

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

## Code Quality & Testing

Keep changes safe by running the test and lint workflow locally:

```bash
# Run the full Python test suite (backend + simulation logic)
pytest

# Lint the core math helpers, plant verification script, and poker regression tests
ruff check core/math_utils.py scripts/verify_plants_no_metabolic_cost.py tests/test_static_vs_fish_comparison.py tests/test_vector2.py
```

The `scripts/verify_plants_no_metabolic_cost.py` helper can also be used to spot-check plant energy behavior without launching the full UI:

```bash
python scripts/verify_plants_no_metabolic_cost.py  # Prints energy every 10 frames for a sample plant
```

### AI Code Evolution Workflow

**Automatically improve fish behaviors using AI!** The simulation now includes an **AI Code Evolution Agent** that analyzes simulation data and generates algorithm improvements.

```bash
# Step 1: Run simulation and export stats
python main.py --headless --max-frames 10000 --export-stats results.json

# Step 2: Set up your API key (Claude or GPT-4)
export ANTHROPIC_API_KEY="sk-ant-..."
# OR
export OPENAI_API_KEY="sk-..."

# Step 3: Run the AI agent to improve worst performer
python scripts/ai_code_evolution_agent.py results.json --provider anthropic

# Step 4: Review changes
git diff HEAD~1

# Step 5: Push and create PR
git push -u origin <branch-name>
```

**What the AI agent does:**
- ✅ Identifies the worst performing algorithm (lowest reproduction rate)
- ✅ Analyzes why it's failing (starvation, predation, etc.)
- ✅ Reads the source code from the algorithm registry
- ✅ Generates improved code using Claude/GPT-4
- ✅ Creates a git branch with descriptive commit message
- ✅ Ready for human review and testing before merge

**Example result**: FreezeResponse improved from 0% → 100% reproduction rate!

See `docs/archive/2025-12-cleanup/AI_CODE_EVOLUTION_WORKFLOW.md` for the archived guide and
`docs/archive/2025-12-cleanup/PROOF_OF_AI_IMPROVEMENT.md` for the archived real-world example.

## Project Structure

```
tank/
├── main.py                  # CLI entry point (web or headless)
├── backend/                 # FastAPI app + WebSocket bridge
│   ├── main.py              # API and WebSocket server
│   ├── simulation_runner.py # Threaded simulation runner for the UI
│   ├── state_payloads.py    # Pydantic models for WebSocket state
│   └── models.py            # Pydantic schemas shared with the frontend
├── frontend/                # React + Vite frontend (npm run dev)
│   └── src/                 # Components, hooks, rendering utilities
├── core/                    # Shared simulation logic
│   ├── tank_world.py        # Simulation wrapper with config + RNG
│   ├── simulation_engine.py # Headless engine used by both modes
│   ├── entities/            # Entity classes (modular structure)
│   │   ├── fish.py          # Fish entity with component system
│   │   ├── plant.py         # L-system fractal plants
│   │   ├── resources.py     # Food, Plant, PlantNectar, Castle
│   │   ├── predators.py     # Crab entity
│   │   └── base.py          # Base Agent class
│   ├── fish/                # Fish component system
│   │   ├── energy_component.py
│   │   ├── lifecycle_component.py
│   │   ├── reproduction_component.py
│   │   └── poker_stats_component.py
│   ├── poker/               # Poker game system (organized package)
│   │   ├── core/            # Card, Hand, PokerEngine
│   │   ├── evaluation/      # Hand evaluation logic
│   │   └── strategy/        # AI poker strategies
│   ├── algorithms/          # Behavior algorithm library (58 strategies)
│   ├── genetics/    # Fish/plant genome, traits, inheritance
│   ├── plant_poker.py       # Plant vs fish poker games
│   ├── root_spots.py        # Plant anchor point management
│   ├── ecosystem.py         # Population tracking & statistics
│   ├── environment.py       # Spatial queries & collision detection
│   ├── time_system.py       # Day/night cycle management
│   └── constants.py         # Configuration parameters
├── scripts/                 # Automation scripts (AI code evolution, demos)
├── tests/                   # Test suite (determinism, integration)
├── docs/                    # Architecture + feature documentation
├── BEHAVIOR_DEVELOPMENT_GUIDE.md # Guide for creating behaviors
├── EVOLUTION_EXAMPLE.md     # Example evolution scenarios
├── QUICK_REFERENCE.md       # Quick command reference
└── README.md                # This file
```

## Web UI Controls

- **Add Food** button - Drop food into the tank
- **Pause/Resume** button - Pause or resume the simulation
- **Reset** button - Reset the simulation to initial state

## Configuration

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
POKER_HOUSE_CUT_PERCENTAGE = 10  # House cut for fish-vs-fish games (8-25% scaled by winner size)
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

## Ecosystem Dynamics Observed

### Sustainable Population
- **Population**: Stable at 7-15 fish with balanced predation
- **Birth rate**: ~10 births per 90 seconds
- **Generation transitions**: Continuous evolution across generations
- **Energy flow**: Environment → Fractal Plants → Nectar → Fish → Predators

### Algorithmic Evolution in Action
- **Algorithm diversity**: Population develops mix of strategies over time
- **Trait selection**: Better algorithms = more offspring
- **Parameter optimization**: Algorithm parameters fine-tune through mutation
- **Emergent strategies**: Fish discover optimal foraging and survival patterns
- **Performance tracking**: Stats export shows which algorithms dominate

### Poker Economy
- **Energy redistribution**: Poker transfers energy between fish and plants
- **Fitness signaling**: Better poker players accumulate more energy
- **Risk/reward**: Fish must balance poker with survival needs
- **Energy accounting details**: See `docs/archive/2025-12-cleanup/ENERGY_ACCOUNTING.md` for reconciliation + house cut attribution rules

### Plant Ecosystem
- **Fractal growth**: Plants grow from root spots using L-system genetics
- **Nectar production**: Plants produce floral nectar when energy threshold reached
- **Plant poker**: Fish can challenge plants to poker for energy rewards
- **Visual diversity**: Each plant has unique branch angles, colors, and patterns

### Population Dynamics
- **Carrying capacity**: Max 100 fish prevents overpopulation
- **Birth-death balance**: Sustainable with fractal plants producing nectar
- **Predator-prey cycles**: Crab population affects fish numbers
- **Starvation**: Rare with proper plant density

## Genetics & Evolution

### Heritable Traits
- **Physical traits**: Speed, size, vision range, metabolism, max energy
- **Visual traits**: Body shape, fin size, tail size, color pattern, pattern intensity
- **Behavior algorithm**: One of 58 parametrizable algorithms (inherited from parent)
- **Algorithm parameters**: Tunable values that control algorithm behavior
- **Mate preferences**: Preferred mate trait values (size, color, template, fins, body aspect, eye size, pattern type) and a preference for high pattern intensity

### Mutation
- **Trait mutations**: Small random variations in physical traits during reproduction
- **Preference mutations**: Mate preference targets drift over generations
- **Parameter tuning**: Algorithm parameters mutate slightly to explore nearby strategies
- **Algorithm switching**: Rare mutations can change to a completely different algorithm
- **Visual variations**: Color and shape traits evolve independently

### Natural Selection
- **Survival pressure**: Fish with better-adapted genetics survive longer
- **Reproductive success**: Better algorithms reproduce more, spreading through population
- **Competition**: Limited food creates selection pressure for efficient foraging
- **Generational evolution**: Population average fitness improves over time
- **Algorithm diversity**: Multiple successful strategies can coexist

## Testing

```bash
# Run all tests
pytest tests/

# Run specific test
python tests/test_simulation.py

# Test determinism
python tests/test_parity.py

# Run static analysis (import order, safety, style)
ruff check

# Format code
black .
```

## Educational Value

This simulation demonstrates:
- **Genetics & Heredity**: Mendelian inheritance with mutations
- **Natural Selection**: Survival of the fittest in action
- **Algorithmic Evolution**: Genetic algorithms with parametrizable behaviors
- **L-System Fractals**: Procedural plant generation using Lindenmayer systems
- **Predator-Prey Dynamics**: Balanced hunting and evasion
- **Population Dynamics**: Carrying capacity, birth/death rates
- **Energy Flow**: Producers (fractal plants) → Nectar → Consumers (fish) → Predators
- **Emergent Behavior**: Complex ecosystem from simple rules
- **Evolutionary Computation**: Parameter optimization through natural selection
- **Game Theory**: Poker interactions and strategic play (fish vs fish, fish vs plant)
- **Interpretable AI**: Clear, debuggable algorithm behaviors vs black-box approaches
- **Data Science**: LLM-friendly stat exports for AI-assisted analysis

## Recent Improvements & Future Enhancements

Recently Completed: ✅
- [✅] **Fractal Plants with L-System Genetics** - Procedurally generated plants with genetic evolution!
- [✅] **Plant Nectar System** - Plants produce floral nectar food with unique patterns
- [✅] **Plant Poker** - Fish can play poker against plants for energy rewards
- [✅] **Root Spot System** - Plants anchor to fixed positions at tank bottom
- [✅] **Evolving Poker Strategies** - Genome-based poker aggression that evolves across generations!
- [✅] **8 Poker Behavior Algorithms** - Strategist, Bluffer, Conservative, and more poker strategies
- [✅] **AI Code Evolution Agent** - Automated algorithm improvement using Claude/GPT-4!
- [✅] **Algorithm Registry** - Source mapping for AI-driven code improvements
- [✅] 58 parametrizable behavior algorithms
- [✅] TankWorld class for clean simulation management
- [✅] LLM-friendly JSON stats export with source file mapping
- [✅] Comprehensive behavior evolution tracking
- [✅] Predator-prey balance improvements
- [✅] Headless mode (10-300x faster)
- [✅] Deterministic seeding for reproducibility
- [✅] React-based web UI
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

## Architecture

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
  - Modular entity system (Fish, Plant, Crab, Food, PlantNectar)

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

## License

This project is open source. Feel free to modify and extend!

## Credits

Built with:
- **Python 3.8+**: Core simulation language
- **React + TypeScript**: Frontend framework with type safety
- **FastAPI**: Modern backend API framework
- **NumPy**: Numerical computations
- **HTML5 Canvas**: Real-time visualization
- **WebSocket**: Real-time client-server communication
- **Uvicorn**: High-performance ASGI server
- **Love for ALife**: Inspired by Conway's Life, Tierra, and evolutionary algorithms

## Documentation

**Canonical docs** (these are maintained and up-to-date):
- **[docs/VISION.md](docs/VISION.md)**: Long-term goals and the two-layer evolution paradigm
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**: Technical architecture and module layout
- **[docs/POKER_EVOLUTION_EXPERIMENT.md](docs/POKER_EVOLUTION_EXPERIMENT.md)**: Run the poker evolution experiment and read results
- **[BEHAVIOR_DEVELOPMENT_GUIDE.md](BEHAVIOR_DEVELOPMENT_GUIDE.md)**: How to create and extend behavior algorithms
- **[SETUP.md](SETUP.md)**: Development environment setup
- **[docs/adr/](docs/adr/)**: Architecture Decision Records

> **Note**: Historical analysis docs have been archived to `docs/archive/`.

---

## Contributing to the Framework

Tank World is open source and welcomes contributions:
- **Run simulations** and share performance data
- **Review AI-proposed changes** to algorithms
- **Extend the algorithm library** with new behaviors
- **Improve the visualization** system
- **Propose research directions** and experiments

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

*The fish tank is just the beginning. The goal is a self-improving Alife research framework—and we're building it in the open.*
