# Evolution Example: Creating and Improving Behaviors

This document demonstrates the complete workflow for evolving fish behaviors using the Tank simulation.

## Table of Contents

1. [Overview](#overview)
2. [Step 1: Initial Run](#step-1-initial-run)
3. [Step 2: Analyze Results](#step-2-analyze-results)
4. [Step 3: Identify Opportunities](#step-3-identify-opportunities)
5. [Step 4: Create New Behavior](#step-4-create-new-behavior)
6. [Step 5: Test and Compare](#step-5-test-and-compare)
7. [Step 6: Iterate](#step-6-iterate)

---

## Overview

The evolution workflow follows this pattern:

```
Run Simulation → Analyze Stats → Identify Gaps → Create Behavior → Test → Iterate
```

This example shows how to:
- Run headless simulations to gather data
- Analyze which behaviors succeed/fail
- Create new behaviors based on insights
- Compare performance across runs

---

## Step 1: Initial Run

First, run a baseline simulation to see which behaviors emerge as successful:

```bash
# Run 10,000 frame simulation with stats export
python main.py --headless \
  --max-frames 10000 \
  --stats-interval 1000 \
  --export-stats baseline_run.json \
  --seed 42
```

**What to look for during the run:**

```
Population: 45/100
Generation: 8
Total Births: 245
Total Deaths: 200
Capacity: 45%

Genetic Diversity:
  Unique Algorithms: 12/48    # <-- Only 12 behaviors being used!
  Unique Species: 3/4
  Diversity Score: 35%
```

**Key insight**: Only 12 out of 48 algorithms are active. This means 36 behaviors are not competitive.

---

## Step 2: Analyze Results

After the run completes, examine the exported JSON:

```bash
# View the JSON structure
python -m json.tool baseline_run.json | less

# Or use a custom analysis script (we'll create this)
python scripts/analyze_behavior_performance.py baseline_run.json
```

### Example JSON Output Structure

```json
{
  "simulation_metadata": {
    "total_frames": 10000,
    "simulation_speed_multiplier": 15.2
  },
  "algorithm_performance": {
    "greedy_food_seeker": {
      "total_births": 45,
      "total_deaths": 38,
      "current_population": 7,
      "avg_lifespan_frames": 1250,
      "survival_rate": 0.156,
      "reproduction_rate": 1.2,
      "energy_efficiency": 12.5,
      "death_breakdown": {
        "starvation": 28,        # <-- High starvation!
        "old_age": 8,
        "predation": 2
      }
    },
    "energy_conserver": {
      "total_births": 62,
      "total_deaths": 50,
      "current_population": 12,
      "avg_lifespan_frames": 1850,
      "survival_rate": 0.194,
      "reproduction_rate": 1.8,   # <-- High reproduction!
      "energy_efficiency": 18.3,
      "death_breakdown": {
        "starvation": 5,          # <-- Low starvation!
        "old_age": 40,
        "predation": 5
      }
    }
  },
  "recommendations": {
    "top_performers": [
      {
        "algorithm_name": "energy_conserver",
        "reproduction_rate": 1.8,
        "reason": "High reproduction rate and low starvation"
      }
    ],
    "worst_performers": [
      {
        "algorithm_name": "greedy_food_seeker",
        "reproduction_rate": 0.4,
        "main_death_cause": "starvation",
        "reason": "Burns too much energy, starves often"
      }
    ]
  }
}
```

---

## Step 3: Identify Opportunities

From the analysis, we can identify patterns:

### Successful Behaviors (Learn From These)

**EnergyConserver** is thriving because:
- Low starvation rate (5 deaths vs 28 for GreedyFoodSeeker)
- High reproduction rate (1.8 offspring per birth)
- Long lifespan (1850 frames avg)
- Dies mostly of old age (successful life)

**Key insight**: Energy efficiency beats aggressive food seeking in this environment.

### Failed Behaviors (Learn What NOT To Do)

**GreedyFoodSeeker** is failing because:
- High starvation rate (74% of deaths)
- Burns energy chasing distant food
- Short lifespan (1250 frames)
- Low reproduction (only 1.2x)

**Key insight**: Aggressive food seeking wastes energy on long pursuits.

### Opportunity Gaps

Looking at the 36 unused algorithms, we notice:
- No behavior optimizes for "opportunistic feeding" (only eat nearby high-value food)
- No behavior switches strategy based on population density
- No behavior exploits day/night cycle differences

**Hypothesis**: A behavior that only pursues food when it's **both nearby AND high-value** would:
- Conserve energy like EnergyConserver
- Feed more effectively than passive conservation
- Achieve higher reproduction rates

---

## Step 4: Create New Behavior

Based on our analysis, let's create **SelectiveFoodSeeker**:

```python
# File: core/algorithms/food_seeking.py

class SelectiveFoodSeeker(BehaviorAlgorithm):
    """
    Only pursues food that is both nearby and high-value (energy efficient)

    This behavior combines the energy efficiency of conservative behaviors
    with the active feeding of food seekers, but only when conditions are optimal.

    Evolutionary Advantage:
        - High food density: Finds best food without wasting energy on poor options
        - Scarce food: Conserves energy by not chasing distant/low-value food
        - Low competition: Can afford to be selective about food quality

    Evolutionary Disadvantage:
        - Very scarce food: May starve waiting for "good enough" food
        - High competition: Competitors eat food before this fish decides
        - Unpredictable food spawns: Selectivity may miss opportunities

    Parameters:
        min_food_value_ratio (float): Minimum food value to pursue (0-1). Range: [0.3-0.8], Default: 0.5
        max_pursuit_distance (float): Maximum distance to chase food. Range: [50-200], Default: 120
        urgency_threshold (float): Energy level to abandon selectivity. Range: [20-40], Default: 30

    Example Scenarios:
        - High energy, nearby high-value food: Pursue aggressively
        - High energy, nearby low-value food: Ignore, wait for better
        - Low energy, any nearby food: Abandon selectivity, eat anything
        - No nearby food: Gentle patrol to find food
    """

    def __init__(self, **kwargs):
        algorithm_id = "selective_food_seeker"
        default_parameters = {
            "min_food_value_ratio": 0.5,      # Only pursue food worth at least 50% of max
            "max_pursuit_distance": 120.0,    # Don't chase food beyond this distance
            "urgency_threshold": 30.0,        # Below this energy, eat anything
        }
        super().__init__(algorithm_id, default_parameters, **kwargs)

    def execute(self, fish) -> Tuple[float, float]:
        """
        Pursue food only when it's nearby AND valuable, conserve energy otherwise.
        """
        position = fish.position
        current_energy = fish.energy

        # CRITICAL ENERGY: Abandon selectivity, eat anything!
        if current_energy < self.parameters["urgency_threshold"]:
            nearest_food = self._find_nearest(position, fish.visible_food)
            if nearest_food:
                dx = nearest_food.position.x - position.x
                dy = nearest_food.position.y - position.y
                return self._safe_normalize(dx, dy)

        # SELECTIVE MODE: Only pursue high-value nearby food
        if fish.visible_food:
            # Filter food by value and distance
            max_distance = self.parameters["max_pursuit_distance"]
            min_value = self.parameters["min_food_value_ratio"]

            # Find best food that meets criteria
            best_food = None
            best_score = 0.0

            for food in fish.visible_food:
                # Calculate distance
                dx = food.position.x - position.x
                dy = food.position.y - position.y
                distance = (dx * dx + dy * dy) ** 0.5

                # Skip if too far
                if distance > max_distance:
                    continue

                # Estimate food value (0-1 scale, higher is better)
                # In actual implementation, food items have energy values
                # For now, assume all food is worth pursuing if criteria met
                food_value = 1.0  # Placeholder - actual food has .energy_value

                # Skip if not valuable enough
                if food_value < min_value:
                    continue

                # Score = value / distance (closer + more valuable = better)
                score = food_value / max(distance, 1.0)

                if score > best_score:
                    best_score = score
                    best_food = food

            # Pursue best food if found
            if best_food:
                dx = best_food.position.x - position.x
                dy = best_food.position.y - position.y
                return self._safe_normalize(dx, dy)

        # NO GOOD FOOD: Gentle patrol to find opportunities
        # Don't stay still (wastes time), don't burn energy (expensive)
        import random
        dx = random.uniform(-0.3, 0.3)
        dy = random.uniform(-0.3, 0.3)
        return self._safe_normalize(dx, dy)
```

### Register the New Behavior

```python
# In core/algorithms/__init__.py, add:
from core.algorithms.food_seeking import SelectiveFoodSeeker

ALL_ALGORITHMS = [
    # ... existing algorithms ...
    SelectiveFoodSeeker,
]
```

```python
# In core/algorithms/base.py, add bounds:
ALGORITHM_PARAMETER_BOUNDS = {
    # ... existing bounds ...
    "selective_food_seeker": {
        "min_food_value_ratio": (0.3, 0.8),
        "max_pursuit_distance": (50.0, 200.0),
        "urgency_threshold": (20.0, 40.0),
    },
}
```

```python
# In core/constants.py, update count:
TOTAL_ALGORITHM_COUNT = 49  # Was 48, now 49
```

---

## Step 5: Test and Compare

Run the simulation again with the new behavior:

```bash
# Run with same seed for fair comparison
python main.py --headless \
  --max-frames 10000 \
  --stats-interval 1000 \
  --export-stats improved_run.json \
  --seed 42
```

### Compare Results

**Baseline (baseline_run.json):**
```
EnergyConserver: reproduction_rate = 1.8
GreedyFoodSeeker: reproduction_rate = 0.4
Total unique algorithms in population: 12/48
```

**After Adding SelectiveFoodSeeker (improved_run.json):**
```
SelectiveFoodSeeker: reproduction_rate = 2.1  # <-- BEST!
EnergyConserver: reproduction_rate = 1.6      # <-- Still good
GreedyFoodSeeker: reproduction_rate = 0.3     # <-- Declining
Total unique algorithms in population: 13/49  # <-- New behavior established
```

**Result**: SelectiveFoodSeeker outcompetes both extremes!

### Why Did It Succeed?

Looking at death causes:
```json
{
  "selective_food_seeker": {
    "death_breakdown": {
      "starvation": 3,        # Very low!
      "old_age": 28,          # Most fish live full lives
      "predation": 4
    },
    "energy_efficiency": 22.1,  # Higher than both competitors
    "avg_lifespan": 2100        # Longest lifespan
  }
}
```

**Key success factors:**
1. **Energy efficient**: Doesn't waste energy on low-value food
2. **Opportunistic**: Still actively feeds when opportunities arise
3. **Adaptive**: Switches to survival mode at low energy
4. **Balanced**: Not too aggressive, not too passive

---

## Step 6: Iterate

Now that we have a successful behavior, we can:

### 6.1 Optimize Parameters

Run multiple simulations with different starting parameters:

```bash
# Test with more selective parameters
# Modify default_parameters in the behavior code, then:
python main.py --headless --max-frames 10000 --export-stats selective_v2.json --seed 100

# Test with less selective parameters
# Modify defaults again, then:
python main.py --headless --max-frames 10000 --export-stats selective_v3.json --seed 200
```

### 6.2 Create Variations

Based on SelectiveFoodSeeker's success, create related behaviors:

**SelectiveSchooler**: Only join schools when safe energy level, avoid when hungry
**SelectivePokerPlayer**: Only play poker when high energy and good position
**AdaptiveSelector**: Adjusts selectivity based on food availability

### 6.3 Identify New Gaps

With SelectiveFoodSeeker dominating, look for counters:

- What if food becomes more scarce? (Test with modified food spawn rates)
- What about high competition scenarios? (Test with higher max population)
- Can a behavior exploit SelectiveFoodSeeker's "waiting" behavior?

### 6.4 Long-Term Evolution

Run extended simulations to see how parameters evolve:

```bash
# Run for 100,000 frames to see multiple generations
python main.py --headless \
  --max-frames 100000 \
  --stats-interval 5000 \
  --export-stats evolution_longrun.json \
  --seed 42
```

**Watch for:**
- Parameter convergence (do all SelectiveFoodSeeker fish evolve toward similar values?)
- Frequency-dependent selection (does behavior perform worse when common?)
- Environmental adaptation (do parameters shift over time?)

---

## Real-World LLM Workflow

Here's how an LLM would use this system to evolve behaviors:

### Input to LLM:
```
Here's the stats from our last simulation run:

[Paste JSON from export-stats]

Based on this data:
1. Which behaviors are most successful and why?
2. Which behaviors are failing and what's the main cause?
3. What niches are unexploited?
4. What new behavior would you propose to fill a gap?
5. Provide complete code for the new behavior following the template.
```

### LLM Response Example:
```
Analysis:
1. Top performers: EnergyConserver (1.8 reproduction rate)
2. Failing: GreedyFoodSeeker (0.4 rate, 74% starvation deaths)
3. Gap: No behavior balances efficiency with opportunistic feeding
4. Proposal: SelectiveFoodSeeker - only pursue nearby high-value food

[Complete code follows...]
```

### Workflow Loop:
```
1. Run simulation → Export stats
2. Feed stats to LLM → Get behavior proposal
3. Implement proposed behavior → Add to codebase
4. Run simulation → Compare performance
5. If successful, LLM proposes variations
6. If unsuccessful, LLM analyzes why and proposes fix
7. Repeat
```

---

## Tips for Success

### 1. Use Consistent Seeds
Always use the same seed when comparing behaviors:
```bash
--seed 42  # Use same seed for all comparison runs
```

### 2. Run Long Enough
Ensure enough generations for selection pressure:
- Minimum: 5,000 frames (few generations)
- Recommended: 10,000 frames (clear patterns)
- Long-term: 50,000+ frames (parameter evolution visible)

### 3. Analyze Multiple Metrics
Don't just look at reproduction rate:
- **Survival rate**: % of fish that reproduce before dying
- **Energy efficiency**: Food eaten per fish
- **Death causes**: What kills this behavior?
- **Lifespan**: Do fish live long lives?

### 4. Document Hypotheses
Before creating a behavior, write down:
- What problem it solves
- Why existing behaviors fail at this
- Expected trade-offs
- Predictions for success metrics

### 5. Compare Apples to Apples
When testing changes:
- Use same seed
- Use same frame count
- Use same environment settings
- Only change the behavior being tested

---

## Conclusion

The Tank simulation is a laboratory for code evolution. By:
1. Running simulations to gather data
2. Analyzing which strategies succeed/fail
3. Creating new behaviors based on insights
4. Testing and iterating

You (or an LLM) can discover optimal survival strategies that emerge from natural selection rather than explicit design.

**The goal is not to design the perfect behavior**, but to **create diverse behaviors with different trade-offs**, and let evolution discover which combinations work best in different conditions.

Happy evolving! 🐠🧬
