# Multi-Level Evolution Strategy for Soccer Tank World

## Executive Summary

The Tank World soccer system is designed as a **multi-level evolutionary platform** where:

1. **Individual level**: Fish evolve kick behaviors and movement strategies
2. **Team level**: Team composition and tactics emerge from individual selection
3. **Population level**: Rules and physics parameters tune to find stable, entertaining play
4. **Process level**: Evolutionary discovery methods themselves are evaluated and improved

This creates a self-improving system where both the simulation and solutions evolve.

## Level 1: Individual Fish Evolution

### Current Mechanisms

Fish already have genetic traits for:
- **Physical traits**: size, speed, lifespan
- **Behavioral traits**: aggression, poker strategy, threat response
- **Metabolic traits**: energy consumption rates

### New Soccer Traits to Evolve

Add to `core/genetics/behavioral.py`:

```python
@dataclass
class SoccerBehavioralTraits:
    """Soccer-specific evolved behaviors."""

    kick_aggression: GeneticTrait[float]  # [0-1] How often to kick
    kick_power_preference: GeneticTrait[float]  # [0-100] Preferred power
    kick_accuracy: GeneticTrait[float]  # [0-1] Direction consistency
    positioning_preference: GeneticTrait[float]  # [0-1] Near ball vs goal
    passing_tendency: GeneticTrait[float]  # [0-1] Pass vs. shoot
    defensive_tendency: GeneticTrait[float]  # [0-1] Block vs. attack
```

### Selection Pressure

**Energy-based fitness** (emergent evolution, NOT fitness functions):

```
Energy gain:
- Eating food: +10 energy
- Scoring goal: +100 energy (major reward)
- Assisting goal: +30 energy
- Blocking opponent shot: +5 energy (harder to track, learn naturally)

Energy loss:
- Movement: -2 per unit velocity²
- Kicking: -1 per power unit (optional, tunable)
- Failed kick: -1 (out of range)
```

Fish with better kick strategies:
- Score more goals → gain more energy
- Reproduce more frequently → pass on traits
- Traits become dominant in population

### Evolutionary Outcomes

**Expected specialization by generation**:

| Generation | Role | Traits | Strategy |
|-----------|------|--------|----------|
| 0-10 | Random | All average | Exploration, low kick power |
| 10-50 | Emerging | Aggressive strikers | High power, centered kicks |
| 50-100 | Specialized | Scorers + Defenders | Roles differentiate |
| 100+ | Tactical | Team coordination | Formation play emerges |

## Level 2: Team-Level Strategy Evolution

### Team Composition as Fitness Signal

Rather than explicit team fitness, teams succeed by:
1. Team A has 10 fish, Team B has 10 fish
2. Both teams play against each other repeatedly
3. Winning team (more goals) has better energy → more reproduction
4. Winners' offspring replace losers' offspring over generations

### Emergent Formations

Observations enable spatial learning:

```python
# Fish can see:
- Ball position
- Teammate positions (all within perception)
- Opponent positions (all within perception)
- Goal positions

# Fish behavior becomes context-sensitive:
- Near ball → aggressive, attempt kick
- Near goal → defensive, block opponents
- Far from ball → move toward action
```

### Cooperative Emergence

**Multi-fish rewards** (create selection for cooperation):

```python
# Current: Individual energy for eating
# Goal: Add team-level rewards

# Option 1: Possession bonus
# All teammates gain +1 energy per frame if team has ball > 2 seconds

# Option 2: Formation bonus
# Teammates gain +5 energy if positioned strategically (not overlapping)

# Option 3: Passing chains
# Last 2 fish to touch ball before goal both gain bonus energy
```

Track metrics to measure cooperation:
- Pass completion rate
- Average distance between teammates
- Possession time per team
- Goal scoring distribution (concentrated vs. spread)

## Level 3: Environment/Physics Parameter Evolution

### Identify Tunable Parameters

Create "knobs" that affect game difficulty and entertainment:

```python
class SoccerGameParams:
    # Physics
    ball_decay: float = 0.94          # Slower decay = longer plays
    ball_max_speed: float = 3.0       # Lower = more control needed
    kick_power_rate: float = 0.027    # Higher = easier kicks

    # Goals
    goal_radius: float = 15.0         # Larger = easier to score
    goal_energy_reward: float = 100.0 # Higher = more breeding from winners

    # Fields (tank size)
    field_width: float = 800           # Larger = more space
    field_height: float = 600

    # Stamina (RCSS-Lite mode)
    stamina_max: float = 8000.0       # More stamina = more mobility
    player_decay: float = 0.4         # Velocity retention

    # Game rules
    team_size: int = 10               # More fish = more diversity
    perception_radius: float = 200.0  # What fish can see
```

### Parameter Tuning Process

**Goal**: Find parameters that produce:
1. **Balanced competition**: Both teams score regularly
2. **Emergent complexity**: Interesting tactical play
3. **Viewer entertainment**: Fast-paced, high-scoring, surprising

### Automated Parameter Search

```python
def evaluate_game_parameters(params: SoccerGameParams) -> dict:
    """Evaluate parameter set across multiple matches."""
    results = {
        "balance": 0.0,      # 0=one team dominates, 1=equal wins
        "complexity": 0.0,   # 0=random, 1=strategic patterns
        "entertainment": 0.0, # 0=boring, 1=exciting
        "goal_rate": 0.0,    # Goals per minute
        "rally_length": 0.0, # Avg touches before goal
    }

    # Run 10 matches with param set
    for match in range(10):
        match_result = run_match(params, frames=10000)

        # Compute metrics
        results["balance"] += compute_balance(match_result)
        results["complexity"] += compute_complexity(match_result)
        # ... etc

    # Average across matches
    for key in results:
        results[key] /= 10

    return results
```

### Metrics to Optimize

**Balance**:
```python
def compute_balance(match_result) -> float:
    """How balanced was the match? (0=dominated, 1=even)"""
    goals_a = match_result['team_a_goals']
    goals_b = match_result['team_b_goals']
    total = goals_a + goals_b
    if total == 0: return 0.5  # No goals = neutral
    ratio = min(goals_a, goals_b) / max(goals_a, goals_b)
    return ratio  # 1.0 = perfectly balanced
```

**Complexity** (measure strategic depth):
```python
def compute_complexity(match_result) -> float:
    """How complex/strategic was the play?"""
    # Proxy: diversity of players used
    unique_scorers = len(set(match_result['scoring_fish']))
    # Proxy: goal spacing (clustered = less complex)
    goal_timestamps = match_result['goal_frames']
    spacing = compute_variance(goal_timestamps)
    # Proxy: ball movement (not just back/forth)
    ball_dist_covered = match_result['ball_total_distance']

    return (unique_scorers / 10) * 0.5 + (spacing / max_spacing) * 0.3 + ...
```

**Entertainment** (subjective, but measurable):
```python
def compute_entertainment(match_result) -> float:
    """Heuristic entertainment score."""
    goal_rate = len(match_result['goals']) / (match_result['duration_secs'] / 60)
    rally_complexity = mean([len(r) for r in match_result['rallies']])
    possession_balance = compute_balance(match_result)  # Reuse

    entertainment = (
        min(goal_rate, 2.0) / 2.0 * 0.4 +  # 2 goals/min is exciting
        min(rally_complexity, 10) / 10 * 0.3 +  # Long rallies more complex
        possession_balance * 0.3  # Close games more entertaining
    )
    return min(entertainment, 1.0)
```

### Parameter Optimization Loop

```python
def find_optimal_parameters(n_iterations=100):
    """Evolutionary search for best parameters."""
    best_params = SoccerGameParams()  # Defaults
    best_score = evaluate_game_parameters(best_params)['entertainment']

    for iteration in range(n_iterations):
        # Propose nearby parameters (mutation)
        candidate = mutate_parameters(best_params)

        # Evaluate
        candidate_score = evaluate_game_parameters(candidate)

        # Accept if better (or randomly with low probability)
        if candidate_score['entertainment'] > best_score:
            best_params = candidate
            best_score = candidate_score['entertainment']
            log(f"Iteration {iteration}: New best entertainment = {best_score:.3f}")

        # Log all evaluations for analysis
        log_evaluation(iteration, candidate, candidate_score)

    return best_params
```

## Level 4: Evolutionary Discovery Process

### Meta-Level: Evolving How We Evolve

Instead of hand-tuning parameters, evolve the **parameter tuning strategy**:

```python
class EvolutionStrategy:
    """Strategy for tuning game parameters."""

    learning_rate: float       # How aggressively to change params
    mutation_std: float        # Std dev of parameter mutations
    population_size: int       # Candidate parameter sets per generation
    evaluation_frames: int     # Frames per match evaluation
    match_count: int           # Matches per parameter evaluation
```

### Competitive Co-Evolution

Run BOTH simultaneously:

1. **Fish evolution**: Population of fish evolving kick strategies
2. **Parameter evolution**: Set of game params being tuned for balance

They interact:
- Better parameters → More interesting games → Better strategy evolution
- Better strategies → Clearer signal of what makes good parameters

### Tracking Evolution Progress

Create `core/evolution/soccer_evolution.py`:

```python
@dataclass
class EvolutionCheckpoint:
    """Snapshot of system state at a generation."""

    generation: int
    timestamp: datetime
    fish_population: dict  # Fish genomes and stats
    top_strategies: list   # Top 10 fish by wins/goals
    parameters: SoccerGameParams
    match_results: dict  # Recent match statistics
    metrics: dict  # Balance, complexity, entertainment

def save_checkpoint(checkpoint: EvolutionCheckpoint):
    """Save evolution state for analysis and resumption."""
    path = f"checkpoints/gen_{checkpoint.generation:06d}.pkl"
    with open(path, 'wb') as f:
        pickle.dump(checkpoint, f)

def analyze_evolution():
    """Generate report on system evolution."""
    # Load all checkpoints
    # Plot: parameter changes over time
    # Plot: population diversity over time
    # Plot: top strategies' traits over time
    # Plot: game metrics (balance, entertainment) over time
    # Identify: when specialization happened
    # Identify: when complex behaviors emerged
```

### Metrics Dashboard

```python
class EvolutionMetricsTracker:
    """Track system-wide evolution metrics."""

    # Individual level
    population_diversity: float      # Genetic diversity
    top_performer_advantage: float   # How much better are top fish
    specialization_index: float      # Role differentiation

    # Team level
    team_balance: float              # Win rate parity
    cooperation_metrics: dict        # Pass%, formation stability
    emergent_roles: dict             # Detected positions/roles

    # Parameter level
    parameter_stability: float       # How much params are changing
    game_balance_score: float        # Balance metric
    entertainment_score: float       # Entertainment metric

    # Process level
    discovery_rate: float            # New strategies per generation
    convergence_speed: float         # How fast strategies stabilize
    evolvability: float              # How much mutations help
```

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2) ✅
- ✅ Ball physics implementation
- ✅ Goal zone detection
- ✅ Team affiliations
- ✅ Kick actions and observations
- ✅ RCSS-Lite physics mode
- ✅ Comprehensive physics tests

### Phase 2: Individual Evolution (Weeks 2-3)
- [ ] Extend `Genome` with soccer behavioral traits
- [ ] Implement kick behavior mutations
- [ ] Add goal/energy reward system
- [ ] Test strategy evolution on small populations

### Phase 3: Team/Population Dynamics (Weeks 3-4)
- [ ] Implement team selection (winning team reproduces)
- [ ] Add multi-fish reward bonuses (cooperation)
- [ ] Track emergent roles via observations
- [ ] Visualization of team formations

### Phase 4: Parameter Tuning (Weeks 4-5)
- [ ] Implement parameter search loop
- [ ] Create evaluation metrics (balance, complexity)
- [ ] Run automated parameter optimization
- [ ] Generate parameter sensitivity analysis

### Phase 5: Meta-Evolution (Weeks 5-6)
- [ ] Evolution of evolution strategy
- [ ] Competitive co-evolution of fish vs. parameters
- [ ] Advanced metrics dashboard
- [ ] Historical analysis and replay system

### Phase 6: Polish & Entertainment (Weeks 6-7)
- [ ] Spectator mode and visualization
- [ ] Replay recording and analysis
- [ ] Statistics and leaderboards
- [ ] Web UI for monitoring evolution

## Expected Outcomes

### Individual Level (Generations 1-100)
- Fish learn to kick accurately
- Kick power distribution evolves
- Specialization: strikers vs. defenders
- Passing strategies emerge

### Team Level (Generations 100-300)
- Formation behaviors stabilize
- Team tactics become consistent
- Win/loss ratios become predictable
- Coaching strategies become apparent

### Parameter Level (Generations 300-500)
- Optimal ball decay identified
- Goal distance tuned for challenge
- Field size balances offense/defense
- Stamina levels ensure competitive play

### Discovery Level (Ongoing)
- New tactics emerge unexpectedly
- Parameters adapt to population
- System finds surprising equilibria
- Entertainment metrics guide tuning

## Key Innovation: Process Evolution

Unlike traditional ML, this system:
1. **Learns WHAT to optimize** (entertainment, complexity)
2. **Learns HOW to optimize** (parameter space, mutation rates)
3. **Runs while being observed** (suitable for TV/entertainment)
4. **Produces interpretable results** (genetic explanations, visual tactics)

This is closer to how biological evolution and sports coaching work: repeated trials, measurement, and adjustment, but all automated and data-driven.

## Success Metrics

| Metric | Target | Timeline |
|--------|--------|----------|
| Goal Rate | 1-2 goals/minute | Week 2 |
| Game Balance | Win ratio 0.45-0.55 | Week 4 |
| Strategy Diversity | 10+ distinct tactics | Week 6 |
| Entertainment Score | > 0.8/1.0 | Week 8 |
| Emergent Behaviors | Novel plays per 100 matches | Week 10 |
| Viewer Engagement | Surprise/excitement metrics | Ongoing |

## References

- **Multi-level selection**: Evolution at individual, group, and system levels
- **Coevolution**: Simultaneous evolution of prey and predators (or strategies and parameters)
- **Open-ended evolution**: Systems that continue discovering novelty indefinitely
- **Behavioral diversity**: Measurement of strategy richness over time
