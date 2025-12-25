# Headless Simulation Mode

The fish tank simulation supports running in headless mode without any graphical visualization. This is useful for:

- Running long simulations faster than realtime
- Collecting statistics and performance data
- Running on servers without displays
- Automated testing and benchmarking

## Usage

### Web Mode (Default)

Run with React UI and FastAPI backend:

```bash
python main.py
```

Then open http://localhost:3000 in your browser.

### Headless Mode

Run without visualization, stats-only:

```bash
python main.py --headless --max-frames 10000 --stats-interval 500
```

#### Parameters

- `--headless`: Enable headless mode (no UI)
- `--max-frames`: Maximum number of frames to simulate (default: 10000)
- `--stats-interval`: Print stats every N frames (default: 300)
- `--seed`: Random seed for deterministic behavior (optional)

#### Examples

Quick test run (1000 frames):
```bash
python main.py --headless --max-frames 1000
```

Long simulation (100000 frames ≈ 55 minutes of sim time):
```bash
python main.py --headless --max-frames 100000 --stats-interval 3000
```

Deterministic simulation (for testing):
```bash
python main.py --headless --max-frames 1000 --seed 42
```

## Performance

Headless mode typically runs 10-300x faster than realtime, depending on:
- Number of entities in the simulation
- CPU performance
- Algorithm complexity

Example: A 3000-frame simulation (100 seconds of sim time) runs in about 7 seconds of real time (14x speedup).

## Output

Headless mode provides:

1. **Periodic stats** printed to console:
   - Frame count and simulation time
   - Real-time elapsed and simulation speed
   - Population metrics (births, deaths, capacity)
   - Entity counts (fish, food, plants)
   - Death causes breakdown
   - Reproduction statistics
   - Genetic diversity metrics

2. **Final algorithm performance report**:
   - Saved to `algorithm_performance_report.txt`
   - Ranks algorithms by reproduction rate, survival rate, and lifespan
   - Identifies best and worst performers
   - Provides recommendations for evolution

## Deterministic Behavior

Headless mode supports deterministic behavior via the `--seed` parameter. When using the same seed:
- Produces identical results across runs
- Useful for reproducible experiments and testing
- Enables regression testing

## Architecture

The codebase separates simulation logic from visualization:

- **`simulation_engine.py`**: Pure simulation logic without UI dependencies
- **`main.py`**: Entry point with command-line argument parsing
- **`core/entities.py`**: Pure entity logic (no rendering)
- **`backend/`**: FastAPI server for web mode

All core simulation logic in `core/` modules is UI-independent, allowing headless operation.

## Collision Detection

The simulation uses **bounding box (AABB) collision detection**:
- Fast and efficient
- Deterministic results
- Consistent behavior across runs

## Running Tests

You can verify headless mode behavior with automated tests:

```bash
pytest tests/
```

Or run a specific headless test:

```bash
python main.py --headless --max-frames 1000 --seed 42
```

## Web vs Headless Mode

Both modes use the same `SimulationEngine` core:
- Same entity lifecycle logic
- Same collision detection algorithm
- Same genetics and evolution systems
- Same population dynamics

The only difference is the presentation layer:
- **Web mode**: Sends state to React frontend via WebSocket
- **Headless mode**: Prints stats to console
