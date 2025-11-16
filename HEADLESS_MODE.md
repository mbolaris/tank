# Headless Simulation Mode

The fish tank simulation now supports running in headless mode without any graphical visualization. This is useful for:

- Running long simulations faster than realtime
- Collecting statistics and performance data
- Running on servers without displays
- Automated testing and benchmarking

## Usage

### Graphical Mode (Default)

Run with pygame visualization:

```bash
python main.py --mode graphical
```

Or simply:

```bash
python fishtank.py
```

### Headless Mode

Run without visualization, stats-only:

```bash
python main.py --mode headless --max-frames 10000 --stats-interval 500
```

#### Parameters

- `--mode`: Choose `graphical` or `headless` (default: `graphical`)
- `--max-frames`: Maximum number of frames to simulate (default: 10000)
- `--stats-interval`: Print stats every N frames (default: 300)

#### Examples

Quick test run (1000 frames):
```bash
python main.py --mode headless --max-frames 1000
```

Long simulation (100000 frames ≈ 55 minutes of sim time):
```bash
python main.py --mode headless --max-frames 100000 --stats-interval 3000
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

2. **Final algorithm performance report**:
   - Saved to `algorithm_performance_report.txt`
   - Ranks algorithms by reproduction rate, survival rate, and lifespan
   - Identifies best and worst performers
   - Provides recommendations for evolution

## Architecture

The codebase has been refactored to separate simulation logic from visualization:

- **`simulation_engine.py`**: Pure simulation logic without pygame dependencies
- **`fishtank.py`**: Graphical wrapper using pygame
- **`main.py`**: Entry point with command-line argument parsing
- **`core/entities.py`**: Pure entity logic (no rendering)
- **`agents.py`**: Pygame sprite wrappers for visualization

All core simulation logic in `core/` modules is now pygame-independent, allowing headless operation.
