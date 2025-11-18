# Behavior Algorithm Development Guide

## Overview

This is the **core of the Tank project**: evolving fish behavior algorithms through natural selection. This guide provides the standards and best practices for creating, documenting, and evolving behavior algorithms that can be mixed, matched, and parametrized as fish populations evolve.

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [Behavior Algorithm Structure](#behavior-algorithm-structure)
3. [Coding Standards](#coding-standards)
4. [Parameter Design](#parameter-design)
5. [Testing Your Behavior](#testing-your-behavior)
6. [Evolution & Mixing](#evolution--mixing)
7. [Performance Analysis](#performance-analysis)
8. [Example Workflow](#example-workflow)

---

## Core Concepts

### What is a Behavior Algorithm?

A **behavior algorithm** is a decision-making strategy that controls how a fish moves through the tank. Each fish inherits one algorithm from its parents, which can:

- **Mutate**: Parameters change slightly each generation
- **Cross over**: Blend parameters from two parents
- **Evolve**: Successful behaviors reproduce more, unsuccessful ones die out

### The Evolution Loop

```
1. Fish with behavior X survives and reproduces
2. Offspring inherit behavior X with small mutations
3. Different parameter values compete for survival
4. Over generations, optimal parameters emerge
5. Multiple behaviors coexist in the ecosystem
```

### Current Algorithm Count

**48 algorithms** across 5 categories:
- Food Seeking (12)
- Predator Avoidance (10)
- Schooling/Social (10)
- Energy Management (8)
- Territory/Exploration (8)
- Poker Interactions (5)

---

## Behavior Algorithm Structure

### Base Class Requirements

All behaviors must inherit from `BehaviorAlgorithm` in `/home/user/tank/core/algorithms/base.py`:

```python
from core.algorithms.base import BehaviorAlgorithm
from typing import Dict, Tuple, Optional

class MyNewBehavior(BehaviorAlgorithm):
    """
    CONCISE ONE-LINE DESCRIPTION OF STRATEGY

    This behavior [describe in 1-2 sentences what makes it unique].

    Evolutionary Advantage:
        - [Situation 1]: [Why this helps survival/reproduction]
        - [Situation 2]: [Why this helps survival/reproduction]

    Evolutionary Disadvantage:
        - [Situation 1]: [What vulnerabilities this creates]
        - [Situation 2]: [What trade-offs exist]

    Parameters:
        parameter_1 (float): [Purpose] Range: [min-max], Default: [value]
        parameter_2 (float): [Purpose] Range: [min-max], Default: [value]

    Example Scenarios:
        - High energy, food nearby: [Expected behavior]
        - Low energy, no food visible: [Expected behavior]
        - Predator threat detected: [Expected behavior]
    """

    def __init__(self, **kwargs):
        # REQUIRED: Set unique algorithm_id (lowercase_with_underscores)
        algorithm_id = "my_new_behavior"

        # REQUIRED: Define default parameters
        default_parameters = {
            "parameter_1": 1.0,      # [Purpose of parameter 1]
            "parameter_2": 0.5,      # [Purpose of parameter 2]
        }

        super().__init__(algorithm_id, default_parameters, **kwargs)

    def execute(self, fish) -> Tuple[float, float]:
        """
        REQUIRED: Main decision-making method called each frame.

        This method must return a normalized direction vector (velocity_x, velocity_y)
        representing the fish's desired movement direction this frame.

        Args:
            fish: The Fish entity executing this behavior
                  Available attributes:
                    - fish.position (Vector2): Current x, y position
                    - fish.velocity (Vector2): Current movement vector
                    - fish.energy (float): Current energy level
                    - fish.genome: Genetic traits (speed, size, vision_range, etc.)
                    - fish.visible_food (list): Food entities in vision range
                    - fish.visible_fish (list): Other fish in vision range
                    - fish.life_stage (str): "baby", "juvenile", "adult", "mature"
                    - fish.is_low_energy() (bool): Energy below threshold
                    - fish.is_critical_energy() (bool): Near starvation

        Returns:
            Tuple[float, float]: Normalized (velocity_x, velocity_y) direction vector
                                 Will be multiplied by fish's actual speed stat

        Helper Methods Available (injected by base class):
            - self._find_nearest(fish.position, entities_list) -> nearest_entity or None
            - self._safe_normalize(vector_x, vector_y) -> (normalized_x, normalized_y)
            - self._get_predator_threat(fish) -> (threat_x, threat_y) or (0, 0)

        Implementation Pattern:
            1. Gather context (energy, nearby entities, threats)
            2. Make decision based on parameters
            3. Calculate desired direction
            4. Return normalized direction vector
        """
        # Example implementation structure:

        # 1. GATHER CONTEXT
        # Get current state
        current_energy = fish.energy
        position = fish.position

        # Find relevant entities using helper methods
        nearest_food = self._find_nearest(position, fish.visible_food)

        # 2. MAKE DECISION using parameters
        if current_energy < 30:
            priority = "food"
        else:
            priority = "explore"

        # 3. CALCULATE DIRECTION
        if priority == "food" and nearest_food:
            # Move toward food
            dx = nearest_food.position.x - position.x
            dy = nearest_food.position.y - position.y
        else:
            # Default behavior
            dx, dy = 0, 0

        # 4. RETURN NORMALIZED DIRECTION
        # Use helper to safely normalize (handles zero vectors)
        return self._safe_normalize(dx, dy)
```

### Required Components

Every behavior algorithm MUST have:

1. **Unique `algorithm_id`**: Lowercase string with underscores (e.g., `"greedy_food_seeker"`)
2. **Default parameters dict**: All evolvable parameters with starting values
3. **`execute(fish)` method**: Returns `(velocity_x, velocity_y)` tuple
4. **Docstring**: Describing strategy, advantages, disadvantages, parameters

---

## Coding Standards

### 1. Docstring Format (CRITICAL FOR LLM ANALYSIS)

Use this exact structure for the class docstring:

```python
"""
ONE-LINE SUMMARY

Detailed description (1-2 sentences).

Evolutionary Advantage:
    - [Specific scenario]: [Why this helps]
    - [Specific scenario]: [Why this helps]

Evolutionary Disadvantage:
    - [Specific scenario]: [What cost/risk]
    - [Specific scenario]: [What cost/risk]

Parameters:
    param_name (type): Description. Range: [min-max], Default: value
    param_name (type): Description. Range: [min-max], Default: value

Example Scenarios:
    - [Condition]: [Expected behavior]
    - [Condition]: [Expected behavior]
"""
```

**Why this matters**: LLMs analyzing your behavior need to understand:
- When this behavior should thrive
- When it should struggle
- What parameters control what aspects
- How it behaves in different situations

### 2. Parameter Naming Conventions

Use descriptive, self-documenting parameter names:

✅ **Good**:
```python
"speed_multiplier"          # Clear what it affects
"detection_range_factor"    # Clear it modifies detection
"aggression_threshold"      # Clear it's a decision point
```

❌ **Bad**:
```python
"factor"                    # Too vague
"param1"                    # No meaning
"x"                         # Unclear purpose
```

### 3. Code Comments for Evolution

Add comments explaining **why** decisions matter for survival:

```python
def execute(self, fish):
    # SURVIVAL CRITICAL: Low energy fish must prioritize food over all else
    if fish.is_critical_energy():
        # At critical energy, ignore all other concerns
        nearest_food = self._find_nearest(fish.position, fish.visible_food)
        if nearest_food:
            # Direct path to food, no evasion
            dx = nearest_food.position.x - fish.position.x
            dy = nearest_food.position.y - fish.position.y
            return self._safe_normalize(dx, dy)

    # ENERGY EFFICIENCY: At safe energy, conserve by moving less
    if fish.energy > 60:
        # Reduce movement speed to save energy when well-fed
        # This parameter evolves optimal "cruising speed"
        movement_scale = self.parameters["energy_save_factor"]  # 0.5-0.8
        # ... rest of logic
```

### 4. Avoid Magic Numbers

Define constants or use parameters:

❌ **Bad**:
```python
if fish.energy < 25:  # Magic number!
    speed = 1.5       # Magic number!
```

✅ **Good**:
```python
# Use parameters that can evolve
critical_threshold = 25 * self.parameters["energy_threshold_factor"]
if fish.energy < critical_threshold:
    speed = self.parameters["panic_speed_multiplier"]
```

### 5. Fail-Safe Defaults

Always return a valid direction, even if logic fails:

```python
def execute(self, fish):
    dx, dy = 0, 0  # Safe default: stay still

    # Try complex logic
    target = self._find_best_target(fish)
    if target:
        dx = target.position.x - fish.position.x
        dy = target.position.y - fish.position.y
    else:
        # Fallback: gentle random drift
        import random
        dx = random.uniform(-0.1, 0.1)
        dy = random.uniform(-0.1, 0.1)

    return self._safe_normalize(dx, dy)  # Always normalize before returning
```

---

## Parameter Design

### What Makes Good Evolvable Parameters?

Parameters should control **trade-offs** that have different optimal values in different environments.

#### Example: Food Seeking Behavior

```python
default_parameters = {
    # DETECTION: Controls how far fish "sees" food
    # Trade-off: Larger range = more opportunities but more energy spent pursuing distant food
    "detection_range_factor": 1.0,  # Multiplies vision_range

    # PURSUIT: Controls how aggressively fish chases food
    # Trade-off: Higher speed = catch food faster but burn more energy
    "speed_multiplier": 1.0,        # Multiplies base speed

    # SELECTIVITY: Controls minimum food value to pursue
    # Trade-off: Being picky = higher quality but fewer opportunities
    "min_food_value": 0.3,          # 0.0-1.0, fraction of max food value

    # ABANDONMENT: Controls when to give up on distant food
    # Trade-off: Persistence vs. opportunity cost
    "max_pursuit_distance": 200.0,  # Pixels
}
```

### Parameter Bounds

Define realistic bounds in `/home/user/tank/core/algorithms/base.py`:

```python
ALGORITHM_PARAMETER_BOUNDS = {
    "my_new_behavior": {
        "detection_range_factor": (0.5, 2.0),   # Can evolve from half to double
        "speed_multiplier": (0.7, 1.5),         # 70% to 150% of base speed
        "min_food_value": (0.0, 0.8),           # Can't be too picky (0.8 max)
        "max_pursuit_distance": (50.0, 400.0),  # Min and max pursuit distance
    },
    # ...
}
```

### How Mutation Works

When fish reproduce, parameters mutate using `mutate_parameters()`:

```python
# Parent has: {"speed_multiplier": 1.0}
# Mutation: new_value = 1.0 + random(-0.1, 0.1) = 1.05
# Offspring has: {"speed_multiplier": 1.05}
```

Mutation strength is controlled globally but clamped to your bounds.

---

## Testing Your Behavior

### 1. Add to Algorithm Registry

Edit `/home/user/tank/core/algorithms/__init__.py`:

```python
# Import your new behavior
from core.algorithms.my_category import MyNewBehavior

# Add to ALL_ALGORITHMS list
ALL_ALGORITHMS = [
    # ... existing algorithms ...
    MyNewBehavior,
]
```

Update `TOTAL_ALGORITHM_COUNT` in `/home/user/tank/core/constants.py`:

```python
TOTAL_ALGORITHM_COUNT = 49  # Was 48, now 49
```

### 2. Run Headless Simulation

Test your behavior's performance:

```bash
python main.py --headless --max-frames 5000 --stats-interval 500 --seed 42
```

Watch for:
- Does your algorithm appear in "Unique Algorithms"?
- How many fish are using it over time?
- Birth/death rates compared to other algorithms
- Reproduction success rate

### 3. Export Performance Data

```bash
python main.py --headless --max-frames 10000 --export-stats results.json
```

This generates JSON with per-algorithm performance metrics you can analyze.

### 4. Analyze with Stats Script

```bash
python scripts/analyze_behavior_performance.py results.json
```

Look for:
- **Survival rate**: % of fish with this behavior that survive to reproduce
- **Reproduction rate**: Offspring per fish
- **Energy efficiency**: Energy gathered vs. energy spent
- **Population share**: % of total population using this behavior over time

---

## Evolution & Mixing

### How Behaviors Inherit

When two fish reproduce:

```python
# Option 1: Single parent (asexual)
offspring_behavior = inherit_algorithm_with_mutation(parent.genome.behavior_algorithm)

# Option 2: Two parents (sexual)
offspring_behavior = crossover_algorithms(parent1.genome.behavior_algorithm,
                                          parent2.genome.behavior_algorithm)

# Option 3: Weighted crossover (poker winner influence)
offspring_behavior = crossover_algorithms_weighted(winner_behavior, loser_behavior,
                                                   winner_weight=0.7)
```

### Parameter Crossover

```python
# Parent 1: {"speed_multiplier": 1.2, "detection_range": 0.8}
# Parent 2: {"speed_multiplier": 0.9, "detection_range": 1.1}

# Offspring (each parameter randomly from one parent):
# {"speed_multiplier": 1.2, "detection_range": 1.1}  # Got speed from P1, range from P2

# Then mutate:
# {"speed_multiplier": 1.25, "detection_range": 1.08}  # Small random changes
```

### Algorithm Switching

Fish can also switch algorithms entirely if parents have different behaviors:

```python
# Parent 1: GreedyFoodSeeker
# Parent 2: EnergyConserver
# Offspring: 50% chance of either, with mixed parameters
```

This allows **behavior diversity** to emerge and compete.

---

## Performance Analysis

### Key Metrics to Track

The simulation tracks these metrics per algorithm:

1. **Population Metrics**
   - `total_births`: How many fish spawned with this behavior
   - `total_deaths`: How many died
   - `current_population`: How many currently alive
   - `avg_lifespan`: Average frames survived

2. **Reproduction Metrics**
   - `total_reproductions`: Successful breeding events
   - `reproduction_rate`: Reproductions per birth
   - `survival_rate`: % that survive to reproduce

3. **Energy Metrics**
   - `total_food_eaten`: Food items consumed
   - `energy_efficiency`: Energy gained / energy spent

4. **Genetic Metrics**
   - `parameter_variance`: How diverse parameter values are
   - `extinction_events`: Times this algorithm went extinct then re-emerged

### What Makes a Successful Behavior?

A behavior is evolutionarily successful if:

1. **High reproduction rate**: Fish using it reproduce often
2. **Long lifespan**: Fish survive long enough to reproduce multiple times
3. **Energy efficiency**: Gathers more energy than it spends
4. **Consistent presence**: Maintains population share over time
5. **Adaptability**: Parameter diversity shows it works in various conditions

### Warning Signs of Poor Behavior

- **Rapid extinction**: Algorithm dies out within a few generations
- **Low energy**: Fish constantly near starvation
- **No reproduction**: Fish survive but never reproduce
- **High predation rate**: Fish get eaten more often than others
- **Declining population**: % of population decreasing over time

---

## Example Workflow: Creating a New Behavior

### Step 1: Identify a Niche

Look at current algorithm gaps:

```bash
# Run simulation and check diversity
python main.py --headless --max-frames 5000 --stats-interval 1000

# Look at "Unique Algorithms" - if it's low, there's room for new strategies
# Check algorithm performance report - find underserved niches
```

**Example niche**: "No behavior optimizes for nighttime feeding"

### Step 2: Design the Strategy

```
Behavior: NocturnalFeeder
Strategy: Conserve energy during day, feed aggressively at night
Parameters:
  - night_speed_boost: How much faster to move at night
  - day_rest_threshold: Energy level below which to feed even during day
  - circadian_sensitivity: How strongly to respond to day/night
```

### Step 3: Implement

Create `/home/user/tank/core/algorithms/food_seeking.py` addition:

```python
class NocturnalFeeder(BehaviorAlgorithm):
    """
    Feeds aggressively at night, conserves energy during day

    This behavior exploits the day/night cycle by resting when other fish
    are active (reducing competition) and feeding when most fish are slow.

    Evolutionary Advantage:
        - Night time: Less competition for food, can be more selective
        - Day time: Conserves energy while others burn it competing
        - Low competition environments: Can outcompete diurnal feeders

    Evolutionary Disadvantage:
        - High competition environments: May starve waiting for night
        - If most fish adopt this: Advantage disappears (frequency-dependent)
        - Inflexible: Can't respond to rare daytime opportunities

    Parameters:
        night_speed_boost (float): Speed multiplier at night. Range: [1.0-2.0], Default: 1.5
        day_rest_threshold (float): Energy level to feed during day. Range: [10-40], Default: 25
        circadian_sensitivity (float): Day/night response strength. Range: [0.5-1.5], Default: 1.0

    Example Scenarios:
        - Nighttime, high energy: Aggressively hunt food at boosted speed
        - Daytime, high energy: Minimal movement, conserve energy
        - Daytime, critical energy: Override circadian, feed anyway
    """

    def __init__(self, **kwargs):
        algorithm_id = "nocturnal_feeder"
        default_parameters = {
            "night_speed_boost": 1.5,
            "day_rest_threshold": 25.0,
            "circadian_sensitivity": 1.0,
        }
        super().__init__(algorithm_id, default_parameters, **kwargs)

    def execute(self, fish) -> Tuple[float, float]:
        """
        Feed aggressively at night, rest during day (unless energy critical).
        """
        # Get time of day from fish's environment
        time_of_day = fish.environment.time_system.get_time_of_day()
        is_night = time_of_day in ["night", "dusk", "dawn"]

        # CRITICAL OVERRIDE: Always feed if starving
        if fish.is_critical_energy():
            nearest_food = self._find_nearest(fish.position, fish.visible_food)
            if nearest_food:
                dx = nearest_food.position.x - fish.position.x
                dy = nearest_food.position.y - fish.position.y
                return self._safe_normalize(dx, dy)

        # NIGHT BEHAVIOR: Active feeding
        if is_night:
            nearest_food = self._find_nearest(fish.position, fish.visible_food)
            if nearest_food:
                # Calculate direction to food
                dx = nearest_food.position.x - fish.position.x
                dy = nearest_food.position.y - fish.position.y

                # Apply night speed boost via parameter
                # (actual speed multiplication happens in fish movement system)
                return self._safe_normalize(dx, dy)
            else:
                # No food visible, patrol slowly
                import random
                dx = random.uniform(-0.3, 0.3)
                dy = random.uniform(-0.3, 0.3)
                return self._safe_normalize(dx, dy)

        # DAY BEHAVIOR: Rest unless low energy
        else:
            if fish.energy < self.parameters["day_rest_threshold"]:
                # Energy getting low, feed cautiously
                nearest_food = self._find_nearest(fish.position, fish.visible_food)
                if nearest_food:
                    dx = nearest_food.position.x - fish.position.x
                    dy = nearest_food.position.y - fish.position.y
                    # Reduced speed (no boost) during day
                    return self._safe_normalize(dx * 0.5, dy * 0.5)

            # High energy during day: minimal movement
            return (0.0, 0.0)
```

### Step 4: Register and Test

```python
# In core/algorithms/__init__.py
from core.algorithms.food_seeking import NocturnalFeeder

ALL_ALGORITHMS = [
    # ...
    NocturnalFeeder,
]
```

```python
# In core/algorithms/base.py
ALGORITHM_PARAMETER_BOUNDS = {
    # ...
    "nocturnal_feeder": {
        "night_speed_boost": (1.0, 2.0),
        "day_rest_threshold": (10.0, 40.0),
        "circadian_sensitivity": (0.5, 1.5),
    },
}
```

```bash
# Run test
python main.py --headless --max-frames 10000 --export-stats nocturnal_test.json
```

### Step 5: Analyze Results

```bash
# Check if nocturnal_feeder appears and how it performs
python scripts/analyze_behavior_performance.py nocturnal_test.json --algorithm nocturnal_feeder
```

Look for:
- Does it maintain population presence?
- Higher survival during night cycles?
- Good reproduction rate?
- Energy efficiency compared to diurnal feeders?

### Step 6: Iterate

Based on results:
- Adjust parameter bounds if values hit limits
- Tweak default parameters if behavior too weak/strong
- Modify logic if behavior doesn't work as intended
- Add safety checks if fish die unexpectedly

---

## Advanced Topics

### Context-Aware Behaviors

Access environmental context:

```python
def execute(self, fish):
    # Time of day
    time = fish.environment.time_system.get_time_of_day()

    # Population density (via spatial grid)
    nearby_fish_count = len(fish.visible_fish)

    # Food availability
    food_scarcity = 1.0 - (len(fish.visible_food) / 10.0)  # Normalize

    # Adapt behavior based on context
    if food_scarcity > 0.7:
        # Scarce food: be more aggressive
        pass
    elif nearby_fish_count > 8:
        # Crowded: use different strategy
        pass
```

### Multi-Modal Behaviors

Combine multiple strategies with parameter-controlled blending:

```python
def execute(self, fish):
    # Get direction from food-seeking logic
    food_dx, food_dy = self._calculate_food_direction(fish)

    # Get direction from predator avoidance logic
    avoid_dx, avoid_dy = self._get_predator_threat(fish)

    # Blend based on energy (parameter controls blend ratio)
    if fish.is_low_energy():
        food_weight = self.parameters["hunger_priority"]  # 0.8
        avoid_weight = 1.0 - food_weight                   # 0.2
    else:
        food_weight = 0.3
        avoid_weight = 0.7

    # Weighted combination
    dx = food_dx * food_weight + avoid_dx * avoid_weight
    dy = food_dy * food_weight + avoid_dy * avoid_weight

    return self._safe_normalize(dx, dy)
```

### Frequency-Dependent Selection

Some behaviors work well only when rare (or common):

```python
def execute(self, fish):
    # Count how many nearby fish have same algorithm
    same_behavior_count = sum(
        1 for other in fish.visible_fish
        if other.genome.behavior_algorithm.algorithm_id == self.algorithm_id
    )

    # Strategy: Be aggressive when rare, cautious when common
    if same_behavior_count < self.parameters["rarity_threshold"]:
        # Rare: exploit the niche aggressively
        aggression = self.parameters["rare_aggression"]
    else:
        # Common: too much competition, be conservative
        aggression = self.parameters["common_aggression"]

    # Use aggression in movement decisions...
```

---

## LLM Integration Points

### For LLM Analysis

When analyzing algorithm performance data, focus on:

1. **Extinction patterns**: Which behaviors die out and why?
2. **Parameter convergence**: Do parameters evolve toward specific values?
3. **Environmental sensitivity**: Do some behaviors only work in certain conditions?
4. **Interaction effects**: Do behaviors perform differently when others are present?

### For LLM Behavior Generation

When creating new behaviors:

1. **Identify gaps**: What environmental niches are unexploited?
2. **Propose trade-offs**: Every advantage should have a corresponding cost
3. **Design parameters**: 3-5 evolvable parameters controlling key trade-offs
4. **Predict outcomes**: Expected survival/reproduction rates
5. **Set bounds**: Realistic min/max for each parameter

### For LLM Behavior Improvement

When improving existing behaviors:

1. **Analyze failures**: Why did fish with this behavior die?
2. **Propose modifications**: Specific parameter adjustments or logic changes
3. **A/B test**: Run simulations with old vs. new version
4. **Compare metrics**: Survival rate, reproduction rate, energy efficiency
5. **Iterate**: Refine based on results

---

## Quick Reference

### File Locations

- **Behavior algorithms**: `/home/user/tank/core/algorithms/*.py`
- **Base class**: `/home/user/tank/core/algorithms/base.py`
- **Registry**: `/home/user/tank/core/algorithms/__init__.py`
- **Parameter bounds**: `/home/user/tank/core/algorithms/base.py` (ALGORITHM_PARAMETER_BOUNDS)
- **Constants**: `/home/user/tank/core/constants.py`

### Key Methods

- `execute(fish)`: Main behavior logic, returns (vx, vy)
- `mutate_parameters(rate, strength)`: Inherited from base, handles mutation
- `_find_nearest(position, entities)`: Helper to find closest entity
- `_safe_normalize(dx, dy)`: Helper to normalize vector safely
- `_get_predator_threat(fish)`: Helper to get predator avoidance vector

### Testing Commands

```bash
# Basic headless run
python main.py --headless --max-frames 5000

# With stats export
python main.py --headless --max-frames 10000 --export-stats output.json

# With fixed seed (reproducible)
python main.py --headless --max-frames 5000 --seed 42

# Custom stats interval
python main.py --headless --max-frames 5000 --stats-interval 500
```

### Analysis Commands

```bash
# Analyze performance data
python scripts/analyze_behavior_performance.py results.json

# Compare two runs
python scripts/compare_simulations.py run1.json run2.json

# Visualize evolution
python scripts/plot_evolution.py results.json
```

---

## Contributing New Behaviors

When contributing a new behavior algorithm:

1. ✅ Follow the docstring format exactly
2. ✅ Use descriptive parameter names
3. ✅ Add parameter bounds to `ALGORITHM_PARAMETER_BOUNDS`
4. ✅ Register in `ALL_ALGORITHMS` list
5. ✅ Update `TOTAL_ALGORITHM_COUNT`
6. ✅ Test with at least 5000 frame simulation
7. ✅ Document evolutionary advantages/disadvantages
8. ✅ Provide example scenarios in docstring
9. ✅ Include fail-safe default behavior
10. ✅ Add comments explaining survival-critical decisions

---

## Conclusion

The Tank project is a **code evolution laboratory**. Each behavior algorithm you create is a hypothesis about survival strategies. The simulation tests these hypotheses through natural selection, mixing successful behaviors and eliminating unsuccessful ones.

**Your role as a developer** (human or LLM) is to:
1. Propose diverse survival strategies
2. Implement them with evolvable parameters
3. Observe which strategies succeed
4. Learn from the results
5. Create new, better strategies based on insights

**The goal**: Discover emergent optimal behaviors that no human explicitly designed, but that evolved through the process of variation, selection, and inheritance.

Happy evolving! 🐠🧬
