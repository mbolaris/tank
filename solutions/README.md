# TankWorld Solution Repository

This directory contains submitted skill game solutions from TankWorld simulations.
Each solution represents a behavioral strategy that has demonstrated strong performance
in poker and other skill games.

## Solution Format

Each solution is stored as a JSON file with the following structure:

```json
{
  "metadata": {
    "solution_id": "abc12345_20240101_120000",
    "name": "Expert Poker Fish",
    "description": "High-performing poker strategy evolved over 1000 generations",
    "author": "username",
    "submitted_at": "2024-01-01T12:00:00",
    "generation": 1000,
    "fish_id": 42
  },
  "behavior_algorithm": {
    "class": "PokerStrategist",
    "parameters": { ... }
  },
  "benchmark_result": {
    "elo_rating": 1550,
    "skill_tier": "advanced",
    "weighted_bb_per_100": 12.5,
    "per_opponent": { ... }
  }
}
```

## How to Submit a Solution

### Via CLI

```bash
# List existing solutions
python scripts/submit_solution.py list

# Capture from a simulation state file
python scripts/submit_solution.py submit --file state.json --name "My Strategy" --author "myname" --evaluate --push

# Evaluate a solution
python scripts/submit_solution.py evaluate <solution_id>

# Compare all solutions
python scripts/submit_solution.py compare

# Generate a benchmark report
python scripts/submit_solution.py report --print
```

### Via API

```bash
# List solutions
curl http://localhost:8000/api/solutions

# Capture from running tank
curl -X POST http://localhost:8000/api/solutions/capture/{tank_id} \
  -H "Content-Type: application/json" \
  -d '{"name": "My Strategy", "author": "myname", "evaluate": true}'

# Evaluate a solution
curl -X POST http://localhost:8000/api/solutions/evaluate/{solution_id}

# Get comparison
curl http://localhost:8000/api/solutions/compare

# Get benchmark report
curl http://localhost:8000/api/solutions/report
```

### Via Frontend

1. Open the TankWorld UI
2. Navigate to the Solution Leaderboard panel
3. Click "Capture Best" to save the best performing fish from your current tank
4. Solutions will automatically be evaluated against benchmark opponents

## Benchmark System

Solutions are evaluated against 8 standard benchmark opponents:

| Opponent | Elo | Description |
|----------|-----|-------------|
| always_fold | 800 | Folds every hand (trivial) |
| random | 900 | Random actions (trivial) |
| loose_passive | 1100 | Calling station |
| tight_passive | 1150 | Rock player |
| tight_aggressive | 1400 | TAG style |
| loose_aggressive | 1350 | LAG style |
| maniac | 1450 | Hyper-aggressive |
| balanced | 1600 | GTO-inspired |

### Skill Tiers

| Tier | Elo Range | Description |
|------|-----------|-------------|
| failing | <900 | Worse than random |
| novice | 900-1100 | Basic play |
| beginner | 1100-1300 | Competent |
| intermediate | 1300-1450 | Solid |
| advanced | 1450-1550 | Strong |
| expert | 1550-1700 | Very strong |
| master | >1700 | Elite |

## Running the Comprehensive Test

To compare all submitted solutions:

```bash
# Run the benchmark comparison test
pytest tests/test_solution_tracking.py::TestComprehensiveBenchmark -v

# Run full test suite
pytest tests/test_solution_tracking.py -v
```

## Contributing Solutions

1. Run a TankWorld simulation until fish develop strong poker skills
2. Capture the best performer using the CLI or API
3. The solution will be saved to this directory
4. Commit and push to share with other TankWorld users

```bash
git add solutions/
git commit -m "Submit solution: <solution_name>"
git push
```

## Leaderboard

Current top solutions (updated by running `python scripts/submit_solution.py report`):

<!-- Leaderboard will be auto-generated here -->

---

*This directory is part of the TankWorld simulation framework for studying
emergent AI behaviors through evolutionary skill games.*
