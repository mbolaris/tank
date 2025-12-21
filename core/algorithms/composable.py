"""Composable behavior system for fish.

This module provides a composable approach to fish behaviors where the genome
encodes selections from multiple sub-behavior categories plus continuous parameters.

Instead of 48 monolithic algorithms, behaviors are composed from:
- ThreatResponse: How to react to predators (4 options)
- FoodApproach: How to approach/hunt food (6 options)
- EnergyStyle: How to manage energy expenditure (3 options)
- SocialMode: How to interact with other fish (4 options)
- PokerEngagement: How to engage with poker opportunities (4 options)

This gives 4 × 6 × 3 × 4 × 4 = 1,152 behavior combinations, each with tunable
continuous parameters - enabling much richer evolutionary exploration.

The sub-behaviors are extracted from the existing 48 algorithms, preserving
the proven logic while making it composable.
"""

import math
import random
from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from core.algorithms.base import BehaviorAlgorithm, BehaviorHelpersMixin, Vector2
from core.constants import (
    FLEE_SPEED_CRITICAL,
    FLEE_SPEED_NORMAL,
    FLEE_THRESHOLD_CRITICAL,
    FLEE_THRESHOLD_LOW,
    FLEE_THRESHOLD_NORMAL,
    FOOD_SINK_ACCELERATION,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from core.predictive_movement import predict_falling_intercept

if TYPE_CHECKING:
    from core.entities import Fish


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


class EnergyStyle(IntEnum):
    """How to manage energy expenditure."""

    CONSERVATIVE = 0  # Slow, steady, minimize energy use
    BURST_REST = 1  # Alternate between bursts and resting
    BALANCED = 2  # Moderate speed, energy-aware adjustments


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
    "energy_style": len(EnergyStyle),
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
    "pursuit_speed": (0.6, 1.2),
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
    "poker_seek_radius": (80.0, 200.0),
    "poker_avoid_radius": (60.0, 150.0),
    "min_energy_for_poker": (0.3, 0.6),
    # Priority weights (how much each category influences final behavior)
    "threat_priority": (0.6, 1.0),  # Usually high - survival first
    "food_priority": (0.4, 0.9),
    "social_priority": (0.1, 0.5),
    "poker_priority": (0.1, 0.6),
}


def _random_params(rng: random.Random) -> Dict[str, float]:
    """Generate random parameters within bounds."""
    return {key: rng.uniform(low, high) for key, (low, high) in SUB_BEHAVIOR_PARAMS.items()}


# =============================================================================
# ComposableBehavior Class
# =============================================================================


@dataclass
class ComposableBehavior(BehaviorHelpersMixin):
    """A behavior composed of multiple sub-behavior selections plus parameters.

    This replaces the monolithic BehaviorAlgorithm with a composable structure
    that allows evolution to mix and match sub-behaviors while tuning parameters.

    Attributes:
        threat_response: Which threat response sub-behavior to use
        food_approach: Which food approach sub-behavior to use
        energy_style: Which energy management style to use
        social_mode: Which social interaction mode to use
        poker_engagement: Which poker engagement style to use
        parameters: Continuous parameters that tune sub-behavior execution
    """

    threat_response: ThreatResponse = ThreatResponse.PANIC_FLEE
    food_approach: FoodApproach = FoodApproach.DIRECT_PURSUIT
    energy_style: EnergyStyle = EnergyStyle.BALANCED
    social_mode: SocialMode = SocialMode.SOLO
    poker_engagement: PokerEngagement = PokerEngagement.PASSIVE
    parameters: Dict[str, float] = field(default_factory=dict)

    # Internal state for stateful behaviors
    _burst_timer: int = field(default=0, repr=False)
    _is_resting: bool = field(default=False, repr=False)
    _circle_angle: float = field(default=0.0, repr=False)
    _zigzag_phase: float = field(default=0.0, repr=False)
    _patrol_angle: float = field(default=0.0, repr=False)

    def __post_init__(self):
        """Initialize default parameters if not provided."""
        if not self.parameters:
            self.parameters = {
                key: (low + high) / 2 for key, (low, high) in SUB_BEHAVIOR_PARAMS.items()
            }

    @classmethod
    def create_random(cls, rng: Optional["random.Random"] = None) -> "ComposableBehavior":
        """Create a random composable behavior."""
        import random as random_module
        rng = rng or random_module.Random()
        return cls(
            threat_response=ThreatResponse(rng.randint(0, len(ThreatResponse) - 1)),
            food_approach=FoodApproach(rng.randint(0, len(FoodApproach) - 1)),
            energy_style=EnergyStyle(rng.randint(0, len(EnergyStyle) - 1)),
            social_mode=SocialMode(rng.randint(0, len(SocialMode) - 1)),
            poker_engagement=PokerEngagement(rng.randint(0, len(PokerEngagement) - 1)),
            parameters=_random_params(rng),
        )

    # Alias for backward compatibility
    random = create_random

    # -------------------------------------------------------------------------
    # Main Execute Method
    # -------------------------------------------------------------------------

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        """Execute the composed behavior and return desired velocity.

        The execution priority is:
        1. Threat response (if predator detected)
        2. Energy-critical food seeking (if starving)
        3. Poker engagement (if applicable)
        4. Social behavior blended with food seeking
        5. Default exploration

        Returns:
            Tuple of (velocity_x, velocity_y)
        """
        # Get energy state
        is_critical, is_low, energy_ratio = self._get_energy_state(fish)

        # Get priority weights
        threat_priority = self.parameters.get("threat_priority", 0.8)
        food_priority = self.parameters.get("food_priority", 0.6)
        social_priority = self.parameters.get("social_priority", 0.3)
        poker_priority = self.parameters.get("poker_priority", 0.3)

        # 1. THREAT RESPONSE - Check for predators first
        threat_vx, threat_vy, threat_active = self._execute_threat_response(fish)
        if threat_active:
            # Apply energy style modulation to escape
            speed_mod = self._get_energy_speed_modifier(fish, is_critical, is_low)
            return threat_vx * speed_mod, threat_vy * speed_mod

        # 2. CRITICAL ENERGY - Override everything for food
        if is_critical:
            food_vx, food_vy = self._execute_food_approach(fish, urgency=1.5)
            if food_vx != 0 or food_vy != 0:
                return food_vx, food_vy

        # 3. POKER ENGAGEMENT - Check if we should engage/avoid poker
        poker_vx, poker_vy, poker_active = self._execute_poker_engagement(fish, energy_ratio)
        if poker_active and poker_priority > random.random():
            return poker_vx, poker_vy

        # 4. BLENDED BEHAVIOR - Combine food seeking and social
        food_vx, food_vy = self._execute_food_approach(fish, urgency=1.0 if is_low else 0.7)
        social_vx, social_vy = self._execute_social_mode(fish)

        # Blend based on priorities and whether food was found
        if food_vx != 0 or food_vy != 0:
            # Food found - blend with social
            blend_ratio = food_priority / (food_priority + social_priority + 0.01)
            vx = food_vx * blend_ratio + social_vx * (1 - blend_ratio)
            vy = food_vy * blend_ratio + social_vy * (1 - blend_ratio)
        else:
            # No food - rely more on social/exploration
            vx, vy = social_vx, social_vy
            if vx == 0 and vy == 0:
                # Default exploration
                vx, vy = self._default_exploration(fish)

        # Apply energy style speed modulation
        speed_mod = self._get_energy_speed_modifier(fish, is_critical, is_low)
        return vx * speed_mod, vy * speed_mod

    # -------------------------------------------------------------------------
    # Sub-behavior Execution Methods
    # -------------------------------------------------------------------------

    def _execute_threat_response(self, fish: "Fish") -> Tuple[float, float, bool]:
        """Execute the selected threat response sub-behavior.

        Returns:
            (vx, vy, is_active) - velocity and whether threat response triggered
        """
        from core.entities import Crab

        predator = self._find_nearest(fish, Crab, max_distance=200.0)
        if not predator:
            return 0.0, 0.0, False

        distance = (predator.pos - fish.pos).length()
        flee_threshold = self.parameters.get("flee_threshold", 120.0)

        if distance > flee_threshold:
            return 0.0, 0.0, False

        escape_dir = self._safe_normalize(fish.pos - predator.pos)

        if self.threat_response == ThreatResponse.PANIC_FLEE:
            speed = self.parameters.get("flee_speed", 1.2)
            return escape_dir.x * speed, escape_dir.y * speed, True

        elif self.threat_response == ThreatResponse.STEALTH_AVOID:
            speed = self.parameters.get("stealth_speed", 0.3)
            return escape_dir.x * speed, escape_dir.y * speed, True

        elif self.threat_response == ThreatResponse.FREEZE:
            freeze_dist = self.parameters.get("freeze_distance", 60.0)
            if distance < freeze_dist:
                return 0.0, 0.0, True  # Freeze in place
            # Outside freeze zone, move slowly away
            return escape_dir.x * 0.2, escape_dir.y * 0.2, True

        elif self.threat_response == ThreatResponse.ERRATIC_EVADE:
            speed = self.parameters.get("flee_speed", 1.0)
            amplitude = self.parameters.get("erratic_amplitude", 0.5)
            # Add random perpendicular component
            perp = Vector2(-escape_dir.y, escape_dir.x)
            erratic = (random.random() - 0.5) * 2 * amplitude
            vx = escape_dir.x * speed + perp.x * erratic
            vy = escape_dir.y * speed + perp.y * erratic
            return vx, vy, True

        return 0.0, 0.0, False

    def _execute_food_approach(self, fish: "Fish", urgency: float = 1.0) -> Tuple[float, float]:
        """Execute the selected food approach sub-behavior.

        Args:
            urgency: Speed multiplier based on energy state

        Returns:
            (vx, vy) velocity toward food, or (0, 0) if no food
        """
        nearest_food = self._find_nearest_food(fish)
        if not nearest_food:
            return 0.0, 0.0

        distance = (nearest_food.pos - fish.pos).length()
        base_speed = self.parameters.get("pursuit_speed", 0.8) * urgency
        
        # Calculate target position - use prediction for moving food
        # This is the KEY FIX: predict where food will be, accounting for acceleration
        target_pos = nearest_food.pos  # Default: current position
        
        if hasattr(nearest_food, "vel") and hasattr(nearest_food, "food_properties"):
            # It's a Food entity - check if it's moving
            food_vel = nearest_food.vel
            if food_vel.length() > 0.01:  # Lower threshold: catch newly spawned food too
                # Get the sink multiplier for this food type
                sink_multiplier = nearest_food.food_properties.get("sink_multiplier", 1.0)
                acceleration = FOOD_SINK_ACCELERATION * sink_multiplier
                
                # Use acceleration-aware prediction for sinking food
                if acceleration > 0 and food_vel.y >= 0:  # Falling food
                    target_pos, _ = predict_falling_intercept(
                        fish.pos, fish.speed, nearest_food.pos, food_vel, acceleration
                    )
                else:
                    # Non-sinking food (like live food) - simple linear prediction
                    time_to_reach = distance / max(fish.speed, 0.1)
                    time_to_reach = min(time_to_reach, 60.0)  # Cap at ~2 seconds
                    target_pos = Vector2(
                        nearest_food.pos.x + food_vel.x * time_to_reach,
                        nearest_food.pos.y + food_vel.y * time_to_reach,
                    )
        elif hasattr(nearest_food, "vel"):
            # Has velocity but not food_properties - use simple prediction
            food_vel = nearest_food.vel
            if food_vel.length() > 0.01:
                time_to_reach = distance / max(fish.speed, 0.1)
                time_to_reach = min(time_to_reach, 60.0)
                target_pos = Vector2(
                    nearest_food.pos.x + food_vel.x * time_to_reach,
                    nearest_food.pos.y + food_vel.y * time_to_reach,
                )
        
        # Now calculate direction to predicted target position
        direction = self._safe_normalize(target_pos - fish.pos)
        predicted_distance = (target_pos - fish.pos).length()

        if self.food_approach == FoodApproach.DIRECT_PURSUIT:
            # Direct pursuit now uses predicted position
            return direction.x * base_speed, direction.y * base_speed

        elif self.food_approach == FoodApproach.PREDICTIVE_INTERCEPT:
            # Already using predicted position above, just apply skill-based speed boost
            skill = self.parameters.get("intercept_skill", 0.5)
            # Higher skill = faster pursuit (not position blending)
            speed = base_speed * (1.0 + skill * 0.3)
            return direction.x * speed, direction.y * speed

        elif self.food_approach == FoodApproach.CIRCLING_STRIKE:
            circle_radius = self.parameters.get("circle_radius", 50.0)
            circle_speed = self.parameters.get("circle_speed", 0.1)
            strike_distance = self.parameters.get("ambush_strike_distance", 30.0)

            if predicted_distance < strike_distance:
                # Close enough - strike directly at predicted position
                return direction.x * base_speed * 1.3, direction.y * base_speed * 1.3
            elif predicted_distance < circle_radius * 2:
                # Circle around predicted food position
                self._circle_angle += circle_speed
                offset = Vector2(
                    math.cos(self._circle_angle) * circle_radius,
                    math.sin(self._circle_angle) * circle_radius,
                )
                circle_target = Vector2(target_pos.x + offset.x, target_pos.y + offset.y)
                circle_dir = self._safe_normalize(circle_target - fish.pos)
                return circle_dir.x * base_speed * 0.8, circle_dir.y * base_speed * 0.8
            else:
                # Too far - approach predicted position
                return direction.x * base_speed, direction.y * base_speed

        elif self.food_approach == FoodApproach.AMBUSH_WAIT:
            patience = self.parameters.get("ambush_patience", 0.7)
            strike_dist = self.parameters.get("ambush_strike_distance", 40.0)

            if predicted_distance < strike_dist:
                # Strike at predicted position
                return direction.x * base_speed * 1.5, direction.y * base_speed * 1.5
            elif predicted_distance < strike_dist * 3:
                # Wait patiently (move very slowly toward predicted position)
                return direction.x * 0.1 * patience, direction.y * 0.1 * patience
            else:
                # Too far, reposition toward predicted position
                return direction.x * 0.4, direction.y * 0.4

        elif self.food_approach == FoodApproach.ZIGZAG_SEARCH:
            amplitude = self.parameters.get("zigzag_amplitude", 0.6)
            frequency = self.parameters.get("zigzag_frequency", 0.05)
            self._zigzag_phase += frequency
            # Zigzag toward predicted position
            perp = Vector2(-direction.y, direction.x)
            zigzag = math.sin(self._zigzag_phase) * amplitude
            vx = direction.x * base_speed + perp.x * zigzag
            vy = direction.y * base_speed + perp.y * zigzag
            return vx, vy

        elif self.food_approach == FoodApproach.PATROL_ROUTE:
            patrol_radius = self.parameters.get("patrol_radius", 100.0)
            food_priority = self.parameters.get("food_priority", 0.7)

            # If food is close, divert from patrol toward predicted position
            if predicted_distance < patrol_radius * 0.5:
                return direction.x * base_speed, direction.y * base_speed

            # Otherwise, blend patrol with predicted food direction
            self._patrol_angle += 0.02
            patrol_dir = Vector2(math.cos(self._patrol_angle), math.sin(self._patrol_angle))
            blend = food_priority
            vx = direction.x * blend + patrol_dir.x * (1 - blend)
            vy = direction.y * blend + patrol_dir.y * (1 - blend)
            speed = base_speed * 0.7
            return vx * speed, vy * speed

        return direction.x * base_speed, direction.y * base_speed

    def _execute_social_mode(self, fish: "Fish") -> Tuple[float, float]:
        """Execute the selected social mode sub-behavior.

        Returns:
            (vx, vy) social velocity influence
        """
        if self.social_mode == SocialMode.SOLO:
            return 0.0, 0.0

        # Find nearby fish
        from core.entities import Fish as FishClass

        social_distance = self.parameters.get("social_distance", 50.0)
        nearby = self._find_nearby_fish(fish, social_distance * 2)

        if not nearby:
            return 0.0, 0.0

        if self.social_mode == SocialMode.LOOSE_SCHOOL:
            cohesion = self.parameters.get("cohesion_strength", 0.4)
            separation = self.parameters.get("separation_distance", 25.0)
            return self._boids_behavior(fish, nearby, cohesion, 0.0, separation)

        elif self.social_mode == SocialMode.TIGHT_SCHOOL:
            cohesion = self.parameters.get("cohesion_strength", 0.7)
            alignment = self.parameters.get("alignment_strength", 0.4)
            separation = self.parameters.get("separation_distance", 15.0)
            return self._boids_behavior(fish, nearby, cohesion, alignment, separation)

        elif self.social_mode == SocialMode.FOLLOW_LEADER:
            follow_dist = self.parameters.get("follow_distance", 40.0)
            # Find fish that's ahead (higher x or in direction of movement)
            leader = None
            best_score = -float("inf")
            for other in nearby:
                # Score by how "ahead" they are
                delta = other.pos - fish.pos
                score = delta.x + delta.y  # Simple heuristic
                if score > best_score:
                    best_score = score
                    leader = other

            if leader:
                direction = self._safe_normalize(leader.pos - fish.pos)
                dist = (leader.pos - fish.pos).length()
                if dist > follow_dist:
                    return direction.x * 0.6, direction.y * 0.6
                elif dist < follow_dist * 0.5:
                    return -direction.x * 0.3, -direction.y * 0.3  # Too close

        return 0.0, 0.0

    def _execute_poker_engagement(
        self, fish: "Fish", energy_ratio: float
    ) -> Tuple[float, float, bool]:
        """Execute the selected poker engagement sub-behavior.

        Returns:
            (vx, vy, is_active) - velocity and whether poker behavior is active
        """
        min_energy = self.parameters.get("min_energy_for_poker", 0.4)

        if self.poker_engagement == PokerEngagement.AVOID:
            avoid_radius = self.parameters.get("poker_avoid_radius", 100.0)
            nearby = self._find_nearby_fish(fish, avoid_radius)
            if nearby:
                # Move away from nearest fish
                nearest = min(nearby, key=lambda f: (f.pos - fish.pos).length())
                direction = self._safe_normalize(fish.pos - nearest.pos)
                return direction.x * 0.5, direction.y * 0.5, True
            return 0.0, 0.0, False

        elif self.poker_engagement == PokerEngagement.PASSIVE:
            return 0.0, 0.0, False

        elif self.poker_engagement == PokerEngagement.OPPORTUNISTIC:
            if energy_ratio < min_energy:
                return 0.0, 0.0, False
            seek_radius = self.parameters.get("poker_seek_radius", 120.0)
            nearby = self._find_nearby_fish(fish, seek_radius)
            if nearby and random.random() < 0.3:  # 30% chance to engage
                nearest = min(nearby, key=lambda f: (f.pos - fish.pos).length())
                direction = self._safe_normalize(nearest.pos - fish.pos)
                return direction.x * 0.6, direction.y * 0.6, True
            return 0.0, 0.0, False

        elif self.poker_engagement == PokerEngagement.AGGRESSIVE:
            if energy_ratio < min_energy * 0.7:  # Lower threshold for aggressive
                return 0.0, 0.0, False
            seek_radius = self.parameters.get("poker_seek_radius", 150.0)
            nearby = self._find_nearby_fish(fish, seek_radius)
            if nearby:
                nearest = min(nearby, key=lambda f: (f.pos - fish.pos).length())
                direction = self._safe_normalize(nearest.pos - fish.pos)
                return direction.x * 0.9, direction.y * 0.9, True
            return 0.0, 0.0, False

        return 0.0, 0.0, False

    def _get_energy_speed_modifier(
        self, fish: "Fish", is_critical: bool, is_low: bool
    ) -> float:
        """Get speed modifier based on energy style and current energy state."""
        base_mod = self.parameters.get("base_speed_multiplier", 0.8)

        if self.energy_style == EnergyStyle.CONSERVATIVE:
            # Always slow, slightly faster when critical (desperate)
            return base_mod * (1.1 if is_critical else 0.7)

        elif self.energy_style == EnergyStyle.BURST_REST:
            burst_duration = int(self.parameters.get("burst_duration", 60))
            rest_duration = int(self.parameters.get("rest_duration", 60))
            burst_speed = self.parameters.get("burst_speed", 1.3)

            self._burst_timer += 1
            cycle_length = burst_duration + rest_duration

            if self._burst_timer >= cycle_length:
                self._burst_timer = 0
                self._is_resting = False

            if self._burst_timer < burst_duration:
                self._is_resting = False
                return base_mod * burst_speed
            else:
                self._is_resting = True
                return base_mod * 0.3  # Resting

        elif self.energy_style == EnergyStyle.BALANCED:
            urgency_threshold = self.parameters.get("energy_urgency_threshold", 0.4)
            if is_critical:
                return base_mod * 1.2  # Speed up when desperate
            elif is_low:
                return base_mod * 1.0  # Normal
            else:
                return base_mod * 0.8  # Conserve when comfortable

        return base_mod

    def _default_exploration(self, fish: "Fish") -> Tuple[float, float]:
        """Default wandering behavior when nothing else applies."""
        # Gentle random walk
        self._patrol_angle += (random.random() - 0.5) * 0.2
        vx = math.cos(self._patrol_angle) * 0.3
        vy = math.sin(self._patrol_angle) * 0.3
        return vx, vy

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _find_nearby_fish(self, fish: "Fish", radius: float) -> List["Fish"]:
        """Find nearby fish within radius."""
        from core.entities import Fish as FishClass

        env = fish.environment
        fish_id = fish.fish_id

        if hasattr(env, "nearby_evolving_agents"):
            nearby = env.nearby_evolving_agents(fish, radius)
        elif hasattr(env, "nearby_fish"):
            nearby = env.nearby_fish(fish, radius)
        else:
            nearby = env.nearby_agents_by_type(fish, int(radius), FishClass)

        return [f for f in nearby if f.fish_id != fish_id]

    def _boids_behavior(
        self,
        fish: "Fish",
        neighbors: List["Fish"],
        cohesion: float,
        alignment: float,
        separation: float,
    ) -> Tuple[float, float]:
        """Classic boids algorithm for schooling."""
        if not neighbors:
            return 0.0, 0.0

        # Cohesion: steer toward center of neighbors
        center_x = sum(f.pos.x for f in neighbors) / len(neighbors)
        center_y = sum(f.pos.y for f in neighbors) / len(neighbors)
        cohesion_dir = self._safe_normalize(
            Vector2(center_x - fish.pos.x, center_y - fish.pos.y)
        )

        # Alignment: match average heading (approximate from positions)
        # Simplified: move toward where neighbors are heading (their forward direction)
        align_x, align_y = 0.0, 0.0
        for neighbor in neighbors:
            if hasattr(neighbor, "vel"):
                align_x += neighbor.vel.x
                align_y += neighbor.vel.y
        if len(neighbors) > 0:
            align_x /= len(neighbors)
            align_y /= len(neighbors)
        align_dir = self._safe_normalize(Vector2(align_x, align_y))

        # Separation: steer away from very close neighbors
        sep_x, sep_y = 0.0, 0.0
        for neighbor in neighbors:
            dist = (neighbor.pos - fish.pos).length()
            if dist < separation and dist > 0:
                away = self._safe_normalize(fish.pos - neighbor.pos)
                sep_x += away.x / dist
                sep_y += away.y / dist

        # Combine forces
        vx = cohesion_dir.x * cohesion + align_dir.x * alignment + sep_x * 0.5
        vy = cohesion_dir.y * cohesion + align_dir.y * alignment + sep_y * 0.5

        return vx, vy

    # -------------------------------------------------------------------------
    # Mutation Methods
    # -------------------------------------------------------------------------

    def mutate(
        self,
        mutation_rate: float = 0.1,
        mutation_strength: float = 0.15,
        sub_behavior_switch_rate: float = 0.05,
        rng: Optional["random.Random"] = None,
    ) -> None:
        """Mutate the composable behavior.

        Args:
            mutation_rate: Probability of each parameter mutating
            mutation_strength: Magnitude of parameter mutations
            sub_behavior_switch_rate: Probability of switching each sub-behavior
            rng: Random number generator
        """
        import random as random_module
        rng = rng or random_module.Random()

        # Mutate sub-behavior selections (discrete)
        if rng.random() < sub_behavior_switch_rate:
            self.threat_response = ThreatResponse(rng.randint(0, len(ThreatResponse) - 1))
        if rng.random() < sub_behavior_switch_rate:
            self.food_approach = FoodApproach(rng.randint(0, len(FoodApproach) - 1))
        if rng.random() < sub_behavior_switch_rate:
            self.energy_style = EnergyStyle(rng.randint(0, len(EnergyStyle) - 1))
        if rng.random() < sub_behavior_switch_rate:
            self.social_mode = SocialMode(rng.randint(0, len(SocialMode) - 1))
        if rng.random() < sub_behavior_switch_rate:
            self.poker_engagement = PokerEngagement(rng.randint(0, len(PokerEngagement) - 1))

        # Mutate continuous parameters
        for key, value in list(self.parameters.items()):
            if rng.random() < mutation_rate:
                bounds = SUB_BEHAVIOR_PARAMS.get(key, (0.0, 1.0))
                span = bounds[1] - bounds[0]
                delta = rng.gauss(0, mutation_strength * span)
                new_value = max(bounds[0], min(bounds[1], value + delta))
                self.parameters[key] = new_value

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for storage/transmission."""
        return {
            "type": "ComposableBehavior",
            "threat_response": int(self.threat_response),
            "food_approach": int(self.food_approach),
            "energy_style": int(self.energy_style),
            "social_mode": int(self.social_mode),
            "poker_engagement": int(self.poker_engagement),
            "parameters": dict(self.parameters),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComposableBehavior":
        """Deserialize from dictionary."""
        return cls(
            threat_response=ThreatResponse(data.get("threat_response", 0)),
            food_approach=FoodApproach(data.get("food_approach", 0)),
            energy_style=EnergyStyle(data.get("energy_style", 2)),
            social_mode=SocialMode(data.get("social_mode", 0)),
            poker_engagement=PokerEngagement(data.get("poker_engagement", 1)),
            parameters=data.get("parameters", {}),
        )

    # -------------------------------------------------------------------------
    # Inheritance / Crossover
    # -------------------------------------------------------------------------

    @classmethod
    def from_parents(
        cls,
        parent1: "ComposableBehavior",
        parent2: "ComposableBehavior",
        weight1: float = 0.5,
        mutation_rate: float = 0.1,
        mutation_strength: float = 0.15,
        sub_behavior_switch_rate: float = 0.03,
        rng: Optional["random.Random"] = None,
    ) -> "ComposableBehavior":
        """Create offspring by crossing over two parent behaviors.

        Sub-behaviors are inherited Mendelian-style (pick one parent).
        Parameters are blended with weighting.

        Args:
            parent1: First parent behavior
            parent2: Second parent behavior
            weight1: Weight for parent1 (0.0-1.0), parent2 gets (1-weight1)
            mutation_rate: Probability of each parameter mutating
            mutation_strength: Magnitude of mutations
            sub_behavior_switch_rate: Extra chance of random sub-behavior switch
            rng: Random number generator
        """
        import random as random_module
        rng = rng or random_module.Random()

        # Mendelian inheritance for discrete sub-behaviors
        threat_response = (
            parent1.threat_response if rng.random() < weight1 else parent2.threat_response
        )
        food_approach = (
            parent1.food_approach if rng.random() < weight1 else parent2.food_approach
        )
        energy_style = (
            parent1.energy_style if rng.random() < weight1 else parent2.energy_style
        )
        social_mode = (
            parent1.social_mode if rng.random() < weight1 else parent2.social_mode
        )
        poker_engagement = (
            parent1.poker_engagement if rng.random() < weight1 else parent2.poker_engagement
        )

        # Blend parameters
        all_keys = set(parent1.parameters.keys()) | set(parent2.parameters.keys())
        blended_params = {}
        for key in all_keys:
            val1 = parent1.parameters.get(key, SUB_BEHAVIOR_PARAMS.get(key, (0.5, 0.5))[0])
            val2 = parent2.parameters.get(key, SUB_BEHAVIOR_PARAMS.get(key, (0.5, 0.5))[0])
            blended_params[key] = val1 * weight1 + val2 * (1 - weight1)

        # Create offspring
        offspring = cls(
            threat_response=threat_response,
            food_approach=food_approach,
            energy_style=energy_style,
            social_mode=social_mode,
            poker_engagement=poker_engagement,
            parameters=blended_params,
        )

        # Apply mutations
        offspring.mutate(
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            sub_behavior_switch_rate=sub_behavior_switch_rate,
            rng=rng,
        )

        return offspring

    def clone_with_mutation(
        self,
        mutation_rate: float = 0.1,
        mutation_strength: float = 0.15,
        sub_behavior_switch_rate: float = 0.05,
        rng: Optional["random.Random"] = None,
    ) -> "ComposableBehavior":
        """Create a mutated clone (for asexual reproduction)."""
        import random as random_module
        rng = rng or random_module.Random()
        clone = ComposableBehavior(
            threat_response=self.threat_response,
            food_approach=self.food_approach,
            energy_style=self.energy_style,
            social_mode=self.social_mode,
            poker_engagement=self.poker_engagement,
            parameters=dict(self.parameters),
        )
        clone.mutate(mutation_rate, mutation_strength, sub_behavior_switch_rate, rng)
        return clone

    # -------------------------------------------------------------------------
    # Descriptive Properties
    # -------------------------------------------------------------------------

    @property
    def behavior_id(self) -> str:
        """Get a unique string ID for this behavior combination."""
        return (
            f"{self.threat_response.name.lower()}_"
            f"{self.food_approach.name.lower()}_"
            f"{self.energy_style.name.lower()}_"
            f"{self.social_mode.name.lower()}_"
            f"{self.poker_engagement.name.lower()}"
        )

    @property
    def short_description(self) -> str:
        """Get a human-readable short description."""
        threat_names = ["panicky", "stealthy", "freezer", "erratic"]
        food_names = ["direct", "predictive", "circler", "ambusher", "zigzagger", "patroller"]
        energy_names = ["conservative", "bursty", "balanced"]
        social_names = ["loner", "loose", "tight", "follower"]
        poker_names = ["avoider", "passive", "opportunist", "challenger"]

        return (
            f"{threat_names[self.threat_response]} "
            f"{food_names[self.food_approach]} "
            f"{energy_names[self.energy_style]} "
            f"{social_names[self.social_mode]} "
            f"{poker_names[self.poker_engagement]}"
        )
