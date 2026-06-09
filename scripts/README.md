# Simulation Scripts

Utility scripts for running, evolving, benchmarking, diagnosing, and analyzing
the Tank World simulation. These are operational helpers — the supported,
documented entry points live in [`tools/`](../tools/README.md) and `main.py`.

Run any Python script with `PYTHONPATH=.` if you hit import errors:

```bash
PYTHONPATH=. python scripts/<name>.py --help
```

## Start here

- `diagnose.py`: **Environment health check.** Prints a green/red checklist over
  the Python toolchain, core modules, the algorithm registry, a live short
  simulation, and the frontend toolchain — each failure comes with an actionable
  hint. Run it first whenever something won't start. Exits non-zero on failure,
  so it doubles as a CI/setup gate. (To launch the app itself, use `python
  start.py` from the repo root.)

## Evolution loop

- `ai_code_evolution_agent.py`: End-to-end AI agent — reads simulation stats,
  finds the worst-performing algorithm, asks an LLM (Anthropic/OpenAI) for an
  improvement, optionally validates it, and commits to a branch. Needs
  `pip install -e .[ai]` and an `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`.
- `demo_evolution_loop.sh`: Scripted walkthrough of the full benchmark →
  compare → validate loop. Good for a first read of how the pieces fit.
- `complete_solution_workflow.sh`: Capture-and-submit workflow for a solution.
- `run_until_generation.py`: Run a headless sim until generation N is reached
  (useful for getting past early-population transients before measuring).

## Running & simulation

- `run_headless_test.py`: Minimal headless run for quick verification.
- `run_poker_simulations.py`: Batch poker games for strategy evaluation.
- `start_servers.sh` / `stop_servers.sh` / `start.bat` / `restart_servers.ps1`:
  Server lifecycle management (backend + frontend).
- `cleanup_tanks.py`: Clean up persisted tank data and state.

## Analysis

- `analyze_sim.py`: General post-run analysis of an exported stats JSON.
- `analyze_energy.py`: Energy flow through the ecosystem.
- `analyze_population.py`: Population dynamics over time.
- `trace_energy.py` / `debug_energy_flow.py`: Detailed energy tracing for
  debugging accounting bugs.

## Diagnosis

- `diagnose_food_seeking.py`: Checks whether fish are foraging or stuck
  clustering around the soccer ball (a common starvation cause — see CLAUDE.md).
- `diagnose_poker_evolution.py`: Diagnoses stalls in the poker evolution loop.
- `check_castle_size.py`, `check_poker_payload.py`, `check_poker_summary.py`,
  `check_sim_engine.py`: Targeted invariant/state checks.

## Benchmarking & profiling

- `benchmark_performance.py`: Simulation FPS and throughput.
- `profile_simulation.py` / `profile_run.py`: Profile the simulation loop to
  find hot spots.
- `profile_poker_engine.py`: Profile the poker engine specifically.
- `poker_eval_metrics.py`: Metrics for poker agent evaluation.

## Verification (CI helpers)

- `check_imports.py` / `import_check.py` / `import_ecosystem_check.py`: Verify
  critical imports resolve (used by CI).
- `check_pycache.py`: Fail if compiled `__pycache__` artifacts are staged.
- `verify_plants.py`: Plant growth and energy mechanics.
- `verify_skill_games.py`: Skill-game integrations.
- `rcss_adapter_smoketest.py`: Smoketest for the RoboCup Soccer adapter.

## Tournaments

- `run_ai_tournament.py`: Run poker tournaments between AI strategies
  (`--write-back` updates results).

## Setup & infra

- `setup-windows.ps1` / `oracle_cloud_setup.sh`: Environment setup helpers.
- `test_cross_server_migration.sh`, `test_discovery.sh`, `test_discovery_hub.sh`:
  Multi-server discovery/migration smoke tests.

## Archive

Obsolete, one-off, and legacy scripts live in `archive/`. They are kept for
reference only — do not rely on them for active development.
