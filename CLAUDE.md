# CLAUDE.md - Tank World Project Intelligence

This file is automatically loaded by Claude Code at the start of every session. It provides the essential context needed to work effectively in this codebase.

## What Is This Project?

Tank World is a **self-evolving artificial life research framework**. Fish agents compete for survival in a simulated ecosystem using a composable behavior framework (see `core/algorithms/registry.py::ALL_ALGORITHMS` and [docs/ALGORITHM_CATALOG.md](docs/ALGORITHM_CATALOG.md)). AI agents (like you) analyze simulation data, improve the algorithms, and commit changes back to the repository. Git is the heredity mechanism: PRs are mutations, CI is selection, merged changes are offspring.

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
python tools/pre_pr_gate.py

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

# Study a running sim and post commentary to the UI's Board feed (/observe-sim)
python tools/evolution_report.py --url http://127.0.0.1:8000 --json   # observe (read-only)
python tools/post_commentary.py --url http://127.0.0.1:8000 \
    --text "Selection on pursuit_aggression: +12% over 40k frames" --topic ecosystem --severity insight --tags selection
python tools/post_commentary.py --read --topic ecosystem --limit 15   # read the feed back
python tools/post_commentary.py --react 3 --emoji 👍 --as claude      # react to a post
```

## Project Structure

```
tank/
  main.py                    # CLI entry (web or headless mode)
  backend/                   # FastAPI + WebSocket server
  core/                      # Pure Python simulation engine (no UI deps)
    algorithms/              # behavior algorithm library (composable + specialized)
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
- **Type checking**: `python -m mypy core/ backend/ tools/` — the scope CI's
  `mypy` job and `tools/agent_gate.py` both use. Checking only `core/` passes
  locally while CI fails on `tools/`.
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
- `core/algorithms/composable/` - Composable behavior library (see `core/algorithms/registry.py::ALL_ALGORITHMS` for current set)
- `core/agents/components/` - Shared agent state components (lifecycle, reproduction); Fish composes these plus `EnergyComponent` and delegates behavior to `BehaviorExecutor` (see ADR-004, ADR-009)

## Validation Pipeline

Local validation tiers:

1. **Smoke Gate**: `python tools/smoke_gate.py` before coding
2. **Agent Gate**: `python tools/agent_gate.py` before local commit
3. **Pre-PR Gate**: `python tools/pre_pr_gate.py` before PR
4. **Full Gate**: `python tools/full_gate.py` only for maintainers/nightly/full validation

Public CI jobs are named `smoke-gate`, `pre-pr-gate`, `frontend-ci`,
`security-audit`, and `nightly-full` in `ci.yml`, plus `verify-champions` and `benchmark-gate` in
`bench.yml`. Benchmark CI verifies champions and runs determinism checks on
every PR, plus nightly and on explicit maintainer dispatch.

*If your PR changes simulation behavior, `verify-champions` will fail — that is
the gate working. Re-baseline `champions/tank/*.json` in the same PR, using CI's
own scores (`gh workflow run bench.yml --ref master -f rebaseline_tank=true`,
then pull the `tank-champion-rebaseline` artifact). Never re-baseline a tank
champion from a local run: tank scores are not bit-identical across platforms.*

## Working on Improvements

The standard evolution loop:

1. **Smoke Gate**: Run `python tools/smoke_gate.py` before coding
2. **Baseline**: Run `python main.py --headless --max-frames 30000 --export-stats results.json --seed 42`
3. **Evaluate**: Check `results.json` for underperforming algorithms (high starvation rate, low reproduction)
4. **Improve**: Modify code in `core/algorithms/` or `core/config/`
5. **Validate**: Run `python tools/agent_gate.py` before local commit, and `python tools/pre_pr_gate.py` before PR
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
- `core/reproduction/reproduction_service.py` - Emergency spawn logic

### Healthy Ecosystem Indicators

| Metric | Healthy | Warning |
|--------|---------|---------|
| Starvation deaths | <80% of all deaths | >95% = food-seeking broken |
| Population | >20 fish stable | Frequent emergency spawns = unstable |
| Generation rate | >5 per 10k frames | <3 = evolution too slow |
| Reproduction success | >120% | <100% = population declining |

## Common Gotchas

- Always use `--seed 42` for reproducible benchmarks
- **The tank starved because fish could not spend their own savings.** A fish
  banks everything it gains above `max_energy` into an overflow reproduction
  bank, and that bank used to be spendable on offspring and on nothing else.
  Measured at the death site rather than inferred from the death mix
  (`python tools/measure_death_reserves.py benchmarks/tank/survival_5k.py
  --seeds 42,2,999`, artifacts in `research/starvation/`), **51% of seed 42's
  `survival_5k` starvation deaths were fish at exactly zero energy still
  holding a mean of 147 banked units** (29-32% on seeds 2 and 999) - 36,823
  energy foreclosed across the three, seed 42's 12,233 alone more than twice
  the tank's entire standing energy.
  `_draw_on_reserves` in `core/entities/mixins/energy_mixin.py` now lets a
  fish top back up to the starvation threshold out of its own bank before it
  dies. Starvation fell from 86-97% of deaths to 41-82%, and every sampled
  seed of `survival_5k` and the held-out evaluator improved. Note what it does
  *not* do: roughly as much banked energy is still destroyed at death, now at
  old age instead of mid-life, so "stop destroying energy at death" remains
  open ground.
- **Ball pursuit pre-empts food seeking, and it was never why the tank
  starved.** The ordering is real: in `core/movement_strategy.py` soccer-ball
  pursuit (priority 2) runs before the composable behavior's food pursuit
  (priority 4), and the ball exists even in benchmark configs
  (`tank_practice_enabled` defaults to True even when `soccer_enabled` is
  False). This entry used to say to check that first when diagnosing
  starvation. **Measured, it is a dead end**
  (`research/starvation/practice_ball_ablation.json`, reproduce with
  `tools/ablate_world_config.py benchmarks/tank/survival_5k.py --key
  tank_practice_enabled --off --seeds 42,2,999`): turning the ball off moved
  the starvation rate by at most two points and on seed 42 moved it the
  *wrong* way. The ball does cost something, but the cost lands on
  reproduction energy, not foraging.
- **Food supply is a thermostat, and it has a saturation point.**
  `FoodSpawningSystem._calculate_spawn_rate` is a closed loop on *total fish
  energy*: it triples the spawn rate below `AUTO_FOOD_LOW_ENERGY_THRESHOLD`
  (5000) and slows it above `AUTO_FOOD_HIGH_ENERGY_THRESHOLD_1`. Swept with
  `python tools/measure_tank_regulation.py benchmarks/tank/survival_5k.py --key
  auto_food_spawn_rate --values 2,3,9,18,36` (artifact
  `research/starvation/food_supply_regulation.json`): across a **4.5x** change
  in food supply (rate 9 -> 2) the loop holds total fish energy inside
  5,013-5,626, a 12% band, while `max_population` pins the count at 60 - so
  per-fish energy there is a constant of the configuration, not an outcome of
  behavior, and a better forager only makes the thermostat close the tap.
  Below the stock rate the loop **saturates** at its 3x boost ceiling and stops
  regulating: at rates 18 and 36 the tank is still draining when the run ends
  (drift -9.5%, -21.1%), so those are collapses, not lower set points.
  `survival_5k` pins rate 9 - the bottom edge of the regulated band - against an
  *engine default* of 36 at which the benchmark is invalid (starvation 0.9528).
  Its validity is bought by that override. (The population arm of the same
  controller, `AUTO_FOOD_HIGH_POP_THRESHOLD_1 = 80`, never fires in any tank
  benchmark, since they all cap population at 50-60.)
- **`starvation_rate` is a share of deaths, not a rate of starving.** It is
  `starvation_deaths / total_deaths`, so it climbs whenever *other* causes are
  rare, and `survival_5k` gates its score to zero above
  `MAX_VALID_STARVATION_RATE = 0.95`. The tank used to sit right on that line -
  seeds 42/2/999 gave 0.8632 / 0.9482 / 0.9834, one already invalid and another
  0.3 points away before any change - which is why a candidate could tip a
  borderline seed over the gate without being broadly worse (see Theme 10.6's
  retracted
  Finding 3).
- **Tank benchmark population means fish**: `avg_pop`, `mean_population`, and
  `final_population` are fish population fields. `final_total_entities` includes
  food and other world objects and is diagnostic only, never the population score.
- **Reproduction is funded by overflow energy**: fish bank energy gained above
  `max_energy` and spend it on offspring. Changes that burn the surplus energy of
  well-fed fish (e.g. ball play, poker) directly suppress birth rate and generation
  turnover, which the ecosystem_health benchmark penalizes. Corollary: "surplus"
  means energy above `max_energy`, not merely above the 40% safe threshold - a fish
  below max is still climbing toward its next birth. The bank is now *also* a
  reserve of last resort (`_draw_on_reserves`), so a change that raises metabolic
  cost is paid for twice: once in births forgone, once in reserves burned staying
  alive.
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
- [docs/EVOLVABILITY.md](docs/EVOLVABILITY.md) - Evolvability levers mapped to code, the research canon, and the ideas graveyard (read before proposing improvements via `/deliberate`)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Full technical architecture
- [docs/SUBSYSTEM_CLASSIFICATION.md](docs/SUBSYSTEM_CLASSIFICATION.md) - Which subsystems are core experimental domains vs support infrastructure vs optional demos (and the deletion policy for each)
- [docs/EVO_CONTRIBUTING.md](docs/EVO_CONTRIBUTING.md) - Evolutionary PR protocol
- [docs/BEHAVIOR_DEVELOPMENT_GUIDE.md](docs/BEHAVIOR_DEVELOPMENT_GUIDE.md) - Creating new algorithms
- [docs/ROADMAP.md](docs/ROADMAP.md) - Current priorities and milestones
