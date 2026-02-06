# CLAUDE.md - Tank World Project Intelligence

This file is automatically loaded by Claude Code at the start of every session. It provides the essential context needed to work effectively in this codebase.

## What Is This Project?

Tank World is a **self-evolving artificial life research framework**. Fish agents compete for survival in a simulated ecosystem using 58 parametrizable behavior algorithms. AI agents (like you) analyze simulation data, improve the algorithms, and commit changes back to the repository. Git is the heredity mechanism: PRs are mutations, CI is selection, merged changes are offspring.

The project operates at three layers:
- **Layer 0**: In-world evolution (fish evolve through natural selection inside simulations)
- **Layer 1**: AI code evolution (agents improve algorithms via benchmarks + PRs)
- **Layer 2**: Meta-evolution (agents improve the benchmarks, instructions, and workflows themselves)

## Quick Commands

```bash
# Run tests (fast gate - what CI checks first)
pytest -m "not slow and not integration"

# Run full test suite
pytest

# Run a benchmark
python tools/run_bench.py benchmarks/tank/survival_5k.py --seed 42

# Run headless simulation with stats export
python main.py --headless --max-frames 30000 --export-stats results.json --seed 42

# Format and lint
black core/ tests/ tools/ backend/ --config pyproject.toml
ruff check --fix core/ tests/ tools/ backend/

# Pre-commit (all checks at once)
pre-commit run --all-files

# Start web UI (two terminals)
python main.py                    # Backend on :8000
cd frontend && npm run dev        # Frontend on :3000

# Validate improvement against champion
python tools/validate_improvement.py results.json champions/tank/survival_5k.json
```

## Project Structure

```
tank/
  main.py                    # CLI entry (web or headless mode)
  backend/                   # FastAPI + WebSocket server
  core/                      # Pure Python simulation engine (no UI deps)
    algorithms/              # 58 behavior algorithms (composable library)
      composable/            # Main algorithm framework (definitions.py, behavior.py, actions.py)
    worlds/                  # Multi-world backend (Tank, Petri)
      tank/                  # Tank world implementation
      petri/                 # Petri dish implementation
    modes/                   # Game rulesets (TankRuleSet, PetriRuleSet, SoccerRuleSet)
    agents/components/       # Reusable: PerceptionComponent, LocomotionComponent, FeedingComponent
    entities/                # Fish, Plant, Crab, Food, PlantNectar, Castle
    poker/                   # Full poker engine (core/, evaluation/, simulation/, strategy/)
    genetics/                # Genome, traits, inheritance
    simulation/              # Engine orchestration, entity manager, system registry
    config/                  # All tunable parameters (fish.py, food.py, plants.py, poker.py)
    systems/                 # BaseSystem + system implementations
  frontend/                  # React 19 + TypeScript + Vite
  tests/                     # 60+ test files organized by category
    smoke/                   # Quick smoke tests
    core/                    # Core logic tests
    integration/             # Integration tests
  benchmarks/                # Deterministic evaluation harnesses
    tank/                    # survival_5k.py, etc.
    soccer/                  # training_5k.py, training_3k.py, etc.
  champions/                 # Best Known Solutions registry (JSON)
  scripts/                   # AI evolution agent, tournaments, automation
  tools/                     # run_bench.py, validate_improvement.py, mypy_gate.py
  docs/                      # Architecture, vision, guides, ADRs
```

## Code Conventions

- **Python 3.8+ compatible**: Use `from __future__ import annotations` for modern type hints
- **Formatting**: black (100 char line length), isort (black profile)
- **Linting**: ruff with select rules (see pyproject.toml)
- **Type checking**: mypy on core/ (baseline mode via tools/mypy_gate.py)
- **Tests**: pytest with markers: `slow`, `integration`, `manual`, `core`
- **Line length**: 100 characters (both black and ruff)
- **No __pycache__**: Pre-commit hook prevents committing compiled artifacts

## Architecture Principles

- **Protocol-based design**: Interfaces defined as Python Protocols for loose coupling
- **Phase-based execution**: Deterministic phases (perception -> decision -> action -> resolution)
- **Component composition**: Agents built from reusable components (perception, locomotion, feeding)
- **Multi-world backend**: WorldRegistry factory creates world-specific backends
- **Interpretable algorithms**: Explicit behavior strategies, not black-box neural networks
- **Determinism is non-negotiable**: All benchmarks use fixed seeds; simulations are reproducible

## Key Design Patterns

- `core/worlds/registry.py` - WorldRegistry factory pattern
- `core/worlds/interfaces.py` - MultiAgentWorldBackend protocol
- `core/simulation/engine.py` - Main simulation engine (phase-based)
- `core/modes/rulesets.py` - Game rule encapsulation
- `core/algorithms/composable/` - Composable behavior library (58 strategies)
- `core/agents/components/` - Component system for agent building blocks

## CI Pipeline

CI runs on push to main/master/develop and claude/** branches:

1. **fast-gate**: Core tests + smoke tests + black + ruff + mypy + soccer benchmark determinism
2. **integration-gate**: Tests marked `@pytest.mark.integration`
3. **test-headless**: Headless simulation smoke test
4. **frontend-ci**: npm install, lint, build, test
5. **nightly-full**: Full test suite (nightly or on 'full-test' label)

Benchmark CI (`bench.yml`): Verifies champions and runs determinism checks on PRs touching benchmarks/champions/core/tools.

## Working on Improvements

The standard evolution loop:

1. **Baseline**: Run `python main.py --headless --max-frames 30000 --export-stats results.json --seed 42`
2. **Evaluate**: Check `results.json` for underperforming algorithms (high starvation rate, low reproduction)
3. **Benchmark**: Run `python tools/run_bench.py benchmarks/tank/survival_5k.py --seed 42`
4. **Improve**: Modify code in `core/algorithms/` or `core/config/`
5. **Validate**: Run `pytest -m "not slow and not integration"` and `pre-commit run --all-files`
6. **Compare**: Run benchmark again and compare against `champions/` registry
7. **Commit**: Clear message with metrics, reproduction command, and evidence

### Key Files for Algorithm Improvements

- `core/algorithms/composable/definitions.py` - Algorithm parameter bounds
- `core/algorithms/composable/behavior.py` - Main execute logic
- `core/algorithms/composable/actions.py` - Sub-behavior implementations
- `core/config/fish.py` - Energy costs, thresholds, lifecycle
- `core/config/food.py` - Food detection, spawning rates
- `core/reproduction_service.py` - Emergency spawn logic

### Healthy Ecosystem Indicators

| Metric | Healthy | Warning |
|--------|---------|---------|
| Starvation deaths | <80% of all deaths | >95% = food-seeking broken |
| Population | >20 fish stable | Frequent emergency spawns = unstable |
| Generation rate | >5 per 10k frames | <3 = evolution too slow |
| Reproduction success | >120% | <100% = population declining |

## Common Gotchas

- Always use `--seed 42` for reproducible benchmarks
- Run `pre-commit run --all-files` before committing (or `pre-commit install` to auto-run)
- CI uses Python 3.10, not 3.8; but code must be 3.8-compatible
- Frontend is excluded from Python linting (separate ESLint config)
- The `TANK_ENFORCE_MUTATION_INVARIANTS=1` env var enables strict mutation checks in tests
- `PYTHONPATH=.` is set automatically by pytest config but may need manual setting for scripts

## Further Reading

- [AGENTS.md](AGENTS.md) - Detailed AI agent guide with evolution loop workflow
- [docs/VISION.md](docs/VISION.md) - Three-layer evolution paradigm and long-term goals
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Full technical architecture
- [docs/EVO_CONTRIBUTING.md](docs/EVO_CONTRIBUTING.md) - Evolutionary PR protocol
- [docs/BEHAVIOR_DEVELOPMENT_GUIDE.md](docs/BEHAVIOR_DEVELOPMENT_GUIDE.md) - Creating new algorithms
- [docs/ROADMAP.md](docs/ROADMAP.md) - Current priorities and milestones
