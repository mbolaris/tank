import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from core.algorithms.base import BehaviorHelpersMixin
from .actions import BehaviorActionsMixin
from .definitions import (
    ThreatResponse,
    FoodApproach,
    EnergyStyle,
    SocialMode,
    PokerEngagement,
    SUB_BEHAVIOR_PARAMS,
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

    @property
    def behavior_id(self) -> str:
        """Get a unique string identifier for this behavior configuration."""
        return "-".join([
            self.threat_response.name,
            self.food_approach.name,
            self.energy_style.name,
            self.social_mode.name,
            self.poker_engagement.name,
        ]).lower()

    @property
    def short_description(self) -> str:
        """Get a human-readable short description of this behavior."""
        return (
            f"{self.food_approach.name.replace('_', ' ').title()} "
            f"({self.energy_style.name.lower()})"
        )

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
        rng = getattr(fish.environment, "rng", random)
        if poker_active and poker_priority > rng.random():
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
    # Mutation Methods
    # -------------------------------------------------------------------------

    def mutate(
        self,
        mutation_rate: float = 0.1,
        mutation_strength: float = 0.15,
        sub_behavior_switch_rate: float = 0.05,
        rng: Optional["random.Random"] = None,
    ) -> None:
        """Mutate the composable behavior."""
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
        """Create offspring by crossing over two parent behaviors."""
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
        all_keys = sorted(set(parent1.parameters.keys()) | set(parent2.parameters.keys()))
        blended_params = {}
        for key in all_keys:
            val1 = parent1.parameters.get(key)
            val2 = parent2.parameters.get(key)
            if val1 is not None and val2 is not None:
                # Blend
                blended = val1 * weight1 + val2 * (1 - weight1)
            else:
                # Inherit from whoever has it
                blended = val1 if val1 is not None else val2
            blended_params[key] = blended

        # Create child
        child = cls(
            threat_response=threat_response,
            food_approach=food_approach,
            energy_style=energy_style,
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
