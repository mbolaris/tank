import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from core.algorithms.base import BehaviorHelpersMixin
from core.util import coerce_enum

from .actions import BehaviorActionsMixin
from .definitions import (
    SUB_BEHAVIOR_PARAMS,
    FoodApproach,
    PokerEngagement,
    SocialMode,
    ThreatResponse,
    _random_params,
)

if TYPE_CHECKING:
    from core.entities import Fish


@dataclass
class ComposableBehavior(BehaviorHelpersMixin, BehaviorActionsMixin):
    """A behavior composed of multiple sub-behavior selections plus parameters.

    This replaces the monolithic BehaviorAlgorithm with a composable structure
    that allows evolution to mix and match sub-behaviors while tuning parameters.

    Attributes:
        threat_response: Which threat response sub-behavior to use
        food_approach: Which food approach sub-behavior to use
        social_mode: Which social interaction mode to use
        poker_engagement: Which poker engagement style to use
        parameters: Continuous parameters that tune sub-behavior execution

    NOTE: EnergyStyle was removed - speed modulation now uses a simple formula.
    """

    threat_response: ThreatResponse = ThreatResponse.PANIC_FLEE
    food_approach: FoodApproach = FoodApproach.DIRECT_PURSUIT
    social_mode: SocialMode = SocialMode.SOLO
    poker_engagement: PokerEngagement = PokerEngagement.PASSIVE
    parameters: Dict[str, float] = field(default_factory=dict)

    # Internal state for stateful behaviors (food approach patterns)
    _circle_angle: float = field(default=0.0, repr=False)
    _zigzag_phase: float = field(default=0.0, repr=False)
    _patrol_angle: float = field(default=0.0, repr=False)

    @property
    def behavior_id(self) -> str:
        """Get a unique string identifier for this behavior configuration."""
        return "-".join(
            [
                self.threat_response.name,
                self.food_approach.name,
                self.social_mode.name,
                self.poker_engagement.name,
            ]
        ).lower()

    @property
    def short_description(self) -> str:
        """Get a human-readable short description of this behavior."""
        return f"{self.food_approach.name.replace('_', ' ').title()}"

    def __post_init__(self):
        """Initialize default parameters if not provided."""
        if not self.parameters:
            self.parameters = {
                key: (low + high) / 2 for key, (low, high) in SUB_BEHAVIOR_PARAMS.items()
            }

    @classmethod
    def create_random(cls, rng: Optional["random.Random"] = None) -> "ComposableBehavior":
        """Create a random composable behavior."""
        from core.util.rng import require_rng_param

        rng = require_rng_param(rng, "ComposableBehavior.create_random")
        return cls(
            threat_response=coerce_enum(ThreatResponse, rng.randint(0, len(ThreatResponse) - 1)),
            food_approach=coerce_enum(FoodApproach, rng.randint(0, len(FoodApproach) - 1)),
            social_mode=coerce_enum(SocialMode, rng.randint(0, len(SocialMode) - 1)),
            poker_engagement=coerce_enum(PokerEngagement, rng.randint(0, len(PokerEngagement) - 1)),
            parameters=_random_params(rng),
        )

    # -------------------------------------------------------------------------
    # Main Execute Method
    # -------------------------------------------------------------------------

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        """Execute the composed behavior and return desired velocity.

        The execution priority is:
        1. Threat response (if predator detected)
        2. Food pursuit (if food detected) - COMMITS FULLY to chase
        3. Poker engagement (if applicable)
        4. Social behavior / exploration

        Design Decision:
            When food is detected, fish commit fully to the chase without
            blending with social behaviors or applying speed penalties.
            This makes `pursuit_speed` the single evolvable trait for
            food-seeking effectiveness, improving evolutionary selection.

        Returns:
            Tuple of (velocity_x, velocity_y)
        """
        # Get energy state
        is_critical, is_low, energy_ratio = self._get_energy_state(fish)

        # 1. THREAT RESPONSE - Check for predators first
        threat_vx, threat_vy, threat_active = self._execute_threat_response(fish)
        if threat_active:
            # Fleeing gets energy modifier - survival is paramount
            speed_mod = self._get_energy_speed_modifier(fish, is_critical, is_low)
            return threat_vx * speed_mod, threat_vy * speed_mod

        # 2. FOOD PURSUIT - Commit fully when food is detected
        # No blending, no urgency penalty - pursuit_speed is the single control
        food_vx, food_vy = self._execute_food_approach(fish)
        if food_vx != 0 or food_vy != 0:
            # Food found - commit to the chase!
            # Critical/low energy fish get a desperation boost
            # Increased from 1.3/1.1 to 1.5/1.25 to help starving fish catch food
            if is_critical:
                return food_vx * 1.5, food_vy * 1.5
            elif is_low:
                return food_vx * 1.25, food_vy * 1.25
            return food_vx, food_vy

        # 3. POKER ENGAGEMENT - Only when no food detected
        poker_priority = self.parameters.get("poker_priority", 0.3)
        poker_vx, poker_vy, poker_active = self._execute_poker_engagement(fish, energy_ratio)
        if poker_active and poker_priority > fish.environment.rng.random():
            return poker_vx, poker_vy

        # 4. SOCIAL/EXPLORATION - When nothing else to do
        social_vx, social_vy = self._execute_social_mode(fish)
        if social_vx != 0 or social_vy != 0:
            # Apply energy style modulation only during exploration
            speed_mod = self._get_energy_speed_modifier(fish, is_critical, is_low)
            return social_vx * speed_mod, social_vy * speed_mod

        # Default exploration
        vx, vy = self._default_exploration(fish)
        speed_mod = self._get_energy_speed_modifier(fish, is_critical, is_low)
        return vx * speed_mod, vy * speed_mod

    # -------------------------------------------------------------------------
    # Mutation Methods
    # -------------------------------------------------------------------------

    def mutate(
        self,
        mutation_rate: float = 0.15,  # Increased from 0.1
        mutation_strength: float = 0.20,  # Increased from 0.15
        sub_behavior_switch_rate: float = 0.10,  # Increased from 0.05
        rng: Optional["random.Random"] = None,
    ) -> None:
        """Mutate the composable behavior."""
        from core.util.rng import require_rng_param

        rng = require_rng_param(rng, "ComposableBehavior.mutate")

        # Mutate sub-behavior selections (discrete)
        if rng.random() < sub_behavior_switch_rate:
            self.threat_response = coerce_enum(
                ThreatResponse, rng.randint(0, len(ThreatResponse) - 1)
            )
        if rng.random() < sub_behavior_switch_rate:
            self.food_approach = coerce_enum(FoodApproach, rng.randint(0, len(FoodApproach) - 1))
        if rng.random() < sub_behavior_switch_rate:
            self.social_mode = coerce_enum(SocialMode, rng.randint(0, len(SocialMode) - 1))
        if rng.random() < sub_behavior_switch_rate:
            self.poker_engagement = coerce_enum(
                PokerEngagement, rng.randint(0, len(PokerEngagement) - 1)
            )

        # Mutate continuous parameters (sorted for determinism)
        for key, value in sorted(self.parameters.items()):
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
            "social_mode": int(self.social_mode),
            "poker_engagement": int(self.poker_engagement),
            "parameters": dict(self.parameters),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComposableBehavior":
        """Deserialize from dictionary.

        NOTE: energy_style is ignored if present in data (removed from behavior system).
        """
        return cls(
            threat_response=coerce_enum(ThreatResponse, data.get("threat_response", 0)),
            food_approach=coerce_enum(FoodApproach, data.get("food_approach", 0)),
            social_mode=coerce_enum(SocialMode, data.get("social_mode", 0)),
            poker_engagement=coerce_enum(PokerEngagement, data.get("poker_engagement", 1)),
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
        mutation_rate: float = 0.15,  # Increased from 0.1
        mutation_strength: float = 0.20,  # Increased from 0.15
        sub_behavior_switch_rate: float = 0.08,  # Increased from 0.03
        rng: Optional["random.Random"] = None,
    ) -> "ComposableBehavior":
        """Create offspring by crossing over two parent behaviors."""
        from core.util.rng import require_rng_param

        rng = require_rng_param(rng, "ComposableBehavior.from_parents")

        # Mendelian inheritance for discrete sub-behaviors
        threat_response = (
            parent1.threat_response if rng.random() < weight1 else parent2.threat_response
        )
        food_approach = parent1.food_approach if rng.random() < weight1 else parent2.food_approach
        social_mode = parent1.social_mode if rng.random() < weight1 else parent2.social_mode
        poker_engagement = (
            parent1.poker_engagement if rng.random() < weight1 else parent2.poker_engagement
        )

        # Blend parameters
        all_keys = sorted(set(parent1.parameters.keys()) | set(parent2.parameters.keys()))
        blended_params = {}
        for key in all_keys:
            val1 = parent1.parameters.get(key)
            val2 = parent2.parameters.get(key)
            if val1 is not None and val2 is not None:
                # Blend
                blended = val1 * weight1 + val2 * (1 - weight1)
            elif val1 is not None:
                blended = val1
            else:
                assert val2 is not None
                blended = val2
            blended_params[key] = blended

        # Create child
        child = cls(
            threat_response=threat_response,
            food_approach=food_approach,
            social_mode=social_mode,
            poker_engagement=poker_engagement,
            parameters=blended_params,
        )

        # Mutate
        child.mutate(
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            sub_behavior_switch_rate=sub_behavior_switch_rate,
            rng=rng,
        )

        return child
