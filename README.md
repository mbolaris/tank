# Tank World

**Self-evolving artificial life where Git is the genome.**

Tank World is an open-source research framework where AI agents autonomously conduct artificial life experiments and commit their improvements back to the codebase. The simulation runs, collects data, an AI analyzes the results, improves the underlying algorithms, and opens a pull request. CI validates the improvement. If it passes, the change merges and becomes the new baseline for the next cycle.

The result: a continuously improving evolutionary system where **PRs are mutations, CI is natural selection, and Git history is the phylogenetic tree**.

> **[Full Vision](docs/VISION.md)** | **[Architecture](docs/ARCHITECTURE.md)** | **[Agent Guide](AGENTS.md)** | **[Roadmap](docs/ROADMAP.md)**

---

## Why This Matters

Most AI-assisted development treats the AI as a tool that responds to human requests. Tank World inverts this: the AI is the primary researcher, running experiments 24/7, and the human reviews the results. The framework is designed so that:

- **AI agents discover improvements** by analyzing simulation data and proposing code changes
- **Benchmarks enforce rigor** with deterministic seeds and reproducible results
- **CI gates prevent regressions** automatically before any merge
- **Every merged PR raises the floor** for the next agent session

This creates compounding returns. Each improvement is inherited by future agents who build on top of it. Over time, the system gets better at getting better.

---

## Three-Layer Evolution

Tank World is not "a sim with evolution." It is an **evolution engine whose own development process is part of the evolutionary loop**.

### Layer 0: In-World Evolution

Fish compete for survival using 58 parametrizable behavior algorithms. Natural selection optimizes parameters over generations. Better strategies mean more reproduction and longer survival.

**Output**: Champion genomes, performance telemetry, population dynamics data.

### Layer 1: AI-Driven Code Evolution

AI agents run deterministic benchmarks, compare results against the Best Known Solutions registry, and propose improvements via pull requests. CI validates the improvement before merge.

**Output**: Better algorithms, tuned parameters, new behavior strategies.

### Layer 2: Meta-Evolution

AI agents improve the benchmarks, fitness functions, agent instructions, and CI workflows that Layer 1 uses. This is evolution of the evolutionary process itself.

**Output**: Better ways of discovering improvements.

**The loop**: Run Benchmarks -> Compare vs BKS -> Open PR -> CI Validates -> Merge -> Future Agents Inherit

---

## What You See

A fish tank ecosystem with real evolutionary dynamics:

- **58 behavior algorithms** across food seeking, predator avoidance, schooling, energy management, territory, and poker strategies
- **Predator-prey dynamics** with crabs hunting fish
- **Fractal L-system plants** with genetic evolution and nectar production
- **Fish poker** where fish play Texas Hold'em against each other and plants for energy
- **Day/night cycles** affecting behavior and visibility
- **Genetic inheritance** of physical traits, visual traits, behavior algorithms, and mate preferences
- **Real-time web UI** built with React + FastAPI + WebSocket, rendering at 30 FPS

The visualization is deliberately engaging. Entertainment drives participation: if people enjoy watching their tank, they'll run longer experiments and contribute more compute.

### AI Oceanographer (Planned)

A future narration layer will explain what's happening in plain language, like an AI Jacques Cousteau providing commentary on the evolutionary dynamics unfolding in your tank.

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node 18+ (for the React frontend)

### Install

```bash
# Clone
git clone https://github.com/mbolaris/tank.git
cd tank

# Python setup
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .\.venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -e .[dev]

# Frontend setup
cd frontend && npm install && cd ..
```

### Run the Web UI

```bash
# Terminal 1: Backend
python main.py

# Terminal 2: Frontend
cd frontend && npm run dev

# Open http://localhost:3000
```

### Run Headless (10-300x Faster)

```bash
# Quick test
python main.py --headless --max-frames 5000 --seed 42

# Full experiment with stats export
python main.py --headless --max-frames 30000 --export-stats results.json --seed 42

# Run a benchmark
python tools/run_bench.py benchmarks/tank/survival_5k.py --seed 42
```

See [SETUP.md](SETUP.md) for detailed setup instructions and troubleshooting.

---

## The Evolution Loop

This is the core workflow that makes Tank World a self-improving system:

```
1. RUN benchmark with deterministic seed
2. COMPARE results against Best Known Solutions registry
3. IMPROVE code based on data analysis
4. VALIDATE with tests and benchmarks
5. OPEN PR with reproducible evidence
6. CI CONFIRMS the improvement
7. MERGE raises the baseline for all future agents
8. REPEAT
```

### Best Known Solutions (BKS) Registry

The repository maintains a formal registry of champion solutions:

```
benchmarks/          # Evaluation harnesses (deterministic, reproducible)
  tank/              # Tank world benchmarks
  soccer/            # Soccer mode benchmarks
champions/           # Best-known solutions per benchmark
  tank/              # Current tank champions with scores, genomes, repro commands
  soccer/            # Current soccer champions
```

Each champion entry includes the score, algorithm, genome, Git commit, seed, and exact reproduction command. Anyone can verify any claimed improvement.

### Evolutionary PR Protocol

When you discover an improvement (human or AI):

1. Run the benchmark: `python tools/run_bench.py benchmarks/tank/survival_5k.py --seed 42`
2. Compare vs champion: `python tools/validate_improvement.py results.json champions/tank/survival_5k.json`
3. If better, update the champion file and open a PR with evidence
4. CI re-runs the benchmark and confirms the score before merge

See [docs/EVO_CONTRIBUTING.md](docs/EVO_CONTRIBUTING.md) for the complete protocol.

---

## AI Code Evolution

AI agents can autonomously improve the simulation:

```bash
# 1. Run simulation and export data
python main.py --headless --max-frames 30000 --export-stats results.json --seed 42

# 2. AI agent analyzes results, identifies underperformers, and improves code
python scripts/ai_code_evolution_agent.py results.json --provider anthropic --validate

# 3. Run AI tournament to evaluate poker strategies
python scripts/run_ai_tournament.py --write-back
```

The AI agent reads simulation data, identifies the worst-performing algorithms, reads their source code, implements improvements, validates with benchmarks, and creates a Git branch with the changes. See [AGENTS.md](AGENTS.md) for the complete AI agent guide.

---

## Agentic Development with Claude Code

Tank World is designed for AI-first development. The repository includes infrastructure for productive agentic sessions:

- **[CLAUDE.md](CLAUDE.md)**: Project intelligence file loaded automatically by Claude Code
- **[AGENTS.md](AGENTS.md)**: Comprehensive guide for AI agents entering the evolution loop
- **Pre-commit hooks**: Automated formatting, linting, and type checking
- **Deterministic benchmarks**: Reproducible evaluation with fixed seeds
- **CI validation**: Automated verification of all improvements

To start an agentic development session:

```bash
# Install dev tools and hooks
pip install -e .[dev]
pre-commit install

# Run baseline to understand current state
python main.py --headless --max-frames 30000 --export-stats results.json --seed 42

# Run benchmarks
python tools/run_bench.py benchmarks/tank/survival_5k.py --seed 42

# Make improvements, validate, commit
pytest -m "not slow and not integration"
pre-commit run --all-files
```

---

## Architecture

Tank World uses a clean, modular architecture designed for extensibility:

```
tank/
|-- main.py                  # CLI entry point (web or headless)
|-- backend/                 # FastAPI + WebSocket server
|-- core/                    # Pure Python simulation engine
|   |-- algorithms/          # 58 behavior algorithms (composable library)
|   |-- worlds/              # Multi-world backend (Tank, Petri, Soccer)
|   |-- modes/               # Game rulesets (energy models, scoring)
|   |-- agents/components/   # Reusable agent building blocks
|   |-- entities/            # Fish, Plant, Crab, Food, PlantNectar
|   |-- poker/               # Full poker engine with evolving strategies
|   |-- genetics/            # Genome, traits, inheritance
|   |-- simulation/          # Engine orchestration
|   `-- config/              # Tunable parameters
|-- frontend/                # React 19 + TypeScript + Vite
|-- tests/                   # 60+ test files (smoke, core, integration)
|-- benchmarks/              # Deterministic evaluation harnesses
|-- champions/               # Best Known Solutions registry
|-- scripts/                 # AI evolution agent, tournaments, automation
`-- tools/                   # Benchmark runner, validation, dev utilities
```

**Key design decisions**:
- **Protocol-based design** with dependency injection for testability
- **Phase-based execution** for deterministic, reproducible simulation
- **Component composition** for reusable agent building blocks
- **Multi-world backend** enabling different world types (Tank, Petri, Soccer)
- **Interpretable algorithms** over black-box neural networks (behaviors are debuggable)

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full technical deep-dive and [docs/adr/](docs/adr/) for architecture decision records.

---

## Testing & Code Quality

```bash
# Quick gate (what CI runs first)
pytest -m "not slow and not integration"

# Full test suite
pytest

# Formatting and linting
black core/ tests/ tools/ backend/
ruff check --fix core/ tests/ tools/

# Pre-commit (runs all checks)
pre-commit run --all-files

# Benchmark determinism verification
python tools/run_bench.py benchmarks/tank/survival_5k.py --seed 42 --verify-determinism
```

CI runs 5 parallel jobs: fast-gate (core tests + linting), integration tests, headless smoke test, frontend build/lint/test, and nightly full suite.

---

## Ecosystem Dynamics

### What Evolves

| Domain | Mechanism | Example |
|--------|-----------|---------|
| Algorithm parameters | In-world natural selection | `GreedyFoodSeeker` tunes detection radius over generations |
| Algorithm prevalence | Differential reproduction | `AmbushFeeder` outcompetes `PanicFlee` in low-predator environments |
| Physical traits | Genetic inheritance + mutation | Speed, size, vision range, metabolism |
| Poker strategies | Energy stakes selection | Aggressive bluffers vs conservative folders |
| Visual traits | Mate preference evolution | Color patterns, fin sizes, body shapes |
| Code itself | AI-driven PR cycle | Agent improves `MirrorMover` with food-seeking fallback |

### Energy Flow

```
Environment -> Fractal Plants -> Nectar -> Fish -> Predators (Crabs)
                                   |
                              Poker Games (energy redistribution)
```

### Population Dynamics

- Stable population at 7-15 fish with balanced predation
- Day/night cycles affecting behavior
- Multiple successful strategies coexisting
- Carrying capacity prevents overpopulation
- Algorithm diversity maintained through mutation

---

## Project Status & Roadmap

**Current**: Phase 1 (Evolution Loop MVP) - establishing BKS registry, evolutionary PR protocol, and CI validation.

| Phase | Goal | Status |
|-------|------|--------|
| 0 | Foundation (58 algorithms, headless mode, web UI, basic AI evolution) | Complete |
| 1 | Evolution Loop MVP (BKS registry, evolutionary PRs, CI validation) | In Progress |
| 2 | Closed-loop automation (24/7 AI improvement cycles) | Planned |
| 3 | Meta-evolution (AI improves its own instructions and benchmarks) | Planned |
| 4 | Research platform (publishable ALife findings) | Planned |
| 5 | Distributed compute (entertainment-driven participation) | Planned |
| 6 | Evolving visualization (AI evolves how research is presented) | Planned |

See [docs/ROADMAP.md](docs/ROADMAP.md) for detailed milestones.

---

## Contributing

Tank World welcomes contributions from humans and AI agents:

- **Run simulations** and share performance data
- **Improve algorithms** in `core/algorithms/` and validate with benchmarks
- **Review AI-proposed changes** to maintain quality
- **Extend the benchmark suite** with new evaluation harnesses
- **Improve the framework** (visualization, tooling, documentation)

See [docs/EVO_CONTRIBUTING.md](docs/EVO_CONTRIBUTING.md) for the evolutionary PR protocol.

---

## Documentation

| Document | Purpose |
|----------|---------|
| [CLAUDE.md](CLAUDE.md) | Claude Code project intelligence (auto-loaded) |
| [AGENTS.md](AGENTS.md) | AI agent guide for entering the evolution loop |
| [SETUP.md](SETUP.md) | Development environment setup |
| [docs/VISION.md](docs/VISION.md) | Long-term vision and three-layer evolution paradigm |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Development roadmap and milestones |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Technical architecture deep-dive |
| [docs/EVO_CONTRIBUTING.md](docs/EVO_CONTRIBUTING.md) | Evolutionary PR protocol |
| [docs/BEHAVIOR_DEVELOPMENT_GUIDE.md](docs/BEHAVIOR_DEVELOPMENT_GUIDE.md) | Creating new behavior algorithms |
| [docs/INDEX.md](docs/INDEX.md) | Complete documentation index |

---

## Credits

Built with Python, React, TypeScript, FastAPI, NumPy, and a deep appreciation for Conway's Life, Tierra, Avida, and the ALife research tradition.

## License

This project is open source under the [MIT License](LICENSE).

---

*The fish tank is just the surface. Underneath it, Git is evolving.*
