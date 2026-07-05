# Tank World Algorithm Catalog

> This catalog is dynamically generated from the codebase registry. It documents all available fish behavior algorithms, their configuration bounds, and evolutionary characteristics.

---

## Table of Contents
1. [The Composable Behavior Framework](#the-composable-behavior-framework)
2. [Specialized/Monolithic Behavior Algorithms](#specializedmonolithic-behavior-algorithms)
   - [Aggressive](#aggressive)
   - [Ambush](#ambush)
   - [Bottom](#bottom)
   - [Circular](#circular)
   - [Cooperative](#cooperative)
   - [Energy Aware](#energy-aware)
   - [Energy Management](#energy-management)
   - [Greedy](#greedy)
   - [Memory](#memory)
   - [Opportunistic](#opportunistic)
   - [Patrol](#patrol)
   - [Poker](#poker)
   - [Predator Avoidance](#predator-avoidance)
   - [Quality](#quality)
   - [Schooling](#schooling)
   - [Spiral](#spiral)
   - [Surface](#surface)
   - [Territory](#territory)
   - [Zigzag](#zigzag)

---

## The Composable Behavior Framework

The Composable Behavior Framework is the primary mechanism for fish behavior evolution. Rather than using fixed algorithms, the genome configures combinations of sub-behaviors along four orthogonal axes.

### Threat Response
Determines how fish react when predators are nearby.
| Enum Option | Value | Description |
|---|---|---|
| `PANIC_FLEE` | `0` | Flee at max speed directly away from predator |
| `STEALTH_AVOID` | `1` | Move slowly and carefully away from predator |
| `FREEZE` | `2` | Stop moving when predator is close to avoid detection |
| `ERRATIC_EVADE` | `3` | Unpredictable zigzag escape movement |

### Food Approach
Determines how fish approach and capture food.
| Enum Option | Value | Description |
|---|---|---|
| `DIRECT_PURSUIT` | `0` | Beeline directly to nearest food |
| `PREDICTIVE_INTERCEPT` | `1` | Predict where moving food/prey will be and intercept |
| `CIRCLING_STRIKE` | `2` | Circle around food before striking |
| `AMBUSH_WAIT` | `3` | Wait for food to come close, conserving energy |
| `ZIGZAG_SEARCH` | `4` | Explore the tank in a zigzag pattern to scan for food |
| `PATROL_ROUTE` | `5` | Follow local patrol pattern, diverting to food only when spotted |

### Social Mode
Determines how fish interact and school with other fish.
| Enum Option | Value | Description |
|---|---|---|
| `SOLO` | `0` | Ignore other fish, acting completely independently |
| `LOOSE_SCHOOL` | `1` | Maintain loose proximity to other fish for safety |
| `TIGHT_SCHOOL` | `2` | Stay very close to neighboring fish, tight schooling |
| `FOLLOW_LEADER` | `3` | Identify and follow the nearest fish ahead of it |

### Poker Engagement
Determines how fish engage with poker minigames.
| Enum Option | Value | Description |
|---|---|---|
| `AVOID` | `0` | Actively steer away from other fish to avoid poker games |
| `PASSIVE` | `1` | Neither seek nor avoid poker games, neutral posture |
| `OPPORTUNISTIC` | `2` | Engage in poker if nearby and energy levels are high |
| `AGGRESSIVE` | `3` | Actively seek out neighboring fish to trigger poker games |

### Composable Tuning Parameters
These continuous parameters tune the execution of the selected sub-behaviors.
| Parameter Name | Bounds |
|---|---|
| `alignment_strength` | `[0.2, 0.5904]` |
| `ambush_patience` | `[0.5, 1]` |
| `ambush_strike_distance` | `[20, 60]` |
| `base_speed_multiplier` | `[0.5, 0.9427]` |
| `burst_duration` | `[30, 86.4517]` |
| `burst_speed` | `[1.1, 1.7]` |
| `circle_radius` | `[32.8147, 80]` |
| `circle_speed` | `[0.05, 0.15]` |
| `cohesion_strength` | `[0.3, 0.8]` |
| `energy_urgency_threshold` | `[0.3, 0.6]` |
| `erratic_amplitude` | `[0.3, 0.8]` |
| `flee_speed` | `[0.8, 1.5]` |
| `flee_threshold` | `[80, 180]` |
| `follow_distance` | `[20, 58.8267]` |
| `food_priority` | `[0.5, 0.95]` |
| `freeze_distance` | `[40, 100]` |
| `intercept_skill` | `[0.3, 0.9]` |
| `min_energy_for_poker` | `[0.5653, 0.8]` |
| `patrol_radius` | `[60, 150]` |
| `poker_avoid_radius` | `[60, 150]` |
| `poker_priority` | `[0.05, 0.3]` |
| `poker_seek_radius` | `[80, 175.182]` |
| `pursuit_speed` | `[0.9, 1.6]` |
| `rest_duration` | `[40, 100]` |
| `separation_distance` | `[15, 40]` |
| `social_distance` | `[30, 80]` |
| `social_priority` | `[0.1, 0.4734]` |
| `stealth_speed` | `[0.2121, 0.5]` |
| `threat_priority` | `[0.6, 1]` |
| `zigzag_amplitude` | `[0.4, 1]` |
| `zigzag_frequency` | `[0.02, 0.08]` |

---

## Specialized/Monolithic Behavior Algorithms

Specialized behavior algorithms are dedicated, self-contained implementations. While Composable Behavior is usually the active choice, these algorithms provide baseline performance references and specialized test configurations.

### Aggressive

#### AggressiveHunter ⚠️ **[DEPRECATED]**
- **ID**: `aggressive_hunter`
- **Source File**: [core/algorithms/food_seeking/aggressive.py](../core/algorithms/food_seeking/aggressive.py)
- **Description**: Aggressively pursue food with high-speed interception.
- **Evolutionary Niche**: Highly competitive settings with fast moving prey or high fish counts, where getting to the food first at all costs is required.
- **Known Weakness**: Extreme energy drain due to constant high-speed sprints; dies of starvation quickly if food is missed.
- **Parameters**: None


### Ambush

#### AmbushFeeder ⚠️ **[DEPRECATED]**
- **ID**: `ambush_feeder`
- **Source File**: [core/algorithms/food_seeking/ambush.py](../core/algorithms/food_seeking/ambush.py)
- **Description**: Wait in one spot for food to come close.
- **Evolutionary Niche**: High food spawn rates where sitting still and letting food drift close conserves maximum energy.
- **Known Weakness**: Extremely vulnerable to starvation if food spawn rate is low or if food is stationary.
- **Parameters**:
  - `patience`: range `[0.5, 1]`
  - `strike_distance`: range `[30, 80]`
  - `strike_speed`: range `[1, 1.5]`


### Bottom

#### BottomFeeder ⚠️ **[DEPRECATED]**
- **ID**: `bottom_feeder`
- **Source File**: [core/algorithms/food_seeking/bottom.py](../core/algorithms/food_seeking/bottom.py)
- **Description**: Stay near bottom to catch sinking food.
- **Evolutionary Niche**: Deep/sinking food environments where food drops to the bottom.
- **Known Weakness**: High starvation when food stays near the surface, plus low exploration range.
- **Parameters**:
  - `preferred_depth`: range `[0.7, 0.9]`
  - `search_speed`: range `[0.4, 0.8]`


### Circular

#### CircularHunter ⚠️ **[DEPRECATED]**
- **ID**: `circular_hunter`
- **Source File**: [core/algorithms/food_seeking/circular.py](../core/algorithms/food_seeking/circular.py)
- **Description**: Circle around food before striking - IMPROVED for better survival.
- **Evolutionary Niche**: Circling moving food/prey before striking to optimize intercept angle.
- **Known Weakness**: Unnecessary rotation costs when food is static, delaying feeding.
- **Parameters**:
  - `circle_radius`: range `[40, 100]`
  - `circle_speed`: range `[0.05, 0.15]`
  - `strike_threshold`: range `[0.3, 0.6]`


### Cooperative

#### CooperativeForager
- **ID**: `cooperative_forager`
- **Source File**: [core/algorithms/food_seeking/cooperative.py](../core/algorithms/food_seeking/cooperative.py)
- **Description**: Follow other fish to food sources - HEAVILY IMPROVED.
- **Evolutionary Niche**: Schooling/group-foraging environments where following successful foragers increases search efficiency.
- **Known Weakness**: High congestion and competition at food sites; susceptible to herd errors if leaders go the wrong way.
- **Parameters**:
  - `follow_strength`: range `[0.5, 0.9]`
  - `independence`: range `[0.2, 0.5]`


### Energy Aware

#### EnergyAwareFoodSeeker ⚠️ **[DEPRECATED]**
- **ID**: `energy_aware_food_seeker`
- **Source File**: [core/algorithms/food_seeking/energy_aware.py](../core/algorithms/food_seeking/energy_aware.py)
- **Description**: Seek food more aggressively when energy is low.
- **Evolutionary Niche**: Medium-to-sparse food environments where conserving energy when full and rushing for food when hungry is necessary.
- **Known Weakness**: Suboptimal speed transition thresholds can result in starvation if it waits too long to start moving quickly.
- **Parameters**:
  - `calm_speed`: range `[0.3, 0.6]`
  - `search_speed`: range `[0.4, 0.8]`
  - `urgency_threshold`: range `[0.3, 0.7]`
  - `urgent_speed`: range `[0.8, 1.2]`


### Energy Management

#### EnergyConserver
- **ID**: `energy_conserver`
- **Source File**: [core/algorithms/energy_management.py](../core/algorithms/energy_management.py)
- **Description**: Minimize movement to conserve energy.
- **Evolutionary Niche**: Extreme food scarcity, minimizing unnecessary movement to survive long periods without food.
- **Known Weakness**: Easily outcompeted for food when it does spawn due to passive speed.
- **Parameters**:
  - `activity_threshold`: range `[0.4, 0.7]`
  - `rest_speed`: range `[0.1, 0.3]`

#### BurstSwimmer
- **ID**: `burst_swimmer`
- **Source File**: [core/algorithms/energy_management.py](../core/algorithms/energy_management.py)
- **Description**: Alternate between bursts of activity and rest.
- **Evolutionary Niche**: Alternating rapid exploration with stationary rest periods to optimize metabolic rates.
- **Known Weakness**: Stationary resting periods make the fish highly vulnerable to passing predators.
- **Parameters**:
  - `burst_duration`: range `[30, 90]`
  - `burst_speed`: range `[1.2, 1.6]`
  - `rest_duration`: range `[60, 120]`

#### OpportunisticRester
- **ID**: `opportunistic_rester`
- **Source File**: [core/algorithms/energy_management.py](../core/algorithms/energy_management.py)
- **Description**: Rest when no food or threats nearby.
- **Evolutionary Niche**: Resting only when safe and food is absent, maximizing activity when opportunities exist.
- **Known Weakness**: Can get stuck resting if threat and food detection zones are configured too small.
- **Parameters**:
  - `active_speed`: range `[0.5, 0.9]`
  - `safe_radius`: range `[100, 200]`

#### EnergyBalancer
- **ID**: `energy_balancer`
- **Source File**: [core/algorithms/energy_management.py](../core/algorithms/energy_management.py)
- **Description**: Balance energy expenditure with reserves.
- **Evolutionary Niche**: Balancing current speed/activity directly with remaining internal energy reserves.
- **Known Weakness**: May run too slowly to escape threats when energy is low.
- **Parameters**:
  - `max_energy_ratio`: range `[0.7, 0.9]`
  - `min_energy_ratio`: range `[0.3, 0.5]`

#### SustainableCruiser
- **ID**: `sustainable_cruiser`
- **Source File**: [core/algorithms/energy_management.py](../core/algorithms/energy_management.py)
- **Description**: Maintain steady, sustainable pace.
- **Evolutionary Niche**: Constant, steady cruising speed that avoids the high metabolic cost of acceleration and sprinting.
- **Known Weakness**: Lack of burst speed makes it vulnerable to predators and fast competitors.
- **Parameters**:
  - `consistency`: range `[0.7, 1]`
  - `cruise_speed`: range `[0.4, 0.7]`

#### StarvationPreventer
- **ID**: `starvation_preventer`
- **Source File**: [core/algorithms/energy_management.py](../core/algorithms/energy_management.py)
- **Description**: Prioritize food when energy gets low.
- **Evolutionary Niche**: Rapidly switching to hyper-aggressive food seeking when energy drops below critical thresholds.
- **Known Weakness**: Extreme energy burn in the panic phase can accelerate death if food is not found immediately.
- **Parameters**:
  - `critical_threshold`: range `[0.2, 0.4]`
  - `urgency_multiplier`: range `[1.3, 1.8]`

#### MetabolicOptimizer
- **ID**: `metabolic_optimizer`
- **Source File**: [core/algorithms/energy_management.py](../core/algorithms/energy_management.py)
- **Description**: Adjust activity based on metabolic efficiency.
- **Evolutionary Niche**: Dynamically tuning speed to maximize distance traveled per unit of energy consumed.
- **Known Weakness**: Highly dependent on accurate environmental feedback; fails if configuration is noisy.
- **Parameters**:
  - `efficiency_threshold`: range `[0.5, 0.8]`
  - `high_efficiency_speed`: range `[0.7, 1.1]`
  - `low_efficiency_speed`: range `[0.2, 0.4]`

#### AdaptivePacer
- **ID**: `adaptive_pacer`
- **Source File**: [core/algorithms/energy_management.py](../core/algorithms/energy_management.py)
- **Description**: Adapt speed based on current energy and environment.
- **Evolutionary Niche**: Adapting speed dynamically to both internal energy reserves and local predator/food density.
- **Known Weakness**: High decision complexity can lead to sub-optimal behavior blending under rapid state changes.
- **Parameters**:
  - `base_speed`: range `[0.5, 0.8]`
  - `energy_influence`: range `[0.3, 0.7]`


### Greedy

#### GreedyFoodSeeker ⚠️ **[DEPRECATED]**
- **ID**: `greedy_food_seeker`
- **Source File**: [core/algorithms/food_seeking/greedy.py](../core/algorithms/food_seeking/greedy.py)
- **Description**: Always move directly toward nearest food.
- **Evolutionary Niche**: High food density environments where immediate exploitation of close resources is optimal.
- **Known Weakness**: In sparse environments, gets stuck walking in straight lines or gets outcompeted by wider search patterns.
- **Parameters**:
  - `detection_range`: range `[0.5, 1]`
  - `speed_multiplier`: range `[0.7, 1.3]`


### Memory

#### FoodMemorySeeker ⚠️ **[DEPRECATED]**
- **ID**: `food_memory_seeker`
- **Source File**: [core/algorithms/food_seeking/memory.py](../core/algorithms/food_seeking/memory.py)
- **Description**: Remember where food was found before.
- **Evolutionary Niche**: Stationary or clustering food spawns where remembering previous food locations pays off.
- **Known Weakness**: Memory can become stale in dynamically shifting environments, leading to empty searches.
- **Parameters**:
  - `exploration_rate`: range `[0.2, 0.5]`
  - `memory_strength`: range `[0.5, 1]`


### Opportunistic

#### OpportunisticFeeder
- **ID**: `opportunistic_feeder`
- **Source File**: [core/algorithms/food_seeking/opportunistic.py](../core/algorithms/food_seeking/opportunistic.py)
- **Description**: Only pursue food if it's close enough - IMPROVED to avoid starvation.
- **Evolutionary Niche**: Environments with varying food density, allowing the fish to balance resting/patrolling with sudden, short-range food pursuit.
- **Known Weakness**: Relies on food coming relatively close; fails to adapt if food is very far.
- **Parameters**:
  - `max_pursuit_distance`: range `[50, 200]`
  - `speed`: range `[0.6, 1]`


### Patrol

#### PatrolFeeder ⚠️ **[DEPRECATED]**
- **ID**: `patrol_feeder`
- **Source File**: [core/algorithms/food_seeking/patrol.py](../core/algorithms/food_seeking/patrol.py)
- **Description**: Patrol in a pattern looking for food - IMPROVED with better detection.
- **Evolutionary Niche**: Predictable food spawning grounds, moving in a local area to capture food as soon as it appears.
- **Known Weakness**: Misses food that spawns outside its patrol radius.
- **Parameters**:
  - `food_priority`: range `[0.6, 1]`
  - `patrol_radius`: range `[50, 150]`
  - `patrol_speed`: range `[0.5, 1]`


### Poker

#### PokerChallenger
- **ID**: `poker_challenger`
- **Source File**: [core/algorithms/poker.py](../core/algorithms/poker.py)
- **Description**: Actively seeks out other fish for poker games.
- **Evolutionary Niche**: High-energy fish seeking to challenge neighbors to poker games to exploit their energy.
- **Known Weakness**: Suffers energy loss if opponent plays better or has a better cards hand.
- **Parameters**:
  - `challenge_radius`: range `[100, 250]`
  - `challenge_speed`: range `[0.8, 1.3]`
  - `min_energy_to_challenge`: range `[15, 30]`

#### PokerDodger
- **ID**: `poker_dodger`
- **Source File**: [core/algorithms/poker.py](../core/algorithms/poker.py)
- **Description**: Avoids other fish to prevent poker games.
- **Evolutionary Niche**: Avoiding poker invitations to preserve energy for foraging.
- **Known Weakness**: Misses out on profitable poker games when holding strong hands or energy advantage.
- **Parameters**:
  - `avoidance_radius`: range `[80, 150]`
  - `avoidance_speed`: range `[0.7, 1.1]`
  - `food_priority`: range `[0.6, 1]`

#### PokerGambler
- **ID**: `poker_gambler`
- **Source File**: [core/algorithms/poker.py](../core/algorithms/poker.py)
- **Description**: Seeks poker aggressively when high energy.
- **Evolutionary Niche**: High risk tolerance, joining games frequently to quickly accumulate large energy surpluses.
- **Known Weakness**: High variance; prone to sudden bankruptcy/starvation from consecutive losses.
- **Parameters**:
  - `challenge_speed`: range `[1, 1.5]`
  - `high_energy_threshold`: range `[0.6, 0.9]`
  - `risk_tolerance`: range `[0.3, 0.8]`

#### SelectivePoker
- **ID**: `selective_poker`
- **Source File**: [core/algorithms/poker.py](../core/algorithms/poker.py)
- **Description**: Only engages in poker when conditions are favorable.
- **Evolutionary Niche**: Playing poker only when possessing a distinct energy advantage or within optimal energy bounds.
- **Known Weakness**: Misses passive energy accumulation when playing too conservatively.
- **Parameters**:
  - `challenge_speed`: range `[0.6, 1]`
  - `max_energy_ratio`: range `[0.7, 0.95]`
  - `min_energy_ratio`: range `[0.4, 0.7]`
  - `selectivity`: range `[0.5, 0.9]`

#### PokerOpportunist
- **ID**: `poker_opportunist`
- **Source File**: [core/algorithms/poker.py](../core/algorithms/poker.py)
- **Description**: Balances food seeking with poker opportunities.
- **Evolutionary Niche**: Balancing poker challenges with food seeking based on direct proximity.
- **Known Weakness**: Can get distracted by nearby games when in critical need of food.
- **Parameters**:
  - `food_weight`: range `[0.3, 0.7]`
  - `opportunity_radius`: range `[80, 150]`
  - `poker_weight`: range `[0.3, 0.7]`

#### PokerStrategist
- **ID**: `poker_strategist`
- **Source File**: [core/algorithms/poker.py](../core/algorithms/poker.py)
- **Description**: Uses opponent modeling and strategic positioning for poker.
- **Evolutionary Niche**: Incorporating opponent tracking and position awareness to optimize game selection.
- **Known Weakness**: Overhead in parameters makes it complex to tune and adapt.
- **Parameters**:
  - `aggression_variance`: range `[0.1, 0.4]`
  - `challenge_speed`: range `[0.7, 1.2]`
  - `min_energy_ratio`: range `[0.3, 0.6]`
  - `opponent_tracking`: range `[0.3, 0.8]`
  - `position_awareness`: range `[0.5, 1]`

#### PokerBluffer
- **ID**: `poker_bluffer`
- **Source File**: [core/algorithms/poker.py](../core/algorithms/poker.py)
- **Description**: Varies behavior unpredictably to confuse opponents.
- **Evolutionary Niche**: Bluffing to win pots from more conservative players.
- **Known Weakness**: High-risk strategies can be called and heavily punished by aggressive or high-energy opponents.
- **Parameters**:
  - `aggression_swing`: range `[0.4, 1]`
  - `bluff_frequency`: range `[0.2, 0.6]`
  - `min_energy_to_bluff`: range `[20, 40]`
  - `unpredictability`: range `[0.3, 0.7]`

#### PokerConservative
- **ID**: `poker_conservative`
- **Source File**: [core/algorithms/poker.py](../core/algorithms/poker.py)
- **Description**: Risk-averse poker player that only engages in highly favorable conditions.
- **Evolutionary Niche**: High energy threshold requirements, entering poker only when risk is minimal.
- **Known Weakness**: Extremely low game participation rate.
- **Parameters**:
  - `challenge_speed`: range `[0.5, 0.9]`
  - `energy_advantage_required`: range `[10, 30]`
  - `max_risk_tolerance`: range `[0.1, 0.3]`
  - `min_energy_ratio`: range `[0.6, 0.85]`
  - `safety_distance`: range `[100, 180]`


### Predator Avoidance

#### PanicFlee
- **ID**: `panic_flee`
- **Source File**: [core/algorithms/predator_avoidance.py](../core/algorithms/predator_avoidance.py)
- **Description**: Flee directly away from predators at maximum speed.
- **Evolutionary Niche**: High predator density where immediate high-speed flight away from danger is the only option.
- **Known Weakness**: Extremely high energy cost; can run into other predators or walls if not steering carefully.
- **Parameters**:
  - `flee_speed`: range `[1.2, 1.8]`
  - `panic_distance`: range `[100, 200]`

#### StealthyAvoider
- **ID**: `stealthy_avoider`
- **Source File**: [core/algorithms/predator_avoidance.py](../core/algorithms/predator_avoidance.py)
- **Description**: Move slowly and carefully away from predators.
- **Evolutionary Niche**: Low speed, stealthy movement to avoid triggering predator aggression/awareness.
- **Known Weakness**: Slow speed may fail to escape if the predator has already initiated a pursuit.
- **Parameters**:
  - `awareness_range`: range `[150, 250]`
  - `stealth_speed`: range `[0.3, 0.6]`

#### FreezeResponse
- **ID**: `freeze_response`
- **Source File**: [core/algorithms/predator_avoidance.py](../core/algorithms/predator_avoidance.py)
- **Description**: Freeze when predator is near, but prioritize survival over safety when starving.
- **Evolutionary Niche**: Camouflage/stillness where moving would trigger predator visual detection.
- **Known Weakness**: Becomes a sitting duck if the predator approaches directly regardless of movement.
- **Parameters**:
  - `freeze_distance`: range `[80, 150]`
  - `resume_distance`: range `[200, 300]`

#### ErraticEvader
- **ID**: `erratic_evader`
- **Source File**: [core/algorithms/predator_avoidance.py](../core/algorithms/predator_avoidance.py)
- **Description**: Make unpredictable movements when threatened.
- **Evolutionary Niche**: Evading active predator chases by making unpredictable, sharp turns.
- **Known Weakness**: Hard to navigate toward safety or food while moving erratically; high turning energy cost.
- **Parameters**:
  - `evasion_speed`: range `[0.8, 1.3]`
  - `randomness`: range `[0.5, 1]`
  - `threat_range`: range `[100, 180]`

#### VerticalEscaper
- **ID**: `vertical_escaper`
- **Source File**: [core/algorithms/predator_avoidance.py](../core/algorithms/predator_avoidance.py)
- **Description**: Escape vertically when threatened.
- **Evolutionary Niche**: Predators that operate primarily on a horizontal plane or have poor vertical movement.
- **Known Weakness**: Ineffective if predators can move vertically just as fast, or if the tank depth is shallow.
- **Parameters**:
  - `escape_speed`: range `[1, 1.5]`

#### GroupDefender
- **ID**: `group_defender`
- **Source File**: [core/algorithms/predator_avoidance.py](../core/algorithms/predator_avoidance.py)
- **Description**: Stay close to group for safety.
- **Evolutionary Niche**: Schooling groups where safety in numbers reduces individual predation risk.
- **Known Weakness**: If the group is targeted or panics, individual choices are restricted; can lead to group traps.
- **Parameters**:
  - `group_strength`: range `[0.6, 1]`
  - `min_group_distance`: range `[30, 80]`

#### SpiralEscape
- **ID**: `spiral_escape`
- **Source File**: [core/algorithms/predator_avoidance.py](../core/algorithms/predator_avoidance.py)
- **Description**: Spiral away from predators.
- **Evolutionary Niche**: Escaping line-of-sight predator attacks by looping around the attacker.
- **Known Weakness**: Complex path length takes longer to reach absolute safety compared to a straight line flee.
- **Parameters**:
  - `spiral_radius`: range `[20, 60]`
  - `spiral_rate`: range `[0.1, 0.3]`

#### BorderHugger
- **ID**: `border_hugger`
- **Source File**: [core/algorithms/predator_avoidance.py](../core/algorithms/predator_avoidance.py)
- **Description**: Move to tank edges when threatened.
- **Evolutionary Niche**: Staying near walls where predators rarely patrol or where navigation is restricted.
- **Known Weakness**: Can get cornered easily with no escape routes if a predator approaches along the wall.
- **Parameters**:
  - `hug_speed`: range `[0.7, 1.1]`

#### PerpendicularEscape
- **ID**: `perpendicular_escape`
- **Source File**: [core/algorithms/predator_avoidance.py](../core/algorithms/predator_avoidance.py)
- **Description**: Escape perpendicular to predator's approach.
- **Evolutionary Niche**: Breaking the predator's direct line-of-sight/pursuit angle by fleeing at 90 degrees.
- **Known Weakness**: Does not maximize absolute distance from the predator as quickly as direct fleeing.
- **Parameters**:
  - `escape_speed`: range `[1, 1.4]`

#### DistanceKeeper
- **ID**: `distance_keeper`
- **Source File**: [core/algorithms/predator_avoidance.py](../core/algorithms/predator_avoidance.py)
- **Description**: Maintain safe distance from predators.
- **Evolutionary Niche**: Maintaining a strict safety buffer zone, keeping predators at a distance before they start chasing.
- **Known Weakness**: Can spend too much time adjusting distance, leaving less time for foraging.
- **Parameters**:
  - `approach_speed`: range `[0.3, 0.6]`
  - `flee_speed`: range `[0.8, 1.2]`
  - `safe_distance`: range `[120, 200]`


### Quality

#### FoodQualityOptimizer
- **ID**: `food_quality_optimizer`
- **Source File**: [core/algorithms/food_seeking/quality.py](../core/algorithms/food_seeking/quality.py)
- **Description**: Prefer high-value food types.
- **Evolutionary Niche**: High quality/density clusters of food where selecting the best nutrition per unit distance traveled dominates.
- **Known Weakness**: High movement/evaluation overhead when checking distant food options.
- **Parameters**:
  - `distance_weight`: range `[0.3, 0.7]`
  - `quality_weight`: range `[0.5, 1]`


### Schooling

#### TightSchooler
- **ID**: `tight_schooler`
- **Source File**: [core/algorithms/schooling.py](../core/algorithms/schooling.py)
- **Description**: Stay very close to school members.
- **Evolutionary Niche**: Highly coordinated group schooling to minimize predation and maximize collective sensing.
- **Known Weakness**: Extremely high local competition for food; susceptible to collective traps.
- **Parameters**:
  - `cohesion_strength`: range `[0.7, 1.2]`
  - `preferred_distance`: range `[20, 50]`

#### LooseSchooler
- **ID**: `loose_schooler`
- **Source File**: [core/algorithms/schooling.py](../core/algorithms/schooling.py)
- **Description**: Maintain loose association with school.
- **Evolutionary Niche**: Balancing the safety/social benefits of schooling with individual space to forage.
- **Known Weakness**: Weak cohesion makes the group vulnerable to split attacks by multiple predators.
- **Parameters**:
  - `cohesion_strength`: range `[0.3, 0.6]`
  - `max_distance`: range `[100, 200]`

#### LeaderFollower
- **ID**: `leader_follower`
- **Source File**: [core/algorithms/schooling.py](../core/algorithms/schooling.py)
- **Description**: Follow the fastest/strongest fish.
- **Evolutionary Niche**: Hierarchical group movement where a few dominant individuals navigate.
- **Known Weakness**: Entire school fails if the leader is eaten, makes a bad decision, or gets stuck.
- **Parameters**:
  - `follow_strength`: range `[0.6, 1]`
  - `max_follow_distance`: range `[80, 150]`

#### AlignmentMatcher
- **ID**: `alignment_matcher`
- **Source File**: [core/algorithms/schooling.py](../core/algorithms/schooling.py)
- **Description**: Match velocity with nearby fish.
- **Evolutionary Niche**: Creating synchronized school movement velocities (swarming/flocking).
- **Known Weakness**: Lacks positional cohesion; fish can drift apart if speed matches but positions do not.
- **Parameters**:
  - `alignment_radius`: range `[60, 120]`
  - `alignment_strength`: range `[0.5, 1]`

#### SeparationSeeker
- **ID**: `separation_seeker`
- **Source File**: [core/algorithms/schooling.py](../core/algorithms/schooling.py)
- **Description**: Avoid crowding neighbors.
- **Evolutionary Niche**: Avoiding crowding and collisions within a school, reducing transmission of negative behaviors or group starvation.
- **Known Weakness**: Can disintegrate the school entirely if separation force is too high.
- **Parameters**:
  - `min_distance`: range `[30, 70]`
  - `separation_strength`: range `[0.5, 1]`

#### FrontRunner
- **ID**: `front_runner`
- **Source File**: [core/algorithms/schooling.py](../core/algorithms/schooling.py)
- **Description**: Lead the school from the front.
- **Evolutionary Niche**: Leading the group to navigate toward new resources or away from threats.
- **Known Weakness**: High exposure to frontal predators/hazards.
- **Parameters**:
  - `independence`: range `[0.5, 0.9]`
  - `leadership_strength`: range `[0.7, 1.2]`

#### PerimeterGuard
- **ID**: `perimeter_guard`
- **Source File**: [core/algorithms/schooling.py](../core/algorithms/schooling.py)
- **Description**: Stay on the outside of the school.
- **Evolutionary Niche**: Circling the boundary of a school to watch for and deter predators.
- **Known Weakness**: High energy cost of constant circling; less opportunity to feed.
- **Parameters**:
  - `orbit_radius`: range `[70, 130]`
  - `orbit_speed`: range `[0.5, 0.9]`

#### MirrorMover
- **ID**: `mirror_mover`
- **Source File**: [core/algorithms/schooling.py](../core/algorithms/schooling.py)
- **Description**: Mirror the movements of nearby fish.
- **Evolutionary Niche**: Mimicking adjacent fish movements to maintain precise local schooling structures.
- **Known Weakness**: Delays response to environmental cues by waiting for neighbors to move first.
- **Parameters**:
  - `mirror_distance`: range `[50, 100]`
  - `mirror_strength`: range `[0.6, 1]`

#### BoidsBehavior
- **ID**: `boids_behavior`
- **Source File**: [core/algorithms/schooling.py](../core/algorithms/schooling.py)
- **Description**: Classic boids algorithm (separation, alignment, cohesion).
- **Evolutionary Niche**: Classic flocking (combining cohesion, separation, and alignment) for realistic group simulation.
- **Known Weakness**: Parameter tuning is delicate; poor values lead to either chaotic scattering or rigid stagnation.
- **Parameters**:
  - `alignment_weight`: range `[0.3, 0.7]`
  - `cohesion_weight`: range `[0.3, 0.7]`
  - `separation_weight`: range `[0.3, 0.7]`

#### DynamicSchooler
- **ID**: `dynamic_schooler`
- **Source File**: [core/algorithms/schooling.py](../core/algorithms/schooling.py)
- **Description**: Switch between tight and loose schooling based on conditions.
- **Evolutionary Niche**: Schooling that dynamically contracts (gets tighter) when danger is detected and expands for foraging when safe.
- **Known Weakness**: Transition lag between tight and loose states can leave fish vulnerable or hungry.
- **Parameters**:
  - `calm_cohesion`: range `[0.3, 0.6]`
  - `danger_cohesion`: range `[0.8, 1.2]`
  - `danger_threshold`: range `[150, 250]`


### Spiral

#### SpiralForager ⚠️ **[DEPRECATED]**
- **ID**: `spiral_forager`
- **Source File**: [core/algorithms/food_seeking/spiral.py](../core/algorithms/food_seeking/spiral.py)
- **Description**: NEW: Spiral outward from center to systematically cover area - replaces weak algorithms.
- **Evolutionary Niche**: Systematic search in uniform environments where food is sparse and evenly distributed.
- **Known Weakness**: Fixed geometric pattern makes it highly predictable and unable to dynamically pivot to nearby threats/opportunities.
- **Parameters**: None


### Surface

#### SurfaceSkimmer ⚠️ **[DEPRECATED]**
- **ID**: `surface_skimmer`
- **Source File**: [core/algorithms/food_seeking/surface.py](../core/algorithms/food_seeking/surface.py)
- **Description**: Stay near surface to catch falling food - IMPROVED for better survival.
- **Evolutionary Niche**: Shallow/surface food environments where food floats at the top.
- **Known Weakness**: Completely ignores food in the bottom half of the tank.
- **Parameters**:
  - `horizontal_speed`: range `[0.5, 1]`
  - `preferred_depth`: range `[0.1, 0.3]`


### Territory

#### TerritorialDefender
- **ID**: `territorial_defender`
- **Source File**: [core/algorithms/territory.py](../core/algorithms/territory.py)
- **Description**: Defend a territory from other fish.
- **Evolutionary Niche**: Patrolling and defending a local area containing reliable food resources.
- **Known Weakness**: Vulnerable if the local resource dries up; wastes energy chasing intruders.
- **Parameters**:
  - `aggression`: range `[0.5, 1]`
  - `territory_radius`: range `[80, 150]`

#### RandomExplorer
- **ID**: `random_explorer`
- **Source File**: [core/algorithms/territory.py](../core/algorithms/territory.py)
- **Description**: Explore randomly, covering new ground.
- **Evolutionary Niche**: Searching highly unpredictable environments with no structured food patterns.
- **Known Weakness**: Inefficient pathing, frequently re-visiting recently explored areas.
- **Parameters**:
  - `change_frequency`: range `[0.02, 0.08]`
  - `exploration_speed`: range `[0.5, 0.9]`

#### WallFollower
- **ID**: `wall_follower`
- **Source File**: [core/algorithms/territory.py](../core/algorithms/territory.py)
- **Description**: Follow along tank walls.
- **Evolutionary Niche**: Exploring boundaries or navigating large rectangular layouts.
- **Known Weakness**: Ignores the entire center of the environment where food or social groups might gather.
- **Parameters**:
  - `follow_speed`: range `[0.5, 0.8]`
  - `wall_distance`: range `[20, 60]`

#### CornerSeeker
- **ID**: `corner_seeker`
- **Source File**: [core/algorithms/territory.py](../core/algorithms/territory.py)
- **Description**: Prefer staying in corners.
- **Evolutionary Niche**: Finding shelter or hiding spots in corners where predator approach angles are halved.
- **Known Weakness**: Can get easily trapped; highly restricted food access.
- **Parameters**:
  - `approach_speed`: range `[0.4, 0.7]`

#### CenterHugger
- **ID**: `center_hugger`
- **Source File**: [core/algorithms/territory.py](../core/algorithms/territory.py)
- **Description**: Stay near the center of the tank.
- **Evolutionary Niche**: Staying in the center of the environment where food spawns are often dense.
- **Known Weakness**: High vulnerability to predators that cross the center, and high competition.
- **Parameters**:
  - `orbit_radius`: range `[50, 120]`
  - `return_strength`: range `[0.5, 0.9]`

#### RoutePatroller
- **ID**: `route_patroller`
- **Source File**: [core/algorithms/territory.py](../core/algorithms/territory.py)
- **Description**: Patrol between specific waypoints.
- **Evolutionary Niche**: Patrolling a predefined loop or waypoint sequence to monitor a large territory.
- **Known Weakness**: Inflexible path; can be easily predicted by predators or miss off-path food.
- **Parameters**:
  - `patrol_speed`: range `[0.5, 0.8]`
  - `waypoint_threshold`: range `[30, 60]`

#### BoundaryExplorer
- **ID**: `boundary_explorer`
- **Source File**: [core/algorithms/territory.py](../core/algorithms/territory.py)
- **Description**: Explore edges and boundaries.
- **Evolutionary Niche**: Searching along boundary edges for spawned food or escape paths.
- **Known Weakness**: High travel distance with low food exposure if food spawns centrally.
- **Parameters**:
  - `edge_preference`: range `[0.6, 1]`
  - `exploration_speed`: range `[0.5, 0.8]`

#### NomadicWanderer
- **ID**: `nomadic_wanderer`
- **Source File**: [core/algorithms/territory.py](../core/algorithms/territory.py)
- **Description**: Wander continuously without a home base.
- **Evolutionary Niche**: Long-distance migration to cover maximum ground over time.
- **Known Weakness**: High energy cost; prone to moving into high-danger areas.
- **Parameters**:
  - `direction_change_rate`: range `[0.01, 0.05]`
  - `wander_strength`: range `[0.5, 0.9]`


### Zigzag

#### ZigZagForager ⚠️ **[DEPRECATED]**
- **ID**: `zigzag_forager`
- **Source File**: [core/algorithms/food_seeking/zigzag.py](../core/algorithms/food_seeking/zigzag.py)
- **Description**: Move in zigzag pattern to maximize food discovery.
- **Evolutionary Niche**: Wide exploration in empty tanks to search for sparse, randomly distributed food.
- **Known Weakness**: Inefficient travel path (longer distance) when pursuing a specific, visible food item.
- **Parameters**:
  - `forward_speed`: range `[0.6, 1]`
  - `zigzag_amplitude`: range `[0.5, 1.2]`
  - `zigzag_frequency`: range `[0.02, 0.08]`


