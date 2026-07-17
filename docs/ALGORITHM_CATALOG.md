# Tank World Algorithm Catalog

> This catalog is dynamically generated from the codebase registry. It documents all available fish behavior algorithms, their configuration bounds, and evolutionary characteristics.

---

## Table of Contents
1. [The Composable Behavior Framework](#the-composable-behavior-framework)
2. [Specialized/Monolithic Behavior Algorithms](#specializedmonolithic-behavior-algorithms)
   - [Cooperative](#cooperative)
   - [Opportunistic](#opportunistic)
   - [Quality](#quality)

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
