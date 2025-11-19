# AI Code Evolution Workflow

This document describes the **Continuous Improvement (CI) Loop** for automated algorithm evolution using an AI coding agent.

## Overview

Instead of having the simulation mutate itself (risky and hard to debug), this workflow implements a supervised approach where:

1. **Run Simulation** → Collect performance statistics
2. **AI Agent Analysis** → Identify underperforming algorithms
3. **Code Generation** → LLM generates improvements
4. **Pull Request** → Human reviews and approves changes
5. **Merge & Repeat** → Continuous evolution with human oversight

This gives you an **"AI Junior Developer"** that works 24/7, proposing improvements based on real simulation data.

## Architecture

### Source Mapping Registry

The core innovation is `core/registry.py`, which maps algorithm class names to their source files:

```python
from core.registry import get_algorithm_metadata

metadata = get_algorithm_metadata()
# Returns:
# {
#   "greedy_food_seeker": {
#     "class_name": "GreedyFoodSeeker",
#     "source_file": "/path/to/core/algorithms/food_seeking.py",
#     "category": "food_seeking",
#     ...
#   }
# }
```

This enables the AI agent to:
- Know **exactly which file** to edit for a given algorithm
- Target improvements to specific algorithms based on performance
- Generate surgical pull requests that modify only what's needed

### Enhanced Stats Export

When you run a simulation with `--export-stats`, the JSON now includes:

```json
{
  "algorithm_registry": {
    "greedy_food_seeker": {
      "class_name": "GreedyFoodSeeker",
      "source_file": "/home/user/tank/core/algorithms/food_seeking.py",
      "category": "food_seeking"
    }
  },
  "algorithm_performance": {
    "greedy_food_seeker": {
      "source_file": "/home/user/tank/core/algorithms/food_seeking.py",
      "category": "food_seeking",
      "reproduction_rate": 0.12,
      "survival_rate": 0.15,
      "death_breakdown": {
        "starvation": 45,
        "predation": 38,
        "old_age": 2
      }
    }
  }
}
```

The AI agent reads this and knows:
- **What's broken**: `reproduction_rate: 0.12` (poor)
- **Why it's broken**: Main death cause is starvation
- **Where to fix it**: `core/algorithms/food_seeking.py`

## Step-by-Step Workflow

### 1. Run Simulation and Export Stats

```bash
# Run headless simulation with stats export
python main.py --headless --max-frames 10000 --export-stats results.json
```

This creates `results.json` with comprehensive performance data.

### 2. Run the AI Code Evolution Agent

```bash
# Set up your API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Run the agent
python scripts/ai_code_evolution_agent.py results.json --provider anthropic
```

**What the agent does:**

1. **Loads** `results.json`
2. **Identifies** the worst performing algorithm (lowest reproduction rate)
3. **Reads** the source file for that algorithm
4. **Calls** Claude/GPT with a detailed improvement prompt
5. **Writes** the improved code back to the file
6. **Creates** a git branch (`ai-improve-greedy-food-seeker-20250119-143022`)
7. **Commits** with a detailed message explaining the changes

### 3. Review the Changes

```bash
# See what the AI changed
git diff HEAD~1

# Test the changes
python main.py --headless --max-frames 1000
```

### 4. Push and Create Pull Request

```bash
# Push to remote
git push -u origin ai-improve-greedy-food-seeker-20250119-143022

# Create PR (manually on GitHub or using gh CLI)
gh pr create --title "AI Optimization: Improve GreedyFoodSeeker" \
  --body "See commit message for details"
```

### 5. Merge and Repeat

After reviewing and approving the PR:

```bash
# Merge the PR
gh pr merge --squash

# Run a new simulation
python main.py --headless --max-frames 10000 --export-stats results2.json

# Run the agent again
python scripts/ai_code_evolution_agent.py results2.json
```

The agent will now find the **next** worst performer and improve it!

## AI Agent Options

### Provider Selection

```bash
# Use Claude (default)
python scripts/ai_code_evolution_agent.py results.json --provider anthropic

# Use GPT-4
python scripts/ai_code_evolution_agent.py results.json --provider openai
```

### Dry Run Mode

Test without making changes:

```bash
python scripts/ai_code_evolution_agent.py results.json --dry-run
```

This will:
- Show which algorithm it would improve
- Display the generated code (without writing it)
- Skip git operations

## Example Run

```
$ python scripts/ai_code_evolution_agent.py results.json
================================================================================
AI Code Evolution Agent - Starting
================================================================================
INFO: Loading stats from: results.json
INFO: Identified worst performer: greedy_food_seeker
INFO:   Reproduction rate: 12.34%
INFO:   Avg lifespan: 450.2 frames
INFO:   Main death cause: {'starvation': 45, 'predation': 38, 'old_age': 2}
INFO: Reading source file: /home/user/tank/core/algorithms/food_seeking.py
INFO: Generating improvement for greedy_food_seeker using anthropic...
INFO: Writing improved code to: /home/user/tank/core/algorithms/food_seeking.py
INFO: Creating branch: ai-improve-greedy-food-seeker-20250119-143022
INFO: Staging changes...
INFO: Committing changes...
INFO: Branch 'ai-improve-greedy-food-seeker-20250119-143022' created with improvements!
================================================================================
AI Code Evolution Agent - Complete!
================================================================================

Next steps:
1. Review the changes with: git diff HEAD~1
2. Test the simulation to verify improvements
3. Push the branch: git push -u origin ai-improve-greedy-food-seeker-20250119-143022
4. Create a Pull Request on GitHub
5. Merge if tests pass and improvements are verified!
```

## Benefits of This Approach

### ✅ Safety

- **Human in the loop**: You review every change before merging
- **No self-modifying code**: The simulation never edits itself
- **Git history**: Full audit trail of what changed and why
- **Rollback**: Easy to revert if AI makes mistakes

### ✅ Debuggability

- **Clear diffs**: See exactly what the AI changed
- **Targeted fixes**: Only one algorithm improved per PR
- **Commit messages**: Explain the reasoning behind changes
- **Test before merge**: Run simulations to verify improvements

### ✅ Scalability

- **Automated iteration**: Run in a loop for continuous improvement
- **Parallel development**: Multiple agents can work on different algorithms
- **Data-driven**: Improvements based on real simulation results
- **Learning over time**: Track which AI-generated improvements work best

## Advanced Usage

### Custom Improvement Criteria

You can modify `scripts/ai_code_evolution_agent.py` to target specific metrics:

```python
# Instead of worst reproduction rate, find worst survival rate
worst_algo = min(candidates.items(), key=lambda x: x[1].get("survival_rate", 1.0))

# Or target specific death causes
# Find algorithms dying from predation
worst_algo = max(candidates.items(),
    key=lambda x: x[1].get("death_breakdown", {}).get("predation", 0))
```

### Batch Improvements

Run multiple improvement cycles:

```bash
# Improve top 3 worst performers
for i in {1..3}; do
    python scripts/ai_code_evolution_agent.py results.json
    python main.py --headless --max-frames 5000 --export-stats results.json
done
```

### Automated CI/CD Pipeline

Set up GitHub Actions to:

1. Run simulation nightly
2. Export stats
3. Run AI agent
4. Create PR automatically
5. Run tests on the PR
6. Auto-merge if tests pass

## Troubleshooting

### "Source file not found"

The registry couldn't map the algorithm to a file. This usually means:
- The algorithm was created dynamically
- The class isn't in `ALL_ALGORITHMS` list

**Fix**: Add the algorithm to `core/algorithms/__init__.py`

### "No algorithm to improve found"

All algorithms have insufficient data (< 5 births). Run a longer simulation:

```bash
python main.py --headless --max-frames 50000 --export-stats results.json
```

### LLM generates broken code

The AI sometimes makes syntax errors. This is why human review is critical:

1. Review the diff carefully
2. Run tests before merging
3. If broken, reject the PR and run the agent again

## Future Enhancements

- **Multi-algorithm improvements**: Improve multiple algorithms per PR
- **Performance regression detection**: Reject PRs that make things worse
- **Automated testing**: Run simulation tests in CI before allowing merge
- **Parameter tuning**: Not just code, but also tune parameter ranges
- **Cross-algorithm learning**: Have AI study top performers to improve others

## Conclusion

This workflow gives you the power of **AI-assisted evolution** while maintaining:
- **Human oversight** (PR reviews)
- **Safety** (no self-modifying code)
- **Debuggability** (clear git history)
- **Scalability** (run continuously)

You've built an **AI Junior Developer** that never sleeps! 🚀
