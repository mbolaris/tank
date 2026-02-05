# Tank World

**A framework for AI-driven automated Artificial Life research.**

Tank World is an open-source platform where AI agents conduct Alife research autonomously. The simulation runs, collects data, and then an AI agent analyzes results and improves the underlying algorithms—creating a continuous, closed-loop research cycle that runs without human intervention.

The fish tank visualization is just the beginning. It makes the research **entertaining enough to watch**, which matters because entertaining simulations can drive distributed compute contributions. In future versions, the AI will evolve the visualizations themselves to maximize engagement.

> **See [docs/VISION.md](docs/VISION.md) for the full project vision and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for technical details.**

---

## The Core Idea: Three-Layer Evolution

Tank World is not just "a sim with evolution"—it's an **evolution engine whose own development process is part of the evolutionary loop**. Git becomes the heredity mechanism.

### Layer 0: In-World Evolution (Inside Simulations)

Traditional evolutionary computation. Fish compete for survival using behavior algorithms:
- 58 parametrizable behavior strategies across 6 categories
- Natural selection optimizes algorithm parameters over generations
- Better strategies = more reproduction and survival
- **Output**: Champion genomes + performance telemetry

### Layer 1: Experiment Automation (Evolving the Search)

AI agents run benchmarks, discover improvements, and propose changes via PRs:
- Run deterministic benchmarks with fixed seeds
- Compare results against Best Known Solutions (BKS) registry
- Open PRs with improved algorithms + reproducible artifacts
- CI validates improvements before merge
- **Output**: Better algorithms, evaluators, mutation operators

### Layer 2: Meta-Evolution (Evolving the Toolkit)

AI agents improve the instructions, benchmarks, and workflows used by Layer 1:
- Evolve benchmark design (better fitness functions)
- Evolve agent instructions (better evolution workflows)
- Evolve CI gates (stronger validation)
- **Output**: Better "how we evolve" playbooks

**The loop**: Run Benchmarks → Compare vs BKS → Open PR → CI Validates → Merge → Future Agents Inherit

This is what makes Tank World different: **Git is the heredity mechanism. PRs are mutations, CI is selection, merged changes are offspring.**

---

## What Evolves Here?

Tank World evolves three things simultaneously:

1. **In-world policies** - Fish behavior algorithms and their parameters
2. **The evaluation harness** - Benchmarks, fitness functions, curriculum design
3. **The development toolkit** - Agent instructions, workflows, and CI gates

Evolution happens through **evolutionary PRs** where improvements are validated against the Best Known Solutions (BKS) registry before merge.

## Best Known Solutions (BKS) Registry

Tank World maintains a **formal registry of best-known solutions** for reproducible benchmarks:

### Structure

```
tank/
├── benchmarks/              # Evaluation harnesses
│   ├── tank/                # Tank world benchmarks
│   │   └── survival_5k.py   # 5k frame survival benchmark
│   └── soccer/              # Soccer world benchmarks
│       ├── training_3k.py
│       └── training_5k.py
├── champions/               # Best-known solutions
│   ├── tank/
│   │   └── survival_5k.json    # Current champion for survival
│   └── soccer/
│       ├── training_3k.json
│       └── training_5k.json
└── tools/
    └── run_bench.py         # Standard benchmark runner
```

### Champion Registry Format

Each champion file contains:
- **Score**: The fitness achieved (higher is better)
- **Algorithm**: The winning algorithm name and parameters
- **Genome**: Complete genome data for reproduction
- **Commit**: Git commit hash where this was achieved
- **Seed**: Deterministic seed for reproduction
- **Reproduction command**: Exact command to reproduce the result

### Why BKS Matters

- **Formal selection pressure**: No "this seems better"—only reproducible benchmark wins
- **Auditable lineage**: Git history shows evolutionary progression
- **Reproducible science**: Anyone can re-run and verify claims
- **Future inheritance**: Each champion becomes the baseline for future improvements

## Evolutionary PR Protocol

When you discover an improvement (human or AI agent):

### Requirements

**Must include:**
- ✅ Benchmark results showing improvement over current BKS
- ✅ Updated champion registry entry if claiming a new record
- ✅ Reproduction command that works with deterministic seeds
- ✅ Clear explanation of what changed and why it's better

**Must pass:**
- ✅ CI re-runs the benchmark and confirms the score
- ✅ No regressions on other benchmarks
- ✅ Code review (human-in-the-loop for Layer 2 changes)

**If merged:**
- The new champion becomes the baseline for future PRs
- Future agents inherit this improvement
- Git history shows the evolutionary lineage

### Example Workflow

```bash
# 1. Run benchmark
python tools/run_bench.py benchmarks/tank/survival_5k.py --seed 42

# 2. Compare against current BKS
python tools/validate_improvement.py results.json champions/tank/survival_5k.json

# 3. If better, update champion and open PR
git checkout -b improve/survival-energy-conserver
# ... update champions/tank/survival_5k.json
git commit -m "Improve survival benchmark: EnergyConserver optimization"
git push -u origin improve/survival-energy-conserver

# 4. CI validates and merges if confirmed
```

See [docs/EVO_CONTRIBUTING.md](docs/EVO_CONTRIBUTING.md) for complete protocol details.

---

## Long-Term Goals

Tank World aims to be **self-sustaining research infrastructure** where the development process itself is part of the evolutionary loop:

1. **Evolution Loop MVP** (Current): Establish BKS registry + evolutionary PR protocol + CI validation
2. **Closed-loop research**: Fully automated improvement cycles running 24/7 with human code review
3. **Meta-evolution**: AI improves its own instructions, benchmarks, and workflows (Layer 2)
4. **Legitimate research platform**: ALife research with measurable results and publishable findings
5. **Distributed compute network**: Users contribute compute by running entertaining simulations
6. **Evolving visualization**: AI evolves not just behaviors but how research is presented

The ultimate vision: a research framework where **Git is the heredity mechanism**—running experiments produces improvements that get committed back to the repository, creating a continuous evolutionary loop at multiple levels (in-world, algorithms, and the evolution toolkit itself).

**Current status**: Phase 0 (Foundation) complete. Phase 1 (Evolution Loop MVP) in progress. See [docs/VISION.md](docs/VISION.md) and [docs/ROADMAP.md](docs/ROADMAP.md) for details.

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
- **Unified Hand Engine**: Shared hand-level engine powers heads-up, multiplayer, evaluation, and the human UI
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
tankworld
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

# Record a deterministic replay (JSONL) with per-step snapshot fingerprints
python main.py --headless --seed 42 --max-frames 500 --record run.replay.jsonl

# Record less frequently (fingerprint every 10 frames)
python main.py --headless --seed 42 --max-frames 2000 --record run.replay.jsonl --record-every 10

# Record mode switches at specific frames (tank↔petri)
python main.py --headless --seed 42 --max-frames 500 --record run.replay.jsonl --switch 200:petri --switch 400:tank

# Replay and verify fingerprints match (fails fast on first mismatch)
python main.py --headless --replay run.replay.jsonl
```

**Benefits of headless mode:**
- 10-300x faster than realtime
- Perfect for data collection and long simulations
- No display required
- Identical simulation behavior to web UI
- **LLM-friendly stats export**: Export comprehensive JSON data including algorithm performance, evolution trends, and population dynamics for AI-assisted analysis

See `docs/REPLAY.md` for the replay format and workflow.

## Code Quality & Testing

Keep changes safe by running the test and lint workflow locally:

```bash
# Quick gate (fast, portable collection)
pytest -m "not slow and not integration"

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

**Automatically improve fish behaviors using AI!** AI agents (like Claude, GPT, or similar) can analyze simulation data and directly improve algorithms.

```bash
# Step 1: Run simulation and export stats
python main.py --headless --max-frames 10000 --export-stats results.json --seed 42

# Step 2: AI analyzes results and identifies underperformers
# (The AI agent reads results.json and source code directly)

# Step 3: AI improves the worst-performing algorithm
# (Direct code edits to core/algorithms/)

# Step 4: Validate improvements
python tools/run_bench.py benchmarks/tank/survival_5k.py --seed 42

# Step 5: Push and create PR
git push -u origin <branch-name>
```

**What the AI agent does:**
- ✅ Identifies the worst performing algorithm (highest starvation rate)
- ✅ Analyzes why it's failing (e.g., no food-seeking fallback)
- ✅ Reads the source code and implements improvements
- ✅ Validates with tests and benchmarks
- ✅ Creates a git branch with descriptive commit message

**Example result**: MirrorMover improved with food-seeking behavior to reduce starvation!

See `AGENTS.md` for complete AI agent guide.

## Project Structure

```
tank/
|-- main.py                  # CLI entry point (web or headless)
|-- backend/                 # FastAPI app + WebSocket bridge
|   |-- main.py              # API and WebSocket server
|   |-- app_factory.py       # FastAPI application factory
|   |-- simulation_runner.py # Threaded simulation runner for the UI
|   |-- broadcast.py         # State broadcasting to WebSocket clients
|   |-- state_payloads.py    # Pydantic models for WebSocket state
|   |-- world_persistence.py # Save/load world state
|   |-- replay.py            # Deterministic replay system
|   |-- routers/             # API route handlers
|   `-- models.py            # Pydantic schemas shared with the frontend
|-- frontend/                # React + Vite frontend (npm run dev)
|   `-- src/                 # Components, hooks, rendering utilities
|-- core/                    # Pure Python simulation engine (no UI deps)
|   |-- world.py             # Abstract World interface for simulation
|   |-- agents/              # Reusable agent components
|   |   `-- components/      # PerceptionComponent, LocomotionComponent, FeedingComponent
|   |-- modes/               # Mode pack definitions and rulesets
|   |   |-- interfaces.py    # ModePack, ModePackDefinition protocols
|   |   |-- rulesets.py      # ModeRuleSet: TankRuleSet, PetriRuleSet, SoccerRuleSet
|   |   |-- tank.py          # Tank mode pack configuration
|   |   |-- petri.py         # Petri mode pack configuration
|   |   `-- soccer.py        # Soccer ruleset configuration (minigame)
|   |-- worlds/              # World backend implementations
|   |   |-- interfaces.py    # MultiAgentWorldBackend, StepResult
|   |   |-- registry.py      # WorldRegistry (factory for world backends)
|   |   |-- tank/            # Tank world backend + system pack
|   |   `-- petri/           # Petri world backend
|   |-- simulation/          # Engine orchestration + diagnostics
|   |   |-- engine.py        # Simulation engine used by both modes
|   |   |-- entity_manager.py
|   |   |-- system_registry.py
|   |   `-- diagnostics.py
|   |-- entities/            # Entity classes (modular structure)
|   |   |-- fish.py          # Fish entity with component system
|   |   |-- plant.py         # L-system fractal plants
|   |   |-- resources.py     # Food, PlantNectar, Castle
|   |   |-- predators.py     # Crab entity
|   |   |-- mixins/          # Entity mixins (energy, mortality, reproduction)
|   |   `-- base.py          # Entity base classes
|   |-- fish/                # Fish subsystem
|   |   |-- behavior_executor.py  # Behavior execution logic
|   |   |-- energy_state.py       # Energy state tracking
|   |   |-- poker_stats_component.py
|   |   `-- visual_geometry.py    # Visual trait geometry
|   |-- poker/               # Poker game system (organized package)
|   |   |-- core/            # Card, Hand, PokerEngine
|   |   |-- evaluation/      # Hand evaluation logic
|   |   |-- simulation/      # Shared hand engine + simulation adapters
|   |   `-- strategy/        # AI poker strategies
|   |-- algorithms/          # Behavior algorithm library (58 strategies)
|   |   |-- food_seeking/    # 14 food-seeking algorithms
|   |   |-- composable/      # Composable behavior sub-system
|   |   |-- energy_management.py
|   |   |-- predator_avoidance.py
|   |   |-- schooling.py
|   |   |-- territory.py
|   |   `-- poker.py
|   |-- genetics/            # Fish/plant genome, traits, inheritance
|   |-- systems/             # BaseSystem + system implementations
|   |-- config/              # Simulation configuration modules
|   |-- minigames/           # Soccer and other minigames
|   |-- spatial/             # Spatial queries & grid
|   |-- energy/              # Energy accounting subsystem
|   |-- evolution/           # Evolution logic
|   |-- telemetry/           # Telemetry and stats collection
|   |-- ecosystem.py         # Population tracking & statistics
|   |-- environment.py       # Spatial queries & collision detection
|   `-- time_system.py       # Day/night cycle management
|-- benchmarks/              # Deterministic benchmark harnesses
|-- champions/               # Best-known solutions registry
|-- solutions/               # Submitted poker solutions
|-- tools/                   # Benchmark runners & validators
|-- scripts/                 # Automation scripts (AI code evolution, analysis)
|-- tests/                   # Test suite (determinism, integration, smoke)
|-- docs/                    # Architecture + feature documentation (see docs/INDEX.md)
|-- SETUP.md                 # Development environment setup
|-- AGENTS.md                # AI agent contributor guide
`-- README.md                # This file
```


## Web UI Controls

- **Add Food** button - Drop food into the tank
- **Pause/Resume** button - Pause or resume the simulation
- **Reset** button - Reset the simulation to initial state

## Configuration

Simulation defaults live in `core/config/` and are aggregated in
`core/config/simulation_config.py` (`SimulationConfig`).

```python
# core/config/display.py
SCREEN_WIDTH = 1088
SCREEN_HEIGHT = 612
FRAME_RATE = 30

# core/config/food.py
AUTO_FOOD_SPAWN_RATE = 30  # 1 food per second at 30 FPS
AUTO_FOOD_ENABLED = True
AUTO_FOOD_ULTRA_LOW_ENERGY_THRESHOLD = 1500
AUTO_FOOD_LOW_ENERGY_THRESHOLD = 3500
AUTO_FOOD_HIGH_ENERGY_THRESHOLD_1 = 4500
AUTO_FOOD_HIGH_ENERGY_THRESHOLD_2 = 6500
```

Other notable config modules:
- `core/config/fish.py` (energy, lifecycle, reproduction tuning)
- `core/config/plants.py` (food/nectar production tuning)
- `core/config/poker.py` (poker event and benchmark settings)

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

# Run poker regression manual tests
# Bash/macOS:
python -m pytest tests/test_poker_*.py tests/test_texas_holdem_rules.py -m manual
# PowerShell:
$files = Get-ChildItem tests -Filter "test_poker_*.py"; python -m pytest $files tests/test_texas_holdem_rules.py -m manual

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
- [✅] **Multi-World Backend Architecture** - WorldRegistry + MultiAgentWorldBackend for Tank/Petri worlds
- [✅] **Mode RuleSet Abstraction** - TankRuleSet, PetriRuleSet, SoccerRuleSet with energy/scoring models
- [✅] **Agent Component System** - PerceptionComponent, LocomotionComponent, FeedingComponent for reuse
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
- [x] Save/load ecosystem states (implemented via `backend/world_persistence.py`)
- [x] Replay system for deterministic replay and verification (see `docs/REPLAY.md`)
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

- **Multi-World Backend** (`core/worlds/`): Domain-agnostic world abstraction
  - `MultiAgentWorldBackend` interface for Tank and Petri worlds
  - `WorldRegistry` factory for creating worlds from mode IDs
  - Each world type has its own backend adapter (e.g., `TankWorldBackendAdapter`)
  - Enables easy addition of new world types

- **Mode System** (`core/modes/`): Mode configuration and rules
  - `ModePack` defines mode configs, display names, and capabilities
  - `ModeRuleSet` encapsulates game rules (energy models, scoring, allowed actions)
  - Built-in modes: Tank (fish ecosystem), Petri (microbes), Soccer (minigame ruleset)

- **Agent Components** (`core/agents/components/`): Reusable agent building blocks
  - `PerceptionComponent` - memory queries, food/danger tracking
  - `LocomotionComponent` - movement, turn costs, boundary handling
  - `FeedingComponent` - bite size, food consumption
  - Same agents work across different world rules and render profiles (fish-style side view, microbe-style top-down view)

- **TankWorldBackendAdapter** (`core/worlds/tank/backend.py`): Tank simulation wrapper
  - Clean interface for configuration management
  - Random number generator (RNG) management for deterministic behavior
  - Unified API for both headless and web modes

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

**See [docs/INDEX.md](docs/INDEX.md) for a complete documentation index.**

**Canonical docs** (these are maintained and up-to-date):
- **[docs/VISION.md](docs/VISION.md)**: Long-term goals and the three-layer evolution paradigm
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**: Technical architecture and module layout
- **[docs/BEHAVIOR_DEVELOPMENT_GUIDE.md](docs/BEHAVIOR_DEVELOPMENT_GUIDE.md)**: How to create and extend behavior algorithms
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

See [docs/EVO_CONTRIBUTING.md](docs/EVO_CONTRIBUTING.md) for contribution guidelines.

---

*The fish tank is just the beginning. The goal is a self-improving Alife research framework—and we're building it in the open.*
