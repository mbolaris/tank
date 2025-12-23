"""Poker interaction behavior algorithms.

This module contains algorithms focused on poker-based fish interactions:
- PokerChallenger: Actively seeks out other fish for poker games
- PokerDodger: Avoids other fish to prevent poker games
- PokerGambler: Seeks poker aggressively when high energy
- SelectivePoker: Only engages in poker when conditions are favorable
- PokerOpportunist: Balances food seeking with poker opportunities
- PokerStrategist: Uses opponent modeling and position awareness
- PokerBluffer: Varies behavior unpredictably to confuse opponents
- PokerConservative: Risk-averse, plays only when highly favorable

Performance optimizations:
- Uses spatial queries (nearby_evolving_agents) instead of get_agents_of_type
- Uses squared distances to avoid sqrt overhead
- Caches fish position coordinates
"""

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional, Tuple

from core.algorithms.base import BehaviorAlgorithm
from core.entities import Crab
from core.entities import Fish as FishClass
from core.world import World  # Import World Protocol

if TYPE_CHECKING:
    from core.entities import Fish


def _find_nearest_fish_spatial(fish: "Fish", radius: float) -> Tuple[Optional["Fish"], float]:
    """Find nearest other fish using optimized spatial query.

    Performance: Uses spatial grid query instead of iterating all fish.
    Returns squared distance to avoid sqrt overhead.

    Args:
        fish: The fish searching for others
        radius: Search radius

    Returns:
        Tuple of (nearest_fish, distance_squared) or (None, inf)
    """
    env: World = fish.environment  # Type hint as World Protocol
    
    # Use generic method if available, fall back to type query
    if hasattr(env, "nearby_evolving_agents"):
        nearby = env.nearby_evolving_agents(fish, radius)
    else:
        nearby = env.nearby_agents_by_type(fish, radius, FishClass)

    if not nearby:
        return None, float('inf')

    fish_x, fish_y = fish.pos.x, fish.pos.y
    fish_id = fish.fish_id

    min_dist_sq = float('inf')
    nearest = None

    for other in nearby:
        if other.fish_id == fish_id:
            continue
        dx = other.pos.x - fish_x
        dy = other.pos.y - fish_y
        dist_sq = dx * dx + dy * dy
        if dist_sq < min_dist_sq:
            min_dist_sq = dist_sq
            nearest = other

    return nearest, min_dist_sq


def _get_nearby_fish_spatial(fish: "Fish", radius: float) -> List["Fish"]:
    """Get nearby fish using optimized spatial query.

    Args:
        fish: The fish searching for others
        radius: Search radius

    Returns:
        List of nearby fish (excluding self)
    """
    env: World = fish.environment
    fish_id = fish.fish_id

    if hasattr(env, "nearby_evolving_agents"):
        nearby = env.nearby_evolving_agents(fish, radius)
    else:
        nearby = env.nearby_agents_by_type(fish, radius, FishClass)

    return [f for f in nearby if f.fish_id != fish_id]


@dataclass
class PokerChallenger(BehaviorAlgorithm):
    """Actively seeks out other fish for poker games."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng if rng is not None else random.Random()
        super().__init__(
            algorithm_id="poker_challenger",
            parameters={
                "challenge_radius": rng.uniform(100.0, 250.0),
                "challenge_speed": rng.uniform(0.8, 1.3),
                "min_energy_to_challenge": rng.uniform(15.0, 30.0),
            },
        )
        self.rng = rng

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        import math
        fish_x, fish_y = fish.pos.x, fish.pos.y

        # First check for predators - survival comes first
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            dx = nearest_predator.pos.x - fish_x
            dy = nearest_predator.pos.y - fish_y
            dist_sq = dx * dx + dy * dy
            if dist_sq < 14400:  # 120^2
                dist = math.sqrt(dist_sq)
                if dist > 0:
                    # Flee from predator (normalize and flip direction)
                    return -dx / dist * 1.2, -dy / dist * 1.2
                return 0, 0

        # Only seek poker if we have enough energy
        if fish.energy < self.parameters["min_energy_to_challenge"]:
            # Low energy - seek food instead
            nearest_food = self._find_nearest_food(fish)
            if nearest_food:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                return direction.x * 0.8, direction.y * 0.8
            return 0, 0

        # OPTIMIZATION: Use spatial query instead of get_agents_of_type
        challenge_radius = self.parameters["challenge_radius"]
        nearest_fish, dist_sq = _find_nearest_fish_spatial(fish, challenge_radius)

        if nearest_fish is not None:
            # Move toward the fish for poker
            direction = self._safe_normalize(nearest_fish.pos - fish.pos)
            speed = self.parameters["challenge_speed"]
            return direction.x * speed, direction.y * speed

        # No fish nearby - wander
        rng = getattr(self, "rng", None) or random
        return rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5)


@dataclass
class PokerDodger(BehaviorAlgorithm):
    """Avoids other fish to prevent poker games."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng if rng is not None else random.Random()
        super().__init__(
            algorithm_id="poker_dodger",
            parameters={
                "avoidance_radius": rng.uniform(80.0, 150.0),
                "avoidance_speed": rng.uniform(0.7, 1.1),
                "food_priority": rng.uniform(0.6, 1.0),
            },
        )
        self.rng = rng

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        # First check for predators
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            dx = nearest_predator.pos.x - fish.pos.x
            dy = nearest_predator.pos.y - fish.pos.y
            dist_sq = dx * dx + dy * dy
            if dist_sq < 14400:  # 120^2
                import math
                dist = math.sqrt(dist_sq)
                if dist > 0:
                    return -dx / dist * 1.2, -dy / dist * 1.2
                return 0, 0

        # OPTIMIZATION: Use spatial query with avoidance radius
        avoidance_radius = self.parameters["avoidance_radius"]
        avoidance_radius_sq = avoidance_radius * avoidance_radius
        other_fish = _get_nearby_fish_spatial(fish, avoidance_radius)

        # Calculate avoidance vector using raw floats (avoid Vector2 allocations)
        avoidance_x = 0.0
        avoidance_y = 0.0
        fish_nearby = 0
        fish_x, fish_y = fish.pos.x, fish.pos.y

        for other in other_fish:
            dx = other.pos.x - fish_x
            dy = other.pos.y - fish_y
            dist_sq = dx * dx + dy * dy

            if dist_sq > 0 and dist_sq < avoidance_radius_sq:
                import math
                distance = math.sqrt(dist_sq)
                # Avoid this fish - direction away from other
                inv_dist = 1.0 / distance
                avoid_x = -dx * inv_dist
                avoid_y = -dy * inv_dist
                # Stronger avoidance for closer fish
                strength = (avoidance_radius - distance) / avoidance_radius
                avoidance_x += avoid_x * strength
                avoidance_y += avoid_y * strength
                fish_nearby += 1

        # If fish are nearby, move away from them
        if fish_nearby > 0:
            # Normalize avoidance vector
            import math
            avoid_len = math.sqrt(avoidance_x * avoidance_x + avoidance_y * avoidance_y)
            if avoid_len > 0:
                avoidance_x /= avoid_len
                avoidance_y /= avoid_len

            speed = self.parameters["avoidance_speed"]

            # Still seek food while avoiding
            nearest_food = self._find_nearest_food(fish)
            if nearest_food:
                food_dx = nearest_food.pos.x - fish_x
                food_dy = nearest_food.pos.y - fish_y
                food_dist_sq = food_dx * food_dx + food_dy * food_dy
                if food_dist_sq < 40000 and food_dist_sq > 0:  # 200^2
                    food_dist = math.sqrt(food_dist_sq)
                    food_x = food_dx / food_dist
                    food_y = food_dy / food_dist
                    # Blend avoidance with food seeking
                    final_x = avoidance_x * 0.7 + food_x * 0.3
                    final_y = avoidance_y * 0.7 + food_y * 0.3
                    final_len = math.sqrt(final_x * final_x + final_y * final_y)
                    if final_len > 0:
                        return final_x / final_len * speed, final_y / final_len * speed

            return avoidance_x * speed, avoidance_y * speed

        # No fish nearby - focus on food
        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            direction = self._safe_normalize(nearest_food.pos - fish.pos)
            return (
                direction.x * self.parameters["food_priority"],
                direction.y * self.parameters["food_priority"],
            )

        return 0, 0


@dataclass
class PokerGambler(BehaviorAlgorithm):
    """Seeks poker aggressively when high energy."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng if rng is not None else random.Random()
        super().__init__(
            algorithm_id="poker_gambler",
            parameters={
                "high_energy_threshold": rng.uniform(0.6, 0.9),
                "challenge_speed": rng.uniform(1.0, 1.5),
                "risk_tolerance": rng.uniform(0.3, 0.8),
            },
        )
        self.rng = rng

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        import math
        fish_x, fish_y = fish.pos.x, fish.pos.y

        # Check for predators
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            dx = nearest_predator.pos.x - fish_x
            dy = nearest_predator.pos.y - fish_y
            dist_sq = dx * dx + dy * dy
            if dist_sq < 14400:  # 120^2
                dist = math.sqrt(dist_sq)
                if dist > 0:
                    return -dx / dist * 1.2, -dy / dist * 1.2
                return 0, 0

        energy_ratio = fish.energy / fish.max_energy

        # If energy is high, gamble!
        if energy_ratio > self.parameters["high_energy_threshold"]:
            # OPTIMIZATION: Use spatial query
            nearest_fish, _ = _find_nearest_fish_spatial(fish, 200)
            if nearest_fish is not None:
                direction = self._safe_normalize(nearest_fish.pos - fish.pos)
                speed = self.parameters["challenge_speed"]
                return direction.x * speed, direction.y * speed

        # If energy is medium, balance poker with food
        elif energy_ratio > 0.3:
            # 50/50 chance between seeking fish or food
            rng = getattr(self, "rng", None) or random
            if rng.random() < 0.5:
                # OPTIMIZATION: Use spatial query
                nearest_fish, _ = _find_nearest_fish_spatial(fish, 200)
                if nearest_fish is not None:
                    direction = self._safe_normalize(nearest_fish.pos - fish.pos)
                    return direction.x * 0.8, direction.y * 0.8

        # Low energy - focus on food
        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            direction = self._safe_normalize(nearest_food.pos - fish.pos)
            return direction.x, direction.y

        return 0, 0


@dataclass
class SelectivePoker(BehaviorAlgorithm):
    """Only engages in poker when conditions are favorable."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng if rng is not None else random.Random()
        super().__init__(
            algorithm_id="selective_poker",
            parameters={
                "min_energy_ratio": rng.uniform(0.4, 0.7),
                "max_energy_ratio": rng.uniform(0.7, 0.95),
                "challenge_speed": rng.uniform(0.6, 1.0),
                "selectivity": rng.uniform(0.5, 0.9),
            },
        )
        self.rng = rng

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        import math
        fish_x, fish_y = fish.pos.x, fish.pos.y

        # Check for predators
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            dx = nearest_predator.pos.x - fish_x
            dy = nearest_predator.pos.y - fish_y
            dist_sq = dx * dx + dy * dy
            if dist_sq < 14400:  # 120^2
                dist = math.sqrt(dist_sq)
                if dist > 0:
                    return -dx / dist * 1.2, -dy / dist * 1.2
                return 0, 0

        energy_ratio = fish.energy / fish.max_energy

        # Only seek poker in the "sweet spot" energy range
        if self.parameters["min_energy_ratio"] < energy_ratio < self.parameters["max_energy_ratio"]:
            # Be selective - only challenge sometimes
            rng = getattr(self, "rng", None) or random
            if rng.random() < self.parameters["selectivity"]:
                # OPTIMIZATION: Use spatial query with max distance 150
                nearest_fish, dist_sq = _find_nearest_fish_spatial(fish, 150)

                if nearest_fish is not None:
                    direction = self._safe_normalize(nearest_fish.pos - fish.pos)
                    speed = self.parameters["challenge_speed"]
                    return direction.x * speed, direction.y * speed

        # Default to food seeking
        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            direction = self._safe_normalize(nearest_food.pos - fish.pos)
            return direction.x * 0.9, direction.y * 0.9

        return 0, 0


@dataclass
class PokerOpportunist(BehaviorAlgorithm):
    """Balances food seeking with poker opportunities."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng if rng is not None else random.Random()
        super().__init__(
            algorithm_id="poker_opportunist",
            parameters={
                "poker_weight": rng.uniform(0.3, 0.7),
                "food_weight": rng.uniform(0.3, 0.7),
                "opportunity_radius": rng.uniform(80.0, 150.0),
            },
        )

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        import math
        fish_x, fish_y = fish.pos.x, fish.pos.y

        # Check for predators
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            dx = nearest_predator.pos.x - fish_x
            dy = nearest_predator.pos.y - fish_y
            dist_sq = dx * dx + dy * dy
            if dist_sq < 14400:  # 120^2
                dist = math.sqrt(dist_sq)
                if dist > 0:
                    return -dx / dist * 1.2, -dy / dist * 1.2
                return 0, 0

        # Look for both food and fish opportunities
        nearest_food = self._find_nearest_food(fish)

        # OPTIMIZATION: Use spatial query
        opportunity_radius = self.parameters["opportunity_radius"]
        nearest_fish, _ = _find_nearest_fish_spatial(fish, opportunity_radius)

        # Use raw floats for vectors to avoid allocations
        food_x, food_y = 0.0, 0.0
        poker_x, poker_y = 0.0, 0.0

        # Calculate food attraction
        if nearest_food:
            dx = nearest_food.pos.x - fish_x
            dy = nearest_food.pos.y - fish_y
            dist_sq = dx * dx + dy * dy
            if dist_sq > 0:
                dist = math.sqrt(dist_sq)
                food_x = dx / dist
                food_y = dy / dist

        # Calculate poker attraction (nearest fish)
        if nearest_fish is not None:
            dx = nearest_fish.pos.x - fish_x
            dy = nearest_fish.pos.y - fish_y
            dist_sq = dx * dx + dy * dy
            if dist_sq > 0:
                dist = math.sqrt(dist_sq)
                poker_x = dx / dist
                poker_y = dy / dist

        # Blend the two behaviors based on weights and energy
        energy_ratio = fish.energy / fish.max_energy

        # Adjust weights based on energy
        if energy_ratio < 0.3:
            # Low energy - prioritize food
            food_weight = 0.8
            poker_weight = 0.2
        else:
            food_weight = self.parameters["food_weight"]
            poker_weight = self.parameters["poker_weight"]

        # Combine vectors
        final_x = food_x * food_weight + poker_x * poker_weight
        final_y = food_y * food_weight + poker_y * poker_weight
        final_len = math.sqrt(final_x * final_x + final_y * final_y)
        if final_len > 0:
            return final_x / final_len, final_y / final_len

        return 0, 0


@dataclass
class PokerStrategist(BehaviorAlgorithm):
    """Uses opponent modeling and strategic positioning for poker."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng if rng is not None else random.Random()
        super().__init__(
            algorithm_id="poker_strategist",
            parameters={
                "aggression_variance": rng.uniform(0.1, 0.4),
                "position_awareness": rng.uniform(0.5, 1.0),
                "opponent_tracking": rng.uniform(0.3, 0.8),
                "min_energy_ratio": rng.uniform(0.3, 0.6),
                "challenge_speed": rng.uniform(0.7, 1.2),
            },
        )
        # Track recent poker encounters for opponent modeling
        self.recent_encounters = []
        self.max_memory = 5

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        import math
        fish_x, fish_y = fish.pos.x, fish.pos.y

        # Check for predators first
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            dx = nearest_predator.pos.x - fish_x
            dy = nearest_predator.pos.y - fish_y
            dist_sq = dx * dx + dy * dy
            if dist_sq < 14400:  # 120^2
                dist = math.sqrt(dist_sq)
                if dist > 0:
                    return -dx / dist * 1.2, -dy / dist * 1.2
                return 0, 0

        energy_ratio = fish.energy / fish.max_energy

        # Only seek poker if energy is above minimum
        if energy_ratio < self.parameters["min_energy_ratio"]:
            # Low energy - seek food
            nearest_food = self._find_nearest_food(fish)
            if nearest_food:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                return direction.x * 0.9, direction.y * 0.9
            return 0, 0

        # OPTIMIZATION: Use spatial query instead of get_agents_of_type
        other_fish = _get_nearby_fish_spatial(fish, 200)

        if not other_fish:
            # No opponents - seek food
            nearest_food = self._find_nearest_food(fish)
            if nearest_food:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                return direction.x * 0.7, direction.y * 0.7
            return 0, 0

        # Strategic target selection based on position and energy
        best_target = None
        best_score = -float("inf")

        for target in other_fish:
            # Calculate distance using raw math
            dx = target.pos.x - fish_x
            dy = target.pos.y - fish_y
            dist_sq = dx * dx + dy * dy

            if dist_sq > 40000:  # 200^2 - Too far
                continue

            distance = math.sqrt(dist_sq)

            # Calculate strategic score
            score = 0.0

            # Prefer closer targets (but not too close)
            optimal_distance = 100
            distance_score = 1.0 - abs(distance - optimal_distance) / 150.0
            score += distance_score * self.parameters["position_awareness"]

            # Prefer targets with similar or lower energy
            if hasattr(target, "energy") and target.energy is not None:
                energy_diff = fish.energy - target.energy
                if energy_diff > 0:  # We have more energy
                    score += 0.5 * self.parameters["opponent_tracking"]
                else:  # They have more energy - risky
                    score -= 0.3 * self.parameters["opponent_tracking"]

            # Add some randomness based on aggression variance
            rng = getattr(self, "rng", None) or random
            score += rng.uniform(
                -self.parameters["aggression_variance"], self.parameters["aggression_variance"]
            )

            if score > best_score:
                best_score = score
                best_target = target

        # If we found a good target, pursue it
        if best_target and best_score > 0:
            direction = self._safe_normalize(best_target.pos - fish.pos)
            speed = self.parameters["challenge_speed"]
            return direction.x * speed, direction.y * speed

        # No good targets - balance food and exploration
        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            direction = self._safe_normalize(nearest_food.pos - fish.pos)
            return direction.x * 0.8, direction.y * 0.8

        rng = getattr(self, "rng", None) or random
        return rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3)


@dataclass
class PokerBluffer(BehaviorAlgorithm):
    """Varies behavior unpredictably to confuse opponents."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng if rng is not None else random.Random()
        super().__init__(
            algorithm_id="poker_bluffer",
            parameters={
                "bluff_frequency": rng.uniform(0.2, 0.6),
                "aggression_swing": rng.uniform(0.4, 1.0),
                "unpredictability": rng.uniform(0.3, 0.7),
                "min_energy_to_bluff": rng.uniform(20.0, 40.0),
            },
        )
        # Track behavior state
        self.current_mode = "normal"  # 'normal', 'aggressive', 'passive'
        self.mode_timer = 0
        self.mode_duration = rng.randint(50, 150)
        self.rng = rng

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        import math
        fish_x, fish_y = fish.pos.x, fish.pos.y

        # Check for predators
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            dx = nearest_predator.pos.x - fish_x
            dy = nearest_predator.pos.y - fish_y
            dist_sq = dx * dx + dy * dy
            if dist_sq < 14400:  # 120^2
                dist = math.sqrt(dist_sq)
                if dist > 0:
                    return -dx / dist * 1.2, -dy / dist * 1.2
                return 0, 0

        # Update behavior mode timer
        self.mode_timer += 1
        if self.mode_timer >= self.mode_duration:
            # Switch modes randomly
            rng = getattr(self, "rng", None) or random
            if rng.random() < self.parameters["bluff_frequency"]:
                modes = ["normal", "aggressive", "passive"]
                self.current_mode = rng.choice(modes)
                self.mode_duration = rng.randint(30, 100)
                self.mode_timer = 0

        # Don't bluff if energy is too low
        if fish.energy < self.parameters["min_energy_to_bluff"]:
            nearest_food = self._find_nearest_food(fish)
            if nearest_food:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                return direction.x, direction.y
            return 0, 0

        # OPTIMIZATION: Use spatial query instead of get_agents_of_type
        other_fish = _get_nearby_fish_spatial(fish, 150)

        # Behavior based on current mode
        if self.current_mode == "aggressive":
            # Aggressively seek poker
            nearest_fish, _ = _find_nearest_fish_spatial(fish, 200)
            if nearest_fish is not None:
                direction = self._safe_normalize(nearest_fish.pos - fish.pos)
                speed = 1.0 + self.parameters["aggression_swing"]
                return direction.x * speed, direction.y * speed

        elif self.current_mode == "passive":
            # Avoid fish, focus on food
            nearest_food = self._find_nearest_food(fish)
            avoidance_x = 0.0
            avoidance_y = 0.0

            # Calculate avoidance from nearby fish
            for other in other_fish:
                dx = other.pos.x - fish_x
                dy = other.pos.y - fish_y
                dist_sq = dx * dx + dy * dy
                if dist_sq < 10000 and dist_sq > 0:  # 100^2
                    dist = math.sqrt(dist_sq)
                    # Direction away from other
                    avoidance_x -= dx / dist
                    avoidance_y -= dy / dist

            # Blend avoidance with food seeking
            avoid_len = math.sqrt(avoidance_x * avoidance_x + avoidance_y * avoidance_y)
            if nearest_food and avoid_len > 0:
                avoidance_x /= avoid_len
                avoidance_y /= avoid_len
                food_dx = nearest_food.pos.x - fish_x
                food_dy = nearest_food.pos.y - fish_y
                food_dist = math.sqrt(food_dx * food_dx + food_dy * food_dy)
                if food_dist > 0:
                    food_x = food_dx / food_dist
                    food_y = food_dy / food_dist
                    final_x = avoidance_x * 0.6 + food_x * 0.4
                    final_y = avoidance_y * 0.6 + food_y * 0.4
                    final_len = math.sqrt(final_x * final_x + final_y * final_y)
                    if final_len > 0:
                        return final_x / final_len * 0.8, final_y / final_len * 0.8
            elif nearest_food:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                return direction.x * 0.7, direction.y * 0.7

        else:  # normal mode
            # Balanced approach with unpredictability
            rng = getattr(self, "rng", None) or random
            if other_fish and rng.random() < 0.6:
                nearest_fish, _ = _find_nearest_fish_spatial(fish, 150)
                if nearest_fish is not None:
                    direction = self._safe_normalize(nearest_fish.pos - fish.pos)
                    # Add unpredictable speed variation
                    speed = 0.8 + rng.uniform(0, self.parameters["unpredictability"])
                    return direction.x * speed, direction.y * speed

            # Default to food seeking
            nearest_food = self._find_nearest_food(fish)
            if nearest_food:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                return direction.x * 0.8, direction.y * 0.8

        rng = getattr(self, "rng", None) or random
        return rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4)


@dataclass
class PokerConservative(BehaviorAlgorithm):
    """Risk-averse poker player that only engages in highly favorable conditions."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng if rng is not None else random.Random()
        super().__init__(
            algorithm_id="poker_conservative",
            parameters={
                "min_energy_ratio": rng.uniform(0.6, 0.85),
                "max_risk_tolerance": rng.uniform(0.1, 0.3),
                "safety_distance": rng.uniform(100.0, 180.0),
                "challenge_speed": rng.uniform(0.5, 0.9),
                "energy_advantage_required": rng.uniform(10.0, 30.0),
            },
        )

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        import math
        fish_x, fish_y = fish.pos.x, fish.pos.y

        # Always flee from predators
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            dx = nearest_predator.pos.x - fish_x
            dy = nearest_predator.pos.y - fish_y
            dist_sq = dx * dx + dy * dy
            if dist_sq < 22500:  # 150^2
                dist = math.sqrt(dist_sq)
                if dist > 0:
                    return -dx / dist * 1.3, -dy / dist * 1.3
                return 0, 0

        energy_ratio = fish.energy / fish.max_energy

        # Very conservative - only play poker when energy is high
        if energy_ratio < self.parameters["min_energy_ratio"]:
            # Focus entirely on food
            nearest_food = self._find_nearest_food(fish)
            if nearest_food:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                return direction.x, direction.y
            return 0, 0

        # OPTIMIZATION: Use spatial query with safety distance
        safety_distance = self.parameters["safety_distance"]
        other_fish = _get_nearby_fish_spatial(fish, safety_distance)

        best_target = None
        best_advantage = 0.0
        energy_advantage_required = self.parameters["energy_advantage_required"]

        for other in other_fish:
            # Check if we have energy advantage
            if hasattr(other, "energy") and other.energy is not None:
                energy_advantage = fish.energy - other.energy

                # Only challenge if we have significant energy advantage
                if energy_advantage > energy_advantage_required:
                    if energy_advantage > best_advantage:
                        best_advantage = energy_advantage
                        best_target = other

        # Only engage if we found a favorable matchup (use environment RNG for determinism)
        rng = getattr(fish.environment, "rng", random)
        if best_target and rng.random() > self.parameters["max_risk_tolerance"]:
            direction = self._safe_normalize(best_target.pos - fish.pos)
            speed = self.parameters["challenge_speed"]
            return direction.x * speed, direction.y * speed

        # Default to safe food seeking
        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            # Check if any fish are too close while seeking food (use spatial query)
            close_fish = _get_nearby_fish_spatial(fish, 80)
            if close_fish:
                # Avoid close fish while seeking food - use raw floats
                avoidance_x = 0.0
                avoidance_y = 0.0
                for f in close_fish:
                    dx = f.pos.x - fish_x
                    dy = f.pos.y - fish_y
                    dist_sq = dx * dx + dy * dy
                    if dist_sq > 0:
                        dist = math.sqrt(dist_sq)
                        avoidance_x -= dx / dist
                        avoidance_y -= dy / dist

                food_dx = nearest_food.pos.x - fish_x
                food_dy = nearest_food.pos.y - fish_y
                food_dist = math.sqrt(food_dx * food_dx + food_dy * food_dy)
                if food_dist > 0:
                    food_x = food_dx / food_dist
                    food_y = food_dy / food_dist

                    avoid_len = math.sqrt(avoidance_x * avoidance_x + avoidance_y * avoidance_y)
                    if avoid_len > 0:
                        avoidance_x /= avoid_len
                        avoidance_y /= avoid_len

                    final_x = avoidance_x * 0.5 + food_x * 0.5
                    final_y = avoidance_y * 0.5 + food_y * 0.5
                    final_len = math.sqrt(final_x * final_x + final_y * final_y)
                    if final_len > 0:
                        return final_x / final_len * 0.8, final_y / final_len * 0.8
            else:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                return direction.x * 0.9, direction.y * 0.9

        return 0, 0
