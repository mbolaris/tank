# Fish Evolution and Behavior System Improvements

This document describes the comprehensive improvements made to the fish evolution system and behavior algorithms.

## Table of Contents
1. [Evolution System Enhancements](#evolution-system-enhancements)
2. [Behavior Algorithm Enhancements](#behavior-algorithm-enhancements)
3. [New Systems](#new-systems)
4. [Algorithm Updates](#algorithm-updates)
5. [Usage Examples](#usage-examples)

---

## Evolution System Enhancements

### 1. Advanced Genetic Crossover

**Location:** `core/genetics/`

Implemented three crossover modes for more realistic genetic inheritance:

- **AVERAGING** (original): Simple average of parent traits
- **RECOMBINATION**: Randomly select genes from each parent with blending
- **DOMINANT_RECESSIVE**: Some genes are dominant over others

```python
from core.genetics import GeneticCrossoverMode

# Create offspring with recombination
offspring = Genome.from_parents(
    parent1, parent2,
    crossover_mode=GeneticCrossoverMode.RECOMBINATION
)
```

### 2. Fitness Tracking

Fish now accumulate a fitness score based on:
- Food eaten: +2.0 per food item
- Survival time: +0.01 per frame
- Reproductions: +50.0 per offspring
- Energy maintenance: +0.1 * energy_ratio per frame

The fitness score influences mate selection and can be used for evolutionary analysis.

### 3. Mate Selection

Fish now evaluate potential mates based on:
- **Fitness score**: Prefer mates with higher fitness
- **Size similarity**: Optionally prefer similar-sized mates
- **Color diversity**: Optionally prefer different colors
- **Genetic diversity**: Prefer mates with different traits

Compatibility score (0.0-1.0) determines mating probability, with minimum 30% acceptance to prevent population bottlenecks.

### 4. Trait Linkage

Related traits now evolve together:
- **Speed ↔ Metabolism**: Faster fish have higher metabolism (realistic trade-off)
- Linked traits create more coherent evolutionary strategies

### 5. Epigenetic Effects

Environmental stress can affect offspring through epigenetic modifiers:
- Modifiers decay by 50% each generation
- Allow rapid adaptation to environmental changes
- Effects are heritable but temporary

### 6. Mate Preferences

Fish have evolvable mate preferences:
- `prefer_high_fitness`: Attraction to successful individuals
- `prefer_similar_size`: Preference for size matching
- `prefer_different_color`: Preference for genetic diversity
- `prefer_high_energy`: Preference for healthy mates

These preferences are inherited and mutate, allowing sexual selection to evolve.

---

## Behavior Algorithm Enhancements

### Key Improvements Across All Algorithms

1. **Predictive Movement**: Algorithms can now predict where moving targets will be
2. **Enhanced Memory**: Fish remember food locations, danger zones, and safe areas
3. **Communication**: Fish can signal danger, food, and other information
4. **Learning**: Behaviors improve through success/failure tracking

### Updated Algorithms

#### GreedyFoodSeeker

**Enhancements:**
- Predictive interception of moving food
- Predictive predator avoidance
- Enhanced memory system for food locations
- Danger zone memory
- Adaptive chase distance based on energy state

**Key Features:**
```python
# Predicts where moving food will be
intercept_point, time = predict_intercept_point(
    fish_pos, fish_speed, food_pos, food_vel
)

# Remembers food hotspots
memory_system.add_memory(
    MemoryType.FOOD_LOCATION, food_pos, strength=0.8
)

# Uses best remembered location when hungry
best_memory = memory_system.get_best_memory(MemoryType.FOOD_LOCATION)
```

#### CooperativeForager

**Enhancements:**
- Broadcasts food discoveries to nearby fish
- Listens for food signals from other fish
- Broadcasts danger warnings
- Social tendency affects signal strength

**Key Features:**
```python
# Broadcast food discovery
communication_system.broadcast_signal(
    SignalType.FOOD_FOUND,
    sender_pos=fish.pos,
    target_location=food.pos,
    strength=fish.genome.behavioral.social_tendency.value,
    urgency=0.7
)

# Listen for nearby signals
food_signals = communication_system.get_nearby_signals(
    fish.pos, signal_type=SignalType.FOOD_FOUND
)
```

---

## New Systems

### 1. Enhanced Memory System

**Location:** `core/fish_memory.py`

Fish can now remember:
- Food locations with success/failure tracking
- Danger zones from predator encounters
- Safe zones where no threats exist
- Mate locations for breeding
- Successful paths through environment

**Features:**
- Memories decay over time
- Reinforcement learning (success strengthens memories)
- Capacity limits per memory type
- Spatial clustering (nearby memories merge)

**Usage:**
```python
from core.fish_memory import FishMemorySystem, MemoryType

# Add a memory
fish.memory_system.add_memory(
    MemoryType.FOOD_LOCATION,
    position=Vector2(100, 200),
    strength=1.0,
    metadata={'food_type': 'plant_food'}
)

# Find nearest memory
nearest = fish.memory_system.find_nearest_memory(
    MemoryType.FOOD_LOCATION,
    fish.pos,
    max_distance=150
)

# Get best memory (by success rate)
best = fish.memory_system.get_best_memory(MemoryType.FOOD_LOCATION)

# Track success/failure
fish.memory_system.remember_success(
    MemoryType.FOOD_LOCATION,
    location=food_eaten_pos,
    proximity_radius=50
)
```

### 2. Communication System

**Location:** `core/fish_communication.py`

Fish can broadcast and receive signals:

**Signal Types:**
- `DANGER_WARNING`: Alert others to predators
- `FOOD_FOUND`: Share food discoveries
- `MATING_CALL`: Attract potential mates
- `DISTRESS`: Call for help when under attack
- `ALL_CLEAR`: Indicate danger has passed
- `FOLLOW_ME`: Lead others to resources

**Features:**
- Signals have range based on strength and urgency
- Signals decay over time
- Social fish broadcast stronger signals
- Fish filter signals by relevance to their state

**Usage:**
```python
from core.fish_communication import SignalType

# Broadcast a signal
environment.communication_system.broadcast_signal(
    signal_type=SignalType.DANGER_WARNING,
    sender_pos=fish.pos,
    target_location=predator.pos,
    strength=1.0,
    urgency=1.0
)

# Get nearby signals
danger_signals = environment.communication_system.get_nearby_signals(
    position=fish.pos,
    signal_type=SignalType.DANGER_WARNING
)

# Get strongest signal
strongest = environment.communication_system.get_strongest_signal(
    position=fish.pos,
    signal_type=SignalType.FOOD_FOUND
)
```

### 3. Predictive Movement

**Location:** `core/predictive_movement.py`

Utilities for predicting and intercepting moving targets:

**Functions:**
- `predict_intercept_point()`: Calculate where to aim to intercept moving target
- `predict_position()`: Simple forward prediction
- `get_avoidance_direction()`: Optimal escape direction from moving threat
- `calculate_pursuit_angle()`: Angle to turn for pursuit
- `is_target_ahead()`: Check if target is in field of view
- `calculate_smooth_approach()`: Smooth deceleration when approaching target
- `calculate_circling_movement()`: Circle around a target at fixed radius

**Usage:**
```python
from core.predictive_movement import predict_intercept_point

# Predict interception
intercept_point, time_to_intercept = predict_intercept_point(
    fish_pos=fish.pos,
    fish_speed=fish.speed,
    target_pos=food.pos,
    target_vel=food.vel
)

if intercept_point:
    # Move to intercept point instead of current target position
    direction = (intercept_point - fish.pos).normalize()
```

---

## Algorithm Updates

All 48 behavior algorithms can now leverage the new systems:

### Memory-Enhanced Algorithms

Algorithms that benefit most from memory:
- `FoodMemorySeeker`: Now uses FishMemorySystem with success tracking
- `GreedyFoodSeeker`: Falls back to memories when no food visible
- `PatrolFeeder`: Remembers successful patrol waypoints
- All predator avoidance: Remember danger zones

### Communication-Enhanced Algorithms

Algorithms that use signals:
- `CooperativeForager`: Shares food discoveries and danger warnings
- All schooling algorithms: Can coordinate through signals
- Mating behaviors: Can broadcast mating calls

### Prediction-Enhanced Algorithms

Algorithms that predict movement:
- `GreedyFoodSeeker`: Intercepts moving food
- `CircularHunter`: Predicts food trajectory for circling
- All predator avoidance: Predicts threat movement
- `AmbushFeeder`: Predicts when food will enter strike zone

---

## Usage Examples

### Example 1: Creating a Fish with Enhanced Evolution

```python
from core.genetics import Genome, GeneticCrossoverMode

# Create parent fish
parent1_genome = Genome.random()
parent2_genome = Genome.random()

# Update fitness scores
parent1_genome.update_fitness(food_eaten=10, survived_frames=1000, reproductions=2)
parent2_genome.update_fitness(food_eaten=8, survived_frames=1200, reproductions=1)

# Check mate compatibility
compatibility = parent1_genome.calculate_mate_compatibility(parent2_genome)
print(f"Mate compatibility: {compatibility:.2f}")

# Create offspring with advanced crossover
offspring_genome = Genome.from_parents(
    parent1_genome,
    parent2_genome,
    population_stress=0.2,  # 20% population stress
    crossover_mode=GeneticCrossoverMode.RECOMBINATION
)

# Offspring inherits:
# - Recombined genes from parents
# - Epigenetic modifiers
# - Mate preferences
# - Starts with 0 fitness (must earn it)
```

### Example 2: Using Memory for Smarter Foraging

```python
from core.fish_memory import MemoryType

# When fish finds food
if nearest_food:
    fish.memory_system.add_memory(
        MemoryType.FOOD_LOCATION,
        nearest_food.pos,
        strength=1.0
    )

# When fish eats food successfully
fish.memory_system.remember_success(
    MemoryType.FOOD_LOCATION,
    food_eaten_pos,
    proximity_radius=50
)

# When searching for food
if fish.is_low_energy():
    best_memory = fish.memory_system.get_best_memory(MemoryType.FOOD_LOCATION)
    if best_memory and best_memory.success_count > 0:
        # Go to location with proven success
        direction = (best_memory.location - fish.pos).normalize()
```

### Example 3: Communication Between Fish

```python
from core.fish_communication import SignalType, fish_should_respond_to_signal

# Fish A finds food
environment.communication_system.broadcast_signal(
    SignalType.FOOD_FOUND,
    sender_pos=fish_a.pos,
    target_location=food.pos,
    strength=fish_a.genome.behavioral.social_tendency.value,  # Social fish signal stronger
    urgency=0.7
)

# Fish B hears the signal
nearby_signals = environment.communication_system.get_nearby_signals(
    fish_b.pos,
    signal_type=SignalType.FOOD_FOUND
)

for signal in nearby_signals:
    if fish_should_respond_to_signal(fish_b, signal):
        # Fish B follows the signal
        direction = (signal.target_location - fish_b.pos).normalize()
```

### Example 4: Predictive Hunting

```python
from core.predictive_movement import predict_intercept_point

# Fish tracking moving food
nearest_food = find_nearest(fish, Food)
if nearest_food and nearest_food.vel.length() > 0.1:
    # Predict interception
    intercept_point, time_to_intercept = predict_intercept_point(
        fish.pos,
        fish.speed,
        nearest_food.pos,
        nearest_food.vel
    )

    if intercept_point and time_to_intercept < 60:  # Within 2 seconds
        # Aim for intercept point
        direction = (intercept_point - fish.pos).normalize()
        # Adjust speed based on time to intercept
        speed_multiplier = 1.0 if time_to_intercept > 30 else 1.3
    else:
        # Can't intercept - aim for current position
        direction = (nearest_food.pos - fish.pos).normalize()
        speed_multiplier = 1.0
```

---

## Performance Impact

### Computational Costs

The new systems add minimal overhead:
- **Memory System**: O(M) per fish, where M = memories per type (~10)
- **Communication System**: O(S) global, where S = active signals (~50)
- **Fitness Tracking**: O(1) per fish per frame
- **Predictive Movement**: O(1) calculations when needed

### Memory Usage

- Memory system: ~200 bytes per fish (10 memories × ~20 bytes)
- Communication system: ~5KB total (50 signals × ~100 bytes)
- Fitness tracking: ~40 bytes per fish (new genome fields)

**Total overhead: ~250 bytes per fish + 5KB global**

### Optimization Tips

1. **Limit signal broadcasts**: Only broadcast important events
2. **Tune memory decay**: Faster decay = less memory usage
3. **Use predictive movement selectively**: Only for moving targets
4. **Batch memory updates**: Update every N frames instead of every frame

---

## Evolutionary Implications

These improvements enable:

### Short-term Evolution (within simulation)
- **Fitness-based selection**: Successful fish reproduce more
- **Sexual selection**: Mate preferences can drive trait evolution
- **Behavioral optimization**: Algorithm parameters improve over time
- **Memory-based learning**: Individuals improve within lifetime

### Long-term Evolution (across generations)
- **Trait linkage**: Coherent evolutionary strategies emerge
- **Epigenetic adaptation**: Rapid response to environmental shifts
- **Communication evolution**: Social behaviors can evolve and spread
- **Predictive abilities**: Fish evolve better prediction parameters

### Population Dynamics
- **Mate selectivity**: Prevents genetic degradation
- **Adaptive mutations**: Population stress increases mutation rates
- **Behavioral diversity**: 48 algorithms maintain strategic diversity
- **Cooperative strategies**: Communication enables group behaviors

---

## Future Enhancement Possibilities

Potential additions to consider:

1. **Speciation**: Fish could diverge into distinct species
2. **Cultural transmission**: Learned behaviors passed socially, not genetically
3. **Tool use**: Fish could learn to manipulate environment
4. **Personality**: Persistent behavioral traits beyond genetics
5. **Territorial behavior**: Fish claim and defend regions
6. **Pack hunting**: Coordinated multi-fish predation
7. **Migration patterns**: Seasonal movement behaviors
8. **Sleep/rest cycles**: Energy conservation through inactivity periods

---

## Summary

This update transforms the fish from simple reactive agents into:
- **Intelligent foragers** with memory and prediction
- **Social creatures** that communicate and cooperate
- **Evolutionary subjects** with realistic genetics and selection
- **Learning organisms** that improve through experience

The combination of enhanced evolution and sophisticated behaviors creates a rich ecosystem where complex strategies can emerge and evolve over time.
