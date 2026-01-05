# Contributing Evolutionary Improvements

This guide explains how to contribute **evolutionary improvements** to Tank World—changes that advance the Best Known Solutions (BKS) through reproducible benchmarks.

## The Evolutionary PR Protocol

Tank World treats the repository itself as an evolving organism. When you discover an improvement (whether you're human or AI), you follow the **Evolutionary PR Protocol** to get it merged into the evolutionary lineage.

### Core Principle: Git as Heredity

- **PRs are mutations**: Your proposed change is a genetic variation
- **CI is selection**: Automated validation determines fitness
- **Merged changes are offspring**: Future agents inherit your improvement
- **Git history is lineage**: The evolutionary tree is auditable

## Types of Evolutionary Contributions

### Layer 1: Algorithm Evolution (Most Common)

Improving the behavior algorithms that fish use in simulations:
- Better algorithm implementations
- New algorithm designs
- Parameter range optimizations
- Bug fixes that improve performance

**Merge criteria**: Automated merge if benchmarks pass + no regressions

### Layer 2: Meta-Evolution (Requires Human Review)

Improving the evolution toolkit itself:
- Better benchmark designs
- Improved fitness functions
- Enhanced agent instructions/workflows
- CI gate improvements

**Merge criteria**: Must pass benchmarks + REQUIRES human code review

## Step-by-Step: Contributing an Improvement

### 1. Run a Benchmark

Choose a benchmark from `benchmarks/` and run it with a deterministic seed:

```bash
# Example: Run the Tank survival benchmark
python tools/run_bench.py benchmarks/tank/survival_30k.py --seed 42

# Output: results.json with your score and artifacts
```

**Important**: Always use deterministic seeds so results can be reproduced.

### 2. Compare Against BKS

Check if your result beats the current Best Known Solution:

```bash
# Compare your results against the current champion
python tools/validate_improvement.py results.json champions/tank/survival_30k.json

# Output: "IMPROVEMENT: +45.7 points (1247.3 vs 1201.6)"
#         or "NO IMPROVEMENT: -12.3 points"
```

If you don't beat the BKS, iterate on your approach and try again!

### 3. Update the Champion Registry

If you have an improvement, update the champion file with your new result:

```bash
# Create a branch for your improvement
git checkout -b improve/survival-energy-conserver

# Edit champions/tank/survival_30k.json with your new champion data
# (tools/validate_improvement.py can generate this for you)

# Commit with a descriptive message
git add champions/tank/survival_30k.json
git commit -m "Improve Tank survival: EnergyConserver parameter optimization

New score: 1247.3 (previous: 1201.6, +45.7)
Algorithm: EnergyConserver with adjusted rest_threshold
Seed: 42
Reproduction: python tools/run_bench.py benchmarks/tank/survival_30k.py --seed 42

- Reduced rest_threshold from 0.3 to 0.25
- Allows fish to conserve energy more aggressively
- Improves average lifespan by 12%"
```

### 4. Push and Open PR

```bash
# Push your branch
git push -u origin improve/survival-energy-conserver

# Open a PR on GitHub
# Title: "Improve Tank survival: EnergyConserver parameter optimization"
# Description: Include benchmark results, reproduction command, and explanation
```

### 5. CI Validation

The CI system will automatically:

1. **Detect** that you modified a champion file
2. **Re-run** the claimed benchmark with the same seed
3. **Verify** that the score matches what you claimed
4. **Check** for regressions on other benchmarks
5. **Approve or reject** based on results

**If CI passes**: Your PR is approved for merge (automatic for Layer 1, human review for Layer 2)

**If CI fails**: The benchmark couldn't reproduce your result—check for non-determinism or errors

## Champion Registry Format

Each champion file (e.g., `champions/tank/survival_30k.json`) follows this schema:

```json
{
  "benchmark_id": "tank/survival_30k",
  "version": "1.0",
  "champion": {
    "score": 1247.3,
    "algorithm": "EnergyConserver",
    "parameters": {
      "rest_threshold": 0.25,
      "activity_threshold": 0.75
    },
    "genome": {
      "speed": 2.1,
      "size": 1.0,
      "vision_range": 100.0,
      "max_energy": 150.0,
      "algorithm_index": 42
    },
    "commit": "abc123def456",
    "timestamp": "2026-01-05T10:30:00Z",
    "seed": 42
  },
  "reproduction": {
    "command": "python tools/run_bench.py benchmarks/tank/survival_30k.py --seed 42",
    "runtime_seconds": 45.2,
    "deterministic": true
  },
  "history": [
    {
      "score": 1201.6,
      "commit": "def456abc789",
      "timestamp": "2026-01-01T12:00:00Z",
      "improvement_note": "Previous champion"
    }
  ]
}
```

### Key Fields

- **score**: The fitness achieved (higher is better)
- **algorithm**: Name of the winning algorithm
- **parameters**: Algorithm-specific parameters
- **genome**: Complete genome data for reproduction
- **commit**: Git commit hash where this was achieved
- **seed**: Deterministic seed for reproduction
- **reproduction.command**: Exact command to reproduce
- **history**: Previous champions (for lineage tracking)

## Benchmark Requirements

All benchmarks must satisfy these requirements:

### 1. Determinism

**Required**: Given the same seed, the benchmark must produce **byte-for-byte identical results**.

```python
# Good: Uses injected RNG with fixed seed
def run_benchmark(seed: int) -> float:
    rng = random.Random(seed)
    sim = create_simulation(seed=seed)
    return sim.run(frames=30000)

# Bad: Uses system time or global random
def run_benchmark() -> float:
    start_time = time.time()  # Non-deterministic!
    sim = create_simulation()
    return sim.run(frames=30000)
```

### 2. Reproducibility

**Required**: Include exact reproduction command in champion registry.

```json
"reproduction": {
  "command": "python tools/run_bench.py benchmarks/tank/survival_30k.py --seed 42",
  "runtime_seconds": 45.2,
  "deterministic": true
}
```

### 3. Measurable Fitness

**Required**: Output a single scalar fitness value (higher = better).

```python
# Good: Clear fitness metric
def compute_fitness(results: SimulationResults) -> float:
    return results.average_lifespan

# Bad: Multiple incomparable metrics
def compute_fitness(results: SimulationResults) -> dict:
    return {"lifespan": 120, "births": 45, "deaths": 12}  # Which is "better"?
```

### 4. Reasonable Runtime

**Recommended**: Benchmarks should complete in under 5 minutes for CI validation.

```python
# Good: 30k frames (~1-2 minutes in headless mode)
BENCHMARK_FRAMES = 30_000

# Bad: 1M frames (~30 minutes)
BENCHMARK_FRAMES = 1_000_000  # Too slow for CI
```

## CI Validation Process

When you open a PR that modifies champion files, CI runs this workflow:

### 1. Detect Changes

```yaml
# .github/workflows/bench.yml detects champion updates
if: contains(github.event.pull_request.changed_files, 'champions/')
```

### 2. Re-run Benchmarks

```bash
# CI extracts reproduction command from champion file
python tools/run_bench.py benchmarks/tank/survival_30k.py --seed 42
```

### 3. Verify Score

```bash
# CI compares actual score vs claimed score
if actual_score >= claimed_score - tolerance:
    print("✅ Score verified!")
else:
    print("❌ Score mismatch: claimed {claimed_score}, got {actual_score}")
    exit(1)
```

### 4. Check Regressions

```bash
# CI runs other benchmarks to ensure no regressions
python tools/run_bench.py benchmarks/tank/reproduction_30k.py --seed 42
python tools/run_bench.py benchmarks/tank/diversity_30k.py --seed 42

# If any benchmark regresses significantly, PR is rejected
```

### 5. Approve or Reject

- **Layer 1 PRs**: Automatic merge if validation passes
- **Layer 2 PRs**: Requires human code review even if validation passes

## Common Issues and Solutions

### Issue: "CI couldn't reproduce my result"

**Cause**: Non-determinism in your benchmark run

**Solutions**:
1. Check that you used a fixed seed: `--seed 42`
2. Ensure no global RNG usage (use injected RNGs)
3. Verify no system time or network dependencies
4. Run locally multiple times to confirm determinism

### Issue: "My improvement was rejected due to regression"

**Cause**: Your change improved one benchmark but degraded another

**Solutions**:
1. Check which benchmark regressed (CI log shows this)
2. Understand the trade-off (e.g., survival vs reproduction)
3. Either:
   - Adjust your change to avoid the regression
   - Open two separate PRs for different optimization directions
   - Document the trade-off and ask for human review

### Issue: "My Layer 2 PR is stuck in review"

**Cause**: Layer 2 changes (instructions, benchmarks, CI) require human review

**Solutions**:
1. Ensure your PR clearly explains the meta-improvement
2. Show benchmarked evidence that the new approach is better
3. Document how future agents will benefit
4. Be patient—Layer 2 reviews protect against "prompt soup"

## Anti-Patterns to Avoid

### ❌ Informal "Seems Better" Claims

```markdown
# Bad PR description
"I tweaked the algorithm and it seems better in my tests"
```

**Fix**: Always include benchmark scores and comparison vs BKS.

### ❌ Non-Reproducible Results

```markdown
# Bad champion entry
"score": 1247.3,
"reproduction": {
  "command": "just run it and see"
}
```

**Fix**: Include exact reproduction command with deterministic seed.

### ❌ Overfitting to One Benchmark

**Bad**: Optimize only for survival, ignore reproduction and diversity

**Fix**: Check all benchmarks before submitting. Trade-offs are OK if documented.

### ❌ Vague Commit Messages

```bash
# Bad commit message
git commit -m "improved stuff"
```

**Fix**: Explain what improved, by how much, and why.

### ❌ Prompt Soup (Layer 2)

**Bad**: "I made the agent instructions longer and more detailed"

**Fix**: Show benchmarked evidence that the new instructions produce more/better Layer 1 improvements.

## Example: Complete Evolutionary PR

Here's a full example of a successful evolutionary PR:

### Before: Current Champion

```json
// champions/tank/survival_30k.json
{
  "champion": {
    "score": 1201.6,
    "algorithm": "EnergyConserver",
    "parameters": {
      "rest_threshold": 0.3,
      "activity_threshold": 0.75
    }
  }
}
```

### After: Improved Champion

```json
// champions/tank/survival_30k.json
{
  "champion": {
    "score": 1247.3,
    "algorithm": "EnergyConserver",
    "parameters": {
      "rest_threshold": 0.25,  // ← Changed from 0.3
      "activity_threshold": 0.75
    },
    "commit": "abc123def456",
    "timestamp": "2026-01-05T10:30:00Z",
    "seed": 42
  },
  "reproduction": {
    "command": "python tools/run_bench.py benchmarks/tank/survival_30k.py --seed 42",
    "runtime_seconds": 45.2,
    "deterministic": true
  },
  "history": [
    {
      "score": 1201.6,
      "commit": "def456abc789",
      "timestamp": "2026-01-01T12:00:00Z"
    }
  ]
}
```

### PR Description

```markdown
# Improve Tank Survival: EnergyConserver Parameter Optimization

## Summary

Optimized the `rest_threshold` parameter for the EnergyConserver algorithm,
improving average fish lifespan by 12%.

## Benchmark Results

- **Benchmark**: tank/survival_30k
- **Previous BKS**: 1201.6 (commit def456abc789)
- **New Score**: 1247.3
- **Improvement**: +45.7 points (+3.8%)
- **Seed**: 42

## Changes

Reduced `rest_threshold` from 0.3 to 0.25:
- Fish now conserve energy more aggressively
- Earlier rest periods prevent energy crashes
- Slight decrease in foraging efficiency offset by improved survival

## Reproduction

```bash
python tools/run_bench.py benchmarks/tank/survival_30k.py --seed 42
```

## Other Benchmarks (No Regressions)

- `tank/reproduction_30k`: 842.1 (previous: 845.3, -0.4% acceptable)
- `tank/diversity_30k`: 2.34 (previous: 2.31, +1.3%)

## Type

- [x] Layer 1 (Algorithm Evolution) - Automated merge approved
- [ ] Layer 2 (Meta-Evolution) - Requires human review
```

### Result

✅ CI validates the score
✅ No significant regressions
✅ Automatic merge approved
✅ New champion becomes baseline for future PRs

## Getting Help

- **Questions about benchmarks**: Open an issue with tag `benchmark`
- **CI validation issues**: Check `.github/workflows/bench.yml` logs
- **General discussion**: See [GitHub Discussions](https://github.com/mbolaris/tank/discussions)
- **Vision questions**: Read [docs/VISION.md](VISION.md)

## Further Reading

- [VISION.md](VISION.md) - The three-layer evolution paradigm
- [ROADMAP.md](ROADMAP.md) - Evolution Loop MVP priorities
- [README.md](../README.md) - Overview of Tank World
- [ARCHITECTURE.md](ARCHITECTURE.md) - Technical architecture

---

**Remember**: Evolution is incremental. Small, reproducible improvements accumulate over time. Every merged PR makes the system better for future agents to build upon.

Welcome to the evolutionary lineage. 🧬
