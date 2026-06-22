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
# Run before coding (under 30 seconds)
python tools/smoke_gate.py

# Run before committing locally (under 90 seconds, smoke gate + curated checks)
python tools/agent_gate.py

# Run before PR (smoke gate + broad non-slow tests)
python tools/fast_gate.py

# Run full validation only for nightly or explicit maintainer review
python tools/full_gate.py

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
    agents/components/       # Shared agent state components (LifecycleComponent, ReproductionComponent)
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
  tools/                     # run_bench.py, validate_improvement.py, demo.py
  docs/                      # Architecture, vision, guides, ADRs
```

## Code Conventions

- **Python 3.10+**: Modern type hints (`X | Y`, `list[str]`) used natively
- **Formatting**: black (100 char line length), isort (black profile)
- **Linting**: ruff with select rules (see pyproject.toml)
- **Type checking**: mypy on core/ via `python -m mypy core/`
- **Tests**: pytest with markers: `slow`, `integration`, `manual`, `core`
- **Line length**: 100 characters (both black and ruff)
- **No __pycache__**: Pre-commit hook prevents committing compiled artifacts

## Architecture Principles

- **Protocol-based design**: Interfaces defined as Python Protocols for loose coupling
- **Phase-based execution**: Deterministic phases (perception -> decision -> action -> resolution)
- **Component composition**: Agents own discrete concerns via components (energy, lifecycle, reproduction, skill-game); Fish delegates behavior to a `BehaviorExecutor` + composable behavior (see ADR-009)
- **Multi-world backend**: WorldRegistry factory creates world-specific backends
- **Interpretable algorithms**: Explicit behavior strategies, not black-box neural networks
- **Determinism is non-negotiable**: All benchmarks use fixed seeds; simulations are reproducible

## Key Design Patterns

- `core/worlds/registry.py` - WorldRegistry factory pattern
- `core/worlds/interfaces.py` - MultiAgentWorldBackend protocol
- `core/simulation/engine.py` - Main simulation engine (phase-based)
- `core/modes/rulesets.py` - Game rule encapsulation
- `core/algorithms/composable/` - Composable behavior library (58 strategies)
- `core/agents/components/` - Shared agent state components (lifecycle, reproduction); Fish composes these plus `EnergyComponent` and delegates behavior to `BehaviorExecutor` (see ADR-004, ADR-009)

## Validation Pipeline

Local validation tiers:

1. **Smoke Gate**: `python tools/smoke_gate.py` before coding
2. **Agent Gate**: `python tools/agent_gate.py` before local commit
3. **Fast Gate**: `python tools/fast_gate.py` before PR
4. **Full Gate**: `python tools/full_gate.py` only for maintainers/nightly/full validation

Public CI jobs are named `smoke-gate`, `fast-gate`, `frontend-ci`, and
`nightly-full` in `ci.yml`, plus `verify-champions` and `benchmark-gate` in
`bench.yml`. Benchmark CI verifies champions and runs full determinism checks
nightly or when a maintainer dispatches it explicitly.

## Working on Improvements

The standard evolution loop:

1. **Smoke Gate**: Run `python tools/smoke_gate.py` before coding
2. **Baseline**: Run `python main.py --headless --max-frames 30000 --export-stats results.json --seed 42`
3. **Evaluate**: Check `results.json` for underperforming algorithms (high starvation rate, low reproduction)
4. **Improve**: Modify code in `core/algorithms/` or `core/config/`
5. **Validate**: Run `python tools/agent_gate.py` before local commit, and `python tools/fast_gate.py` before PR
6. **Benchmark**: Run full benchmarks only after a candidate improvement exists
7. **Compare**: Compare candidate results against the `champions/` registry
8. **Commit**: Clear message with metrics, reproduction command, and evidence

*Note: Never claim benchmark improvement without reproduction command, seed,
score, and metadata. Layer 2 changes to benchmarks, CI, scoring, prompts, gates,
or champion metadata must be separate from Layer 1 algorithm improvements.*

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
- **Ball pursuit pre-empts food seeking**: in `core/movement_strategy.py`, soccer-ball
  pursuit (priority 2) runs before the composable behavior's food pursuit (priority 4),
  and the ball exists even in benchmark configs (`tank_practice_enabled` defaults to True
  even when `soccer_enabled` is False). When diagnosing starvation, first check whether
  fish are clustering around the ball at tank center instead of foraging
  (`scripts/diagnose_food_seeking.py` helps).
- **Tank benchmark population means fish**: `avg_pop`, `mean_population`, and
  `final_population` are fish population fields. `final_total_entities` includes
  food and other world objects and is diagnostic only, never the population score.
- **Reproduction is funded by overflow energy**: fish bank energy gained above
  `max_energy` and spend it on offspring. Changes that burn the surplus energy of
  well-fed fish (e.g. ball play, poker) directly suppress birth rate and generation
  turnover, which the ecosystem_health benchmark penalizes. Corollary: "surplus"
  means energy above `max_energy`, not merely above the 40% safe threshold - a fish
  below max is still climbing toward its next birth.
- **ecosystem_health scores are trajectory-sensitive on a single seed**: the score
  is linear in `max_generation` (a small integer), so any behavior change that
  perturbs trajectories can swing the seed-42 score several percent up or down for
  reasons unrelated to its average effect. Before trusting a candidate, run it on a
  few extra seeds (e.g. 7, 123) against the same-seed baseline. A real improvement
  wins or stays neutral across seeds; a single-seed win that regresses elsewhere is
  likely noise. Use `scripts/diagnose_evolution.py` to confirm selection is actually
  occurring (trait drift), not just generation churn.
- Run `pre-commit run --all-files` before committing (or `pre-commit install` to auto-run)
- CI uses Python 3.10; `requires-python = ">=3.10"` in pyproject.toml
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
