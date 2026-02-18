import random
from enum import IntEnum

# =============================================================================
# Sub-behavior Enums - Each category has discrete options
# =============================================================================


class ThreatResponse(IntEnum):
    """How to react when predators are detected."""

    PANIC_FLEE = 0  # Flee at max speed directly away
    STEALTH_AVOID = 1  # Move slowly and carefully away
    FREEZE = 2  # Stop moving when predator is close
    ERRATIC_EVADE = 3  # Unpredictable zigzag escape


class FoodApproach(IntEnum):
    """How to approach and capture food."""

    DIRECT_PURSUIT = 0  # Beeline to nearest food
    PREDICTIVE_INTERCEPT = 1  # Predict where moving food will be
    CIRCLING_STRIKE = 2  # Circle around food before striking
    AMBUSH_WAIT = 3  # Wait for food to come close
    ZIGZAG_SEARCH = 4  # Zigzag pattern to find food
    PATROL_ROUTE = 5  # Follow patrol pattern, divert for food


# NOTE: EnergyStyle was removed to simplify the behavior system.
# The 3 energy styles (CONSERVATIVE, BURST_REST, BALANCED) added complexity
# without meaningful evolutionary differentiation. Speed modulation is now
# handled by a simple energy-based formula in _get_energy_speed_modifier().


class SocialMode(IntEnum):
    """How to interact with other fish."""

    SOLO = 0  # Ignore other fish, act independently
    LOOSE_SCHOOL = 1  # Maintain loose proximity to others
    TIGHT_SCHOOL = 2  # Stay very close to group
    FOLLOW_LEADER = 3  # Follow the nearest fish ahead


class PokerEngagement(IntEnum):
    """How to engage with poker game opportunities."""

    AVOID = 0  # Actively avoid other fish / poker
    PASSIVE = 1  # Neither seek nor avoid poker
    OPPORTUNISTIC = 2  # Engage if convenient and energy allows
    AGGRESSIVE = 3  # Actively seek poker games


# Category counts for inheritance bounds
SUB_BEHAVIOR_COUNTS = {
    "threat_response": len(ThreatResponse),
    "food_approach": len(FoodApproach),
    "social_mode": len(SocialMode),
    "poker_engagement": len(PokerEngagement),
}


# =============================================================================
# Sub-behavior Parameter Bounds
# =============================================================================

# Each sub-behavior type has associated continuous parameters
SUB_BEHAVIOR_PARAMS = {
    # Threat response parameters
    "flee_speed": (0.8, 1.5),
    "flee_threshold": (80.0, 180.0),
    "stealth_speed": (0.2, 0.5),
    "freeze_distance": (40.0, 100.0),
    "erratic_amplitude": (0.3, 0.8),
    # Food approach parameters
    # Increased pursuit_speed from (0.8, 1.2) to (0.9, 1.4) based on experiment
    # showing 98.9% starvation - fish need to catch food faster
    "pursuit_speed": (0.9, 1.4),
    "intercept_skill": (0.3, 0.9),
    "circle_radius": (30.0, 80.0),
    "circle_speed": (0.05, 0.15),
    "ambush_patience": (0.5, 1.0),
    "ambush_strike_distance": (20.0, 60.0),
    "zigzag_amplitude": (0.4, 1.0),
    "zigzag_frequency": (0.02, 0.08),
    "patrol_radius": (60.0, 150.0),
    # Energy style parameters
    "base_speed_multiplier": (0.5, 1.0),
    "burst_speed": (1.1, 1.5),
    "burst_duration": (30.0, 90.0),
    "rest_duration": (40.0, 100.0),
    "energy_urgency_threshold": (0.3, 0.6),
    # Social mode parameters
    "social_distance": (30.0, 80.0),
    "cohesion_strength": (0.3, 0.8),
    "alignment_strength": (0.2, 0.6),
    "separation_distance": (15.0, 40.0),
    "follow_distance": (20.0, 60.0),
    # Poker engagement parameters
    "poker_seek_radius": (120.0, 240.0),  # Wider search to trigger more poker games
    "poker_avoid_radius": (60.0, 150.0),
    "min_energy_for_poker": (0.25, 0.5),  # Allow poker engagement at slightly lower energy
    # Priority weights (how much each category influences final behavior)
    "threat_priority": (0.6, 1.0),  # Usually high - survival first
    # Increased food_priority from (0.4, 0.9) to (0.5, 0.95) based on experiment
    # showing fish need to prioritize food more aggressively to survive
    "food_priority": (0.5, 0.95),
    "social_priority": (0.1, 0.5),
    "poker_priority": (0.2, 0.75),  # Increase likelihood of choosing poker actions
}


def _random_params(rng: random.Random) -> dict[str, float]:
    """Generate random parameters within bounds."""
    return {key: rng.uniform(low, high) for key, (low, high) in SUB_BEHAVIOR_PARAMS.items()}
