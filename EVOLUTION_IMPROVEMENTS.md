# Fish Evolution and Behavior Improvements

This document describes the major improvements made to the fish evolution system, poker behaviors, and population statistics.

## Overview

The fish tank simulation now features three major enhancements:

1. **Behavioral Learning System** - Fish learn from experience within their lifetime
2. **Enhanced Population Statistics** - Time series tracking, correlation analysis, extinction tracking, evolutionary rates
3. **Advanced Poker Strategies** - Hand selection, positional awareness, opponent modeling

---

## 1. Behavioral Learning System

### File: `core/behavioral_learning.py`

Fish can now learn from their experiences and improve their behavior within a single lifetime. Learned behaviors are stored in the genome and can be partially inherited by offspring (cultural evolution).

### Learning Types

- **Food Finding** - Learn better food-seeking patterns
- **Predator Avoidance** - Learn better escape routes
- **Poker Strategy** - Learn opponent tendencies and optimal strategies
- **Energy Management** - Learn optimal energy conservation
- **Spatial Navigation** - Learn efficient movement patterns

### How It Works

1. **Learning Events**: When fish eat food, escape predators, or play poker, learning events are triggered
2. **Behavioral Adjustments**: Learned behaviors modify algorithm parameters within the fish's lifetime
3. **Decay**: Learned behaviors gradually fade without reinforcement
4. **Cultural Inheritance**: Offspring inherit 25% of their parents' learned behaviors

### Key Features

- Learning rate: 5% adjustment per learning event
- Decay rate: 0.1% per frame
- Max adjustment: ±30% parameter modification
- Cultural inheritance: 25% of learned behaviors passed to offspring

### Integration Points

- **Fish.eat()**: Triggers FOOD_FINDING learning event
- **Fish.mark_predator_encounter()**: Triggers PREDATOR_AVOIDANCE learning event
- **PokerInteraction.play_poker()**: Triggers POKER_STRATEGY learning event
- **Fish.update()**: Applies learning decay every frame

### Example Usage

```python
# When a fish eats food
food_event = LearningEvent(
    learning_type=LearningType.FOOD_FINDING,
    success=True,
    reward=energy_gained / 10.0,
    context={}
)
fish.learning_system.learn_from_event(food_event)

# Get learning summary
summary = fish.learning_system.get_learning_summary()
# Returns: {
#     'food_finding_efficiency': 0.15,
#     'predator_escape_skill': 0.08,
#     'successful_food_finds': 42,
#     ...
# }
```

---

## 2. Enhanced Population Statistics

### File: `core/enhanced_statistics.py`

The simulation now tracks comprehensive statistics including historical trends, trait correlations, extinctions, and evolutionary rates.

### Features

#### 2.1 Time Series Tracking

Records snapshots of population state every 10 frames:
- Population size
- Average fitness
- Average traits (speed, size, metabolism, energy)
- Unique algorithms present
- Diversity score
- Birth/death rates

```python
# Access time series data
time_series_summary = ecosystem.enhanced_stats.get_time_series_summary(frames=100)
# Returns trends over last 100 frames:
# - Average population
# - Population trend (+/-)
# - Fitness trend
# - Diversity trend
```

#### 2.2 Trait Correlation Analysis

Calculates which traits correlate with fitness using Pearson correlation:

```python
correlations = ecosystem.enhanced_stats.calculate_trait_correlations()
# Returns list of TraitCorrelation objects:
# - trait_name: 'speed', 'size', 'aggression', etc.
# - correlation: -1.0 to +1.0
# - sample_size: number of samples
# - p_value: statistical significance
```

**Example Output:**
- Speed vs Fitness: r=0.35, p=0.001 (positive correlation)
- Metabolism vs Fitness: r=-0.22, p=0.01 (negative correlation)
- Aggression vs Fitness: r=0.18, p=0.05 (weak positive)

#### 2.3 Extinction Tracking

Detects when algorithms go extinct (no fish with that algorithm for 1000 frames):

```python
extinctions = ecosystem.enhanced_stats.extinct_algorithms
# Returns list of ExtinctionEvent objects:
# - algorithm_name
# - extinction_frame
# - total_births
# - avg_lifespan
# - extinction_cause: 'starvation', 'predation', 'outcompeted'
```

#### 2.4 Evolutionary Rates

Measures how fast traits are evolving:

```python
rates = ecosystem.enhanced_stats.calculate_evolutionary_rates()
# Returns list of EvolutionaryRate objects:
# - trait_name
# - rate_of_change: units per generation
# - variance_change: change in population variance
# - directional_selection: -1 to +1 (direction of selection pressure)
```

#### 2.5 Energy Efficiency Metrics

Tracks energy usage and reproduction efficiency:

```python
efficiency = ecosystem.enhanced_stats.energy_efficiency
# Provides:
# - total_energy_consumed
# - total_energy_from_food
# - total_offspring_produced
# - energy_per_offspring
# - food_to_offspring_ratio
# - avg_energy_waste (energy lost at death)
```

### Integration Points

- **EcosystemManager.update()**: Checks for extinctions every frame
- **EcosystemManager.update_population_stats()**: Records time series snapshots every 10 frames
- **EcosystemManager.record_death()**: Records trait-fitness samples and energy waste
- **EcosystemManager.record_food_eaten()**: Tracks energy from food
- **EcosystemManager.record_birth()**: Tracks offspring production

### Accessing Enhanced Stats

```python
# Get comprehensive report
full_report = ecosystem.get_enhanced_stats_summary()
# Returns dictionary with:
# - time_series_summary
# - trait_correlations
# - extinctions
# - evolutionary_rates
# - energy_efficiency
```

---

## 3. Advanced Poker Strategies

### File: `core/poker_strategy.py`

Fish now use sophisticated poker strategies including hand selection, positional play, and opponent modeling.

### Features

#### 3.1 Hand Selection

Fish evaluate starting hand strength (0.0-1.0) and decide whether to play based on:
- Hand strength (pairs, high cards, suited connectors)
- Position (button vs off-button)
- Learned hand selection tightness
- Opponent tendencies

**Hand Strength Examples:**
- AA, KK, QQ, AK: 0.85-0.95 (premium)
- JJ, TT, AQ, AJ: 0.70-0.80 (strong)
- 99-66, suited connectors: 0.60-0.65 (medium)
- Small pairs, suited aces: 0.45-0.50 (weak)
- Random low cards: 0.20-0.35 (trash)

#### 3.2 Positional Awareness

Fish adjust strategy based on button position:
- **On Button** (late position): Play looser (top 15% of hands), +15% aggression
- **Off Button** (early position): Play tighter (top 8% of hands), normal aggression

This mimics real poker strategy where position provides information advantage.

#### 3.3 Opponent Modeling

Fish track and remember opponent playing styles:

```python
# Opponent model tracks:
# - games_played
# - hands_won/lost
# - times_folded/raised/called
# - avg_aggression
# - is_tight/is_aggressive/is_passive
# - bluff_frequency
# - playing style: 'tight-aggressive', 'loose-passive', etc.
```

**Strategy Adjustments:**
- vs Tight opponents: +20% aggression (steal their blinds)
- vs Aggressive opponents: -10% aggression (avoid confrontation)
- vs Tight-Passive: Bluff more frequently (1.8x bluff rate)

#### 3.4 Learning from Outcomes

Fish learn from poker results and adjust their strategy:

**After Winning:**
- Successful bluff → increase bluff frequency
- Won from button → increase positional awareness
- Won with weak hand → loosen hand selection

**After Losing:**
- Failed bluff → decrease bluff frequency
- Lost with weak hand → tighten hand selection

#### 3.5 Bluffing Logic

Fish decide whether to bluff based on:
- Base bluff frequency (20%)
- Position (1.5x more on button)
- Opponent type (1.8x more vs tight-passive)
- Hand strength (bluff more with medium hands)

### Integration Points

- **Fish.__init__()**: Creates PokerStrategyEngine for each fish
- **PokerInteraction.play_poker()**: Uses poker strategy for decisions and learning
- **Learning after poker**: Updates opponent models and strategy parameters

### Example Usage

```python
# Fish evaluates whether to play hand
should_play = fish.poker_strategy.should_play_hand(
    hole_cards=[('A', 'H'), ('K', 'S')],  # AK suited
    position_on_button=True,
    opponent_id=opponent.fish_id
)

# Get adjusted aggression for this situation
aggression = fish.poker_strategy.calculate_adjusted_aggression(
    base_aggression=fish.genome.aggression,
    position_on_button=True,
    opponent_id=opponent.fish_id,
    hand_strength=0.85
)

# After poker game, fish learns
fish.poker_strategy.learn_from_poker_outcome(
    won=True,
    hand_strength=0.85,
    position_on_button=True,
    bluffed=False,
    opponent_id=opponent.fish_id
)
```

---

## Implementation Details

### New Files Created

1. **`core/behavioral_learning.py`** (298 lines)
   - BehavioralLearningSystem class
   - LearningEvent dataclass
   - LearningType enum
   - Learning and decay logic

2. **`core/enhanced_statistics.py`** (487 lines)
   - EnhancedStatisticsTracker class
   - TimeSeriesSnapshot, TraitCorrelation, ExtinctionEvent, EvolutionaryRate dataclasses
   - Correlation analysis, extinction detection, evolutionary rate calculation

3. **`core/poker_strategy.py`** (351 lines)
   - PokerStrategyEngine class
   - OpponentModel dataclass
   - Hand evaluation, position adjustment, bluffing logic
   - Learning and adaptation

### Modified Files

1. **`core/entities.py`**
   - Added learning_system and poker_strategy to Fish.__init__()
   - Added learning decay to Fish.update()
   - Added learning events to Fish.eat() and Fish.mark_predator_encounter()
   - Updated mark_predator_encounter() signature for learning

2. **`core/ecosystem.py`**
   - Added enhanced_stats tracker to EcosystemManager
   - Integrated time series recording
   - Integrated extinction checking
   - Integrated trait-fitness sampling
   - Integrated energy efficiency tracking

3. **`core/genetics.py`**
   - Added cultural inheritance of learned behaviors to from_parents() and from_parents_weighted()

4. **`core/fish_poker.py`**
   - Integrated poker strategy learning
   - Added opponent modeling updates
   - Added behavioral learning events for poker outcomes

### Backward Compatibility

All changes are backward compatible:
- New systems are additive (don't break existing code)
- Learning systems use default values if not explicitly set
- Enhanced statistics run in parallel with existing stats
- Poker strategy provides defaults for fish without explicit training

---

## Performance Considerations

### Memory Usage

- Learning system: ~500 bytes per fish (learned behaviors dict)
- Poker strategy: ~1KB per fish (opponent models for ~10 opponents)
- Enhanced statistics: ~100KB for 1000 frame history

### CPU Usage

- Learning decay: O(1) per fish per frame (minimal)
- Time series recording: O(n) every 10 frames (n = population)
- Correlation analysis: O(n*m) where n=samples, m=traits (called on demand)
- Extinction checking: O(a) where a=algorithms (48) per frame

### Optimizations

- Time series snapshots only recorded every 10 frames (not every frame)
- Trait-fitness samples limited to 500 most recent per trait
- Opponent models only tracked for fish that actually play poker
- Learning decay is simple arithmetic (no complex math)

---

## Testing

To verify the improvements are working:

1. **Learning System Test:**
   ```python
   # Create fish, have it eat food multiple times
   fish = Fish(...)
   for _ in range(10):
       fish.eat(food)

   # Check learned behavior increased
   assert fish.genome.learned_behaviors['food_finding_efficiency'] > 0
   assert fish.genome.learned_behaviors['successful_food_finds'] == 10
   ```

2. **Enhanced Statistics Test:**
   ```python
   # Run simulation for 1000 frames
   ecosystem.update(1000)

   # Check time series has data
   assert len(ecosystem.enhanced_stats.time_series) > 0

   # Check correlations are calculated
   correlations = ecosystem.enhanced_stats.calculate_trait_correlations()
   assert len(correlations) > 0
   ```

3. **Poker Strategy Test:**
   ```python
   # Create two fish, play poker multiple times
   for _ in range(10):
       poker = PokerInteraction(fish1, fish2)
       poker.play_poker()

   # Check opponent models are updated
   assert fish1.poker_strategy.opponent_models[fish2.fish_id].games_played > 0

   # Check learning occurred
   summary = fish1.poker_strategy.get_strategy_summary()
   assert summary['opponents_modeled'] > 0
   ```

---

## Future Enhancements

Potential future improvements:

1. **Behavioral Learning**
   - Add reinforcement learning for algorithm parameters
   - Implement lifetime behavioral plasticity (fish can switch algorithms)
   - Add social learning (fish learn from observing others)

2. **Enhanced Statistics**
   - Add phylogenetic tree tracking (family lineages)
   - Implement Hardy-Weinberg equilibrium analysis
   - Add selective pressure visualization

3. **Poker Strategies**
   - Add multi-way poker (3+ players)
   - Implement pot odds calculation
   - Add stack depth awareness
   - Implement GTO (Game Theory Optimal) solver

---

## Summary

These improvements significantly enhance the evolutionary dynamics of the fish tank simulation:

- **Fish now learn** from experience, creating within-lifetime adaptation
- **Cultural evolution** allows learned behaviors to pass to offspring
- **Comprehensive statistics** reveal evolutionary pressures and trends
- **Sophisticated poker play** creates complex social dynamics and sexual selection

The system now models:
- **Genetic evolution** (heritable traits)
- **Behavioral evolution** (learned strategies)
- **Cultural evolution** (inherited learning)
- **Social dynamics** (opponent modeling)
- **Evolutionary analytics** (correlations, extinctions, rates)

This creates a rich, multi-layered evolutionary simulation with emergent complexity and realistic adaptive behaviors.
