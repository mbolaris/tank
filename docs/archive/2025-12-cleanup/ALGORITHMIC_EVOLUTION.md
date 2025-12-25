# Algorithmic Evolution System

## Overview

The fish tank simulation now features a sophisticated **Algorithmic Evolution System** with **48 parametrizable behavior algorithms** that fish can inherit and evolve through reproduction.

## What is Algorithmic Evolution?

Instead of relying solely on neural networks or hardcoded rules, fish can now inherit specific **behavior algorithms** with tunable parameters. These algorithms evolve over generations through:

1. **Inheritance**: Offspring inherit their parent's algorithm type
2. **Parameter Mutation**: Algorithm parameters mutate during reproduction
3. **Natural Selection**: Better-performing algorithms survive and spread

## The 48 Behavior Algorithms

### Food Seeking Algorithms (12)
1. **GreedyFoodSeeker** - Always move directly toward nearest food
2. **EnergyAwareFoodSeeker** - Seek food more aggressively when energy is low
3. **OpportunisticFeeder** - Only pursue food if it's close enough
4. **FoodQualityOptimizer** - Prefer high-value food types
5. **AmbushFeeder** - Wait in one spot for food to come close
6. **PatrolFeeder** - Patrol in a pattern looking for food
7. **SurfaceSkimmer** - Stay near surface to catch falling food
8. **BottomFeeder** - Stay near bottom to catch sinking food
9. **ZigZagForager** - Move in zigzag pattern to maximize food discovery
10. **CircularHunter** - Circle around food before striking
11. **FoodMemorySeeker** - Remember where food was found before
12. **CooperativeForager** - Follow other fish to food sources

### Predator Avoidance Algorithms (10)
1. **PanicFlee** - Flee directly away from predators at maximum speed
2. **StealthyAvoider** - Move slowly and carefully away from predators
3. **FreezeResponse** - Freeze when predator is near
4. **ErraticEvader** - Make unpredictable movements when threatened
5. **VerticalEscaper** - Escape vertically when threatened
6. **GroupDefender** - Stay close to group for safety
7. **SpiralEscape** - Spiral away from predators
8. **BorderHugger** - Move to tank edges when threatened
9. **PerpendicularEscape** - Escape perpendicular to predator's approach
10. **DistanceKeeper** - Maintain safe distance from predators

### Schooling/Social Algorithms (10)
1. **TightScholer** - Stay very close to school members
2. **LooseScholer** - Maintain loose association with school
3. **LeaderFollower** - Follow the fastest/strongest fish
4. **AlignmentMatcher** - Match velocity with nearby fish
5. **SeparationSeeker** - Avoid crowding neighbors
6. **FrontRunner** - Lead the school from the front
7. **PerimeterGuard** - Stay on the outside of the school
8. **MirrorMover** - Mirror the movements of nearby fish
9. **BoidsBehavior** - Classic boids algorithm (separation, alignment, cohesion)
10. **DynamicScholer** - Switch between tight and loose schooling based on conditions

### Energy Management Algorithms (8)
1. **EnergyConserver** - Minimize movement to conserve energy
2. **BurstSwimmer** - Alternate between bursts of activity and rest
3. **OpportunisticRester** - Rest when no food or threats nearby
4. **EnergyBalancer** - Balance energy expenditure with reserves
5. **SustainableCruiser** - Maintain steady, sustainable pace
6. **StarvationPreventer** - Prioritize food when energy gets low
7. **MetabolicOptimizer** - Adjust activity based on metabolic efficiency
8. **AdaptivePacer** - Adapt speed based on current energy and environment

### Territory/Exploration Algorithms (8)
1. **TerritorialDefender** - Defend a territory from other fish
2. **RandomExplorer** - Explore randomly, covering new ground
3. **WallFollower** - Follow along tank walls
4. **CornerSeeker** - Prefer staying in corners
5. **CenterHugger** - Stay near the center of the tank
6. **RoutePatroller** - Patrol between specific waypoints
7. **BoundaryExplorer** - Explore edges and boundaries
8. **NomadicWanderer** - Wander continuously without a home base

## How It Works

### 1. Genome Integration

Each fish's `Genome` now includes a `behavior_algorithm` field:

```python
from core.genetics import Genome

# Create genome with random behavior algorithm
genome = Genome.random(use_algorithm=True)

# The genome now has a behavior algorithm with parameters
print(genome.behavioral.behavior_algorithm.value.algorithm_id)
print(genome.behavioral.behavior_algorithm.value.parameters)
```

### 2. Algorithm Parameters

Each algorithm has tunable parameters that affect its behavior:

```python
# Example: GreedyFoodSeeker
{
    "speed_multiplier": 0.95,     # How fast to pursue food
    "detection_range": 0.73       # How far to detect food
}

# Example: EnergyAwareFoodSeeker
{
    "urgency_threshold": 0.52,    # Energy level to become urgent
    "calm_speed": 0.48,           # Speed when energy is high
    "urgent_speed": 1.12          # Speed when energy is low
}
```

### 3. Inheritance with Mutation

When fish reproduce, offspring inherit their parent's algorithm with parameter mutations:

```python
# During reproduction
offspring_genome = Genome.from_parents(parent1, parent2)

# Offspring inherits parent's algorithm type
# Parameters are mutated slightly:
# parent: {"speed_multiplier": 0.95}
# child:  {"speed_multiplier": 0.98}  # mutated!
```

### 4. Movement Strategy

Fish with algorithms use the `AlgorithmicMovement` strategy:

```python
from movement_strategy import AlgorithmicMovement

fish = Fish(
    environment=env,
    movement_strategy=AlgorithmicMovement(),
    genome=genome_with_algorithm
)
```

## Evolution in Action

Over generations, you'll observe:

1. **Algorithm Diversity**: Different algorithms compete for survival
2. **Parameter Optimization**: Parameters evolve toward optimal values
3. **Niche Specialization**: Different algorithms dominate different environments
4. **Population Dynamics**: Some algorithms spread, others go extinct

## Future: LLM-Based Sexual Reproduction

**Coming soon**: An LLM agent will combine and enhance two parent algorithms to create novel offspring behaviors based on performance data!

```python
# Future feature (not yet implemented)
def llm_combine_algorithms(parent1_algo, parent2_algo, performance_data):
    """Use LLM to create innovative hybrid algorithm."""
    # LLM analyzes both algorithms
    # Combines their strengths
    # Creates new algorithm for offspring
    return innovative_offspring_algorithm
```

## Configuration

### Enable/Disable Algorithmic Fish

In `fishtank.py`, you can adjust the number of algorithmic fish:

```python
# Create more algorithmic fish
for i in range(10):  # Changed from 5
    genome = Genome.random(use_brain=False, use_algorithm=True)
    fish = Fish(env, AlgorithmicMovement(), ...)
```

### Mutation Rates

Adjust mutation rates in `genetics.py`:

```python
# Higher mutation = more variation
offspring = Genome.from_parents(
    parent1, parent2,
    mutation_rate=0.2,      # 20% chance per parameter
    mutation_strength=0.15  # ±15% variation
)
```

## Technical Details

### File Structure

- **`behavior_algorithms.py`**: All 48 algorithm implementations
- **`genetics.py`**: Updated `Genome` class with algorithm support
- **`movement_strategy.py`**: New `AlgorithmicMovement` strategy
- **`fishtank.py`**: Updated to create algorithmic fish

### Adding New Algorithms

To add your own algorithm:

```python
from behavior_algorithms import BehaviorAlgorithm

@dataclass
class MyCustomAlgorithm(BehaviorAlgorithm):
    """My custom behavior."""

    def __init__(self):
        super().__init__(
            algorithm_id="my_custom_algorithm",
            parameters={
                "param1": random.uniform(0.5, 1.5),
                "param2": random.uniform(0.0, 1.0),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        # Your behavior logic here
        vx = self.parameters["param1"]
        vy = self.parameters["param2"]
        return vx, vy

# Add to registry
ALL_ALGORITHMS.append(MyCustomAlgorithm)
```

## Performance

The algorithmic system is:
- **Fast**: Direct Python execution (no neural network overhead)
- **Interpretable**: Each algorithm's behavior is clear and debuggable
- **Evolvable**: Parameters can be optimized through natural selection
- **Diverse**: 48 different strategies create rich ecosystem dynamics

## Comparison with Other Systems

| Feature | Neural Networks | Rule-Based | **Algorithmic Evolution** |
|---------|----------------|------------|--------------------------|
| Interpretability | Low | High | **High** |
| Diversity | Medium | Low | **Very High** |
| Evolution | Weights | None | **Parameters** |
| Performance | Slow | Fast | **Fast** |
| Variety | Limited | Limited | **48 Algorithms!** |

## Examples

### Example 1: Energy-Efficient Fish

A fish with `EnergyConserver` algorithm + low `metabolism_rate` might:
- Survive longer on less food
- Move slowly but efficiently
- Dominate in low-food environments

### Example 2: Aggressive Hunter

A fish with `GreedyFoodSeeker` + high `speed_multiplier` might:
- Find food faster
- Consume more energy
- Thrive in abundant-food environments

### Example 3: Social Survivor

A fish with `TightScholer` + `GroupDefender` traits might:
- Avoid predators effectively
- Compete poorly for food
- Succeed through safety in numbers

## Metrics & Analysis

Track algorithm success by monitoring:
- **Survival rate** by algorithm type
- **Reproduction rate** per algorithm
- **Parameter drift** over generations
- **Algorithm extinction** events
- **Dominant strategies** emergence

## Conclusion

The Algorithmic Evolution System brings unprecedented diversity and sophistication to the fish tank simulation. With 48 different strategies and parametrizable behaviors, every simulation run will produce unique evolutionary outcomes!

Watch as algorithms compete, adapt, and evolve in real-time! 🐠🧬
