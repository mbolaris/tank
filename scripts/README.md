# Simulation Scripts

This directory contains utility scripts for running, benchmarking, and analyzing the Tank World simulation.

## Core Utilities

- `cleanup_tanks.py`: Cleans up tank data and state.
- `import_check.py`: Verifies all critical imports work (part of CI).
- `run_headless_test.py`: Minimal headless simulation run for quick verification.
- `start.bat` / `start_servers.sh` / `stop_servers.sh`: Server lifecycle management.

## Analysis & Benchmarking

- `analyze_energy.py`: Analyzes energy flow in the ecosystem.
- `analyze_population.py`: Tracks population dynamics over time.
- `benchmark_performance.py`: Benchmarks simulation FPS and throughput.
- `profile_simulation.py`: Profiles the simulation loop to find bottlenecks.
- `trace_energy.py`: Detailed energy tracing for debugging.

## Poker Evolution

- `run_ai_tournament.py`: Runs efficient poker tournaments between AI agents.
- `diagnose_poker_evolution.py`: Diagnoses issues in the poker evolution loop.
- `poker_eval_metrics.py`: Metrics for poker agent evaluation.

## Verification

- `verify_plants.py`: Verifies plant growth and energy mechanics.
- `verify_skill_games.py`: Verifies skill game integrations.
- `rcss_adapter_smoketest.py`: Smoketest for RCSS adapter.

## Archive

Obsolete, one-off, and legacy scripts are moved to `archive/`. Do not rely on them for active development.
