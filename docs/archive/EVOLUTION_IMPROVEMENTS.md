# Evolution System Improvements

## Summary

This update fixes critical bugs and enhances the genetic evolution system to enable robust behavioral evolution through tunable algorithms.

## Issues Fixed

### 1. Energy Economy Bug (Critical Fix)

**Problem:** Total system energy jumped by ~2000 when fish reproduced
- Baby fish were created with 50% of max energy (~55 energy)
- Parent only paid 10 energy for mating
- **Net energy gain per birth: +45 energy**
- When ~44 fish bred simultaneously → +2000 energy spike

**Solution:** Energy transfer from parent to offspring
- Parent now transfers 30% of their current energy to baby
- Parent pays: 10 (mating cost) + 30% of energy (transfer)
- Baby receives: **ONLY** the transferred energy (no free energy)
- **Net energy change per birth: -10 energy** (sustainable!)

**Impact:**
- Energy is now conserved (only mating cost is lost)
- No more unrealistic energy spikes
- Reproduction is a real survival cost
- More realistic population dynamics

### 2. Algorithm Evolution Enhancement

**Previous Behavior:**
- Offspring inherited algorithm from **ONE parent only**
- No parameter blending between parents
- Limited genetic diversity

**New Behavior: Full Crossover**
- Offspring can inherit from **BOTH parents**
- When parents have same algorithm: **parameters blend**
- When parents have different algorithms: 50/50 inheritance
- 5% chance of algorithm mutation (switch to random)

**Example:**
```
Parent 1: GreedyFoodSeeker (speed=0.8, detection=0.6)
Parent 2: GreedyFoodSeeker (speed=1.2, detection=0.9)
Offspring: GreedyFoodSeeker (speed=1.0, detection=0.75)  # Blended!
```

## Current Evolution System Status

### Behavior Algorithm Gene Pool

The system includes **53 tunable behavior algorithms** organized into 6 categories:

#### 1. Food Seeking (12 algorithms)
- `GreedyFoodSeeker`: Direct pursuit of nearest food
- `EnergyAwareFoodSeeker`: Urgency based on energy level
- `OpportunisticFeeder`: Only pursue close food
- `FoodQualityOptimizer`: Prefer high-value food
- `AmbushFeeder`: Wait for food to come close
- `PatrolFeeder`: Systematic area coverage
- `SurfaceSkimmer`: Stay near surface for falling food
- `BottomFeeder`: Scavenge sinking food
- `ZigZagForager`: Maximize discovery area
- `CircularHunter`: Circle before striking
- `FoodMemorySeeker`: Return to known food locations
- `CooperativeForager`: Follow others to food

#### 2. Predator Avoidance (10 algorithms)
- `PanicFlee`: Fast escape
- `StealthyAvoider`: Slow, careful avoidance
- `FreezeResponse`: Stop when predator near
- `ErraticEvader`: Unpredictable escape patterns
- `VerticalEscaper`: Flee vertically
- `GroupDefender`: Stay in group for safety
- `SpiralEscape`: Spiral away from threat
- `BorderHugger`: Use walls for protection
- `PerpendicularEscape`: Escape at right angles
- `DistanceKeeper`: Maintain safe distance

#### 3. Schooling/Social (10 algorithms)
- `TightScholer`: Close formation
- `LooseScholer`: Loose formation
- `LeaderFollower`: Follow strongest fish
- `AlignmentMatcher`: Match neighbor velocities
- `SeparationSeeker`: Maintain personal space
- `FrontRunner`: Lead the school
- `PerimeterGuard`: Patrol school edges
- `MirrorMover`: Mirror partner movements
- `BoidsBehavior`: Classic flocking (alignment + cohesion + separation)
- `DynamicScholer`: Adaptive cohesion based on danger

#### 4. Energy Management (8 algorithms)
- `EnergyConserver`: Minimize activity when low energy
- `BurstSwimmer`: Alternate fast/slow for efficiency
- `OpportunisticRester`: Rest when safe
- `EnergyBalancer`: Maintain target energy range
- `SustainableCruiser`: Consistent moderate pace
- `StarvationPreventer`: Aggressive food seeking when critical
- `MetabolicOptimizer`: Adjust speed to metabolic efficiency
- `AdaptivePacer`: Speed based on energy availability

#### 5. Territory/Exploration (8 algorithms)
- `TerritorialDefender`: Defend home area
- `RandomExplorer`: Random wandering
- `WallFollower`: Follow tank edges
- `CornerSeeker`: Prefer corners
- `CenterHugger`: Stay near center
- `RoutePatroller`: Follow fixed route
- `BoundaryExplorer`: Systematic edge exploration
- `NomadicWanderer`: Continuous migration

#### 6. Poker Interaction (5 algorithms)
- `PokerChallenger`: Actively seek poker games
- `PokerDodger`: Avoid poker confrontations
- `PokerGambler`: High-risk poker when energy high
- `SelectivePoker`: Choose favorable matchups
- `PokerOpportunist`: Balance poker and food based on context

### Parameter Tuning

Each algorithm has 2-5 **tunable parameters** with defined bounds:

Example: `GreedyFoodSeeker`
- `speed_multiplier`: 0.7 - 1.3 (how fast to chase food)
- `detection_range`: 0.5 - 1.0 (scanning distance multiplier)

Example: `BoidsBehavior`
- `alignment_weight`: 0.3 - 0.7 (match neighbor velocities)
- `cohesion_weight`: 0.3 - 0.7 (move toward group center)
- `separation_weight`: 0.3 - 0.7 (avoid crowding)

### Mutation System

**Parameter Mutations:**
- 15% chance per parameter
- Gaussian distribution within bounds
- Adaptive mutation bounds to prevent extreme values

**Algorithm Type Mutations:**
- 5% chance to switch to random algorithm
- Enables exploration of algorithm space
- Prevents local optima

## Inheritance Mechanics

### Physical Traits
- Speed, size, vision, metabolism, etc.
- Mendelian inheritance with mutations
- Linked traits (e.g., speed ↔ metabolism)

### Behavior Algorithms
- **Type inheritance:** 50/50 from each parent (or 5% random)
- **Parameter inheritance:**
  - Same algorithm: Parameters blend (averaging or dominance)
  - Different algorithms: Inherit one parent's full algorithm
- **Mutations:** Applied after crossover

### Visual Traits
- Color hue, template, fin size, tail size, body aspect
- Pattern type and intensity
- Full parametric fish appearance system

## Testing

Run `python3 test_evolution_fixes.py` to verify:
1. ✓ Energy economy is balanced
2. ✓ Algorithm crossover from both parents
3. ✓ Parameter blending when same algorithm type
4. ✓ Algorithm type variation in offspring

## Expected Evolutionary Outcomes

With these fixes, the population should evolve to:
1. **Better food finding** (successful foraging algorithms spread)
2. **Predator avoidance** (survivors pass on escape strategies)
3. **Energy efficiency** (low-metabolism fish reproduce more)
4. **Poker strategy** (winning strategies propagate)
5. **Specialized niches** (different algorithms for different conditions)

## Files Modified

- `core/fish/reproduction_component.py`: Energy transfer system
- `core/entities.py`: Baby energy initialization
- `core/algorithms/__init__.py`: Algorithm crossover function
- `core/genetics/`: Use crossover for algorithm inheritance
- `core/behavior_algorithms.py`: Export crossover function

## Performance Tracking

The system tracks algorithm performance:
- Births per algorithm type
- Deaths per algorithm type (by cause)
- Food consumption per algorithm
- Reproduction success rate
- Average lifespan per algorithm

This data enables identifying which algorithms are evolutionarily successful!

## Next Steps (Optional Enhancements)

1. **Algorithm performance UI** - Show which algorithms are winning
2. **Historical tracking** - Track algorithm dominance over time
3. **Hybrid algorithms** - Combine multiple algorithms
4. **Context switching** - Different algorithms for different situations
5. **Learning** - Algorithms improve within lifetime
