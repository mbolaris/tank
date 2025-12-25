import math
import random
from typing import TYPE_CHECKING, List, Tuple

from core.math_utils import Vector2
from core.config.food import FOOD_SINK_ACCELERATION
from core.predictive_movement import predict_falling_intercept
from .definitions import (
    ThreatResponse,
    FoodApproach,
    EnergyStyle,
    SocialMode,
    PokerEngagement,
)

if TYPE_CHECKING:
    from core.entities import Fish


class BehaviorActionsMixin:
    """Implementations of sub-behavior execution logic.
    
    This mixin assumes the main class has:
    - parameters: Dict[str, float]
    - threat_response: ThreatResponse
    - food_approach: FoodApproach
    - energy_style: EnergyStyle
    - social_mode: SocialMode
    - poker_engagement: PokerEngagement
    - _burst_timer: int
    - _is_resting: bool
    - _circle_angle: float
    - _zigzag_phase: float
    - _patrol_angle: float
    - BehaviorHelpersMixin methods (_find_nearest, _safe_normalize, etc.)
    """

    def _execute_threat_response(self, fish: "Fish") -> Tuple[float, float, bool]:
        """Execute the selected threat response sub-behavior.

        Returns:
            (vx, vy, is_active) - velocity and whether threat response triggered
        """
        from core.entities import Crab

        # helpers.find_nearest assumed present
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
            # Add random perpendicular component (use environment RNG for determinism)
            perp = Vector2(-escape_dir.y, escape_dir.x)
            rng = getattr(fish.environment, "rng", random)
            erratic = (rng.random() - 0.5) * 2 * amplitude
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
            rng = getattr(fish.environment, "rng", random)
            if nearby and rng.random() < 0.3:  # 30% chance to engage
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
        # Gentle random walk (use environment RNG for determinism)
        rng = getattr(fish.environment, "rng", random)
        self._patrol_angle += (rng.random() - 0.5) * 0.2
        vx = math.cos(self._patrol_angle) * 0.3
        vy = math.sin(self._patrol_angle) * 0.3
        return vx, vy

    def _find_nearby_fish(self, fish: "Fish", radius: float) -> List["Fish"]:
        """Find nearby fish within radius."""
        from core.entities import Fish as FishClass

        env = fish.environment
        fish_id = fish.fish_id

        if hasattr(env, "nearby_evolving_agents"):
            nearby = env.nearby_evolving_agents(fish, radius)
        else:
            nearby = env.nearby_agents_by_type(fish, int(radius), FishClass)

        return sorted(
            [f for f in nearby if f.fish_id != fish_id],
            key=lambda f: f.fish_id
        )

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
