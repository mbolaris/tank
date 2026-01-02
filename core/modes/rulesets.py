"""Mode-specific rule sets for multi-agent simulations.

This module defines the ModeRuleSet abstraction which encapsulates
mode-specific game rules, energy models, and scoring mechanics.
This allows "mode = rules + visuals" to be explicit and configurable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class EnergyModel:
    """Configuration for energy/stamina mechanics.

    This defines how energy is consumed, gained, and managed in a mode.
    Frozen to ensure immutability after creation.
    """

    # Base costs
    existence_cost: float = 0.05
    """Energy cost per frame just for existing."""

    movement_cost_multiplier: float = 1.0
    """Multiplier for movement energy costs."""

    turn_cost_base: float = 0.02
    """Base energy cost for direction changes."""

    turn_cost_size_multiplier: float = 1.5
    """Exponent for size scaling of turn costs."""

    # Energy limits
    initial_energy_ratio: float = 0.5
    """Starting energy as ratio of max energy."""

    starvation_threshold_ratio: float = 0.15
    """Energy ratio below which agent is starving."""

    critical_threshold_ratio: float = 0.05
    """Energy ratio below which agent is in critical state."""

    # Overflow handling
    overflow_bank_enabled: bool = True
    """Whether to bank overflow energy for reproduction."""

    overflow_bank_multiplier: float = 1.0
    """Max bank size as multiplier of max energy."""


@dataclass(frozen=True)
class ScoringModel:
    """Configuration for scoring and fitness mechanics.

    This defines what contributes to agent fitness/success in a mode.
    """

    primary_metric: str = "survival_time"
    """Main metric for fitness evaluation."""

    secondary_metrics: tuple = ("reproduction_count", "food_consumed")
    """Additional metrics tracked for fitness."""

    # Reward weights (for modes that use shaped rewards)
    survival_weight: float = 1.0
    reproduction_weight: float = 2.0
    food_weight: float = 0.1

    # Mode-specific reward components
    extra_rewards: Dict[str, float] = field(default_factory=dict)
    """Additional reward components (e.g., goal_reward for soccer)."""


@dataclass(frozen=True)
class ActionSpace:
    """Configuration for available agent actions in a mode."""

    # Movement
    continuous_movement: bool = True
    """Whether movement is continuous or discrete."""

    max_speed: float = 5.0
    """Maximum movement speed."""

    acceleration: float = 1.0
    """Movement acceleration."""

    # Actions
    allowed_actions: tuple = ("move", "eat")
    """List of allowed action types."""

    # Mode-specific
    has_kick: bool = False
    """Whether kick action is available (soccer)."""

    has_poker: bool = False
    """Whether poker skill game is available (tank)."""


class ModeRuleSet(ABC):
    """Abstract base for mode-specific game rules.

    A ModeRuleSet encapsulates all the rules that make a mode unique:
    - Energy/stamina mechanics
    - Scoring/fitness evaluation
    - Available actions
    - Mode-specific behaviors

    This allows different modes to share underlying simulation code
    while having distinct gameplay characteristics.
    """

    @property
    @abstractmethod
    def mode_id(self) -> str:
        """Unique identifier for this mode (e.g., 'tank', 'petri', 'soccer')."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for UI display."""
        ...

    @property
    @abstractmethod
    def energy_model(self) -> EnergyModel:
        """Energy/stamina configuration for this mode."""
        ...

    @property
    @abstractmethod
    def scoring_model(self) -> ScoringModel:
        """Scoring/fitness configuration for this mode."""
        ...

    @property
    @abstractmethod
    def action_space(self) -> ActionSpace:
        """Available actions configuration for this mode."""
        ...

    def get_allowed_actions(self) -> List[str]:
        """Get list of allowed action types.

        Returns:
            List of action type strings
        """
        return list(self.action_space.allowed_actions)

    def validate_action(self, action: Dict[str, Any]) -> bool:
        """Validate an action against this mode's rules.

        Args:
            action: Action dictionary to validate

        Returns:
            True if action is valid for this mode
        """
        action_type = action.get("type", "move")
        return action_type in self.action_space.allowed_actions


class TankRuleSet(ModeRuleSet):
    """Rules for Tank (fish ecosystem) mode.

    Tank mode features:
    - Autonomous agent behavior (no external actions required)
    - Energy-based survival with food consumption
    - Reproduction through energy overflow or poker wins
    - Poker skill game available
    """

    @property
    def mode_id(self) -> str:
        return "tank"

    @property
    def display_name(self) -> str:
        return "Fish Tank"

    @property
    def energy_model(self) -> EnergyModel:
        return EnergyModel(
            existence_cost=0.05,
            movement_cost_multiplier=1.0,
            turn_cost_base=0.02,
            turn_cost_size_multiplier=1.5,
            initial_energy_ratio=0.5,
            starvation_threshold_ratio=0.15,
            critical_threshold_ratio=0.05,
            overflow_bank_enabled=True,
            overflow_bank_multiplier=1.0,
        )

    @property
    def scoring_model(self) -> ScoringModel:
        return ScoringModel(
            primary_metric="survival_time",
            secondary_metrics=("reproduction_count", "food_consumed", "poker_winnings"),
            survival_weight=1.0,
            reproduction_weight=2.0,
            food_weight=0.1,
        )

    @property
    def action_space(self) -> ActionSpace:
        return ActionSpace(
            continuous_movement=True,
            max_speed=5.0,
            acceleration=1.0,
            allowed_actions=("move", "eat", "reproduce", "poker"),
            has_kick=False,
            has_poker=True,
        )


class PetriRuleSet(ModeRuleSet):
    """Rules for Petri dish mode.

    Petri mode is essentially Tank mode with different visuals.
    Uses the same rules with minor cosmetic differences.
    """

    @property
    def mode_id(self) -> str:
        return "petri"

    @property
    def display_name(self) -> str:
        return "Petri Dish"

    @property
    def energy_model(self) -> EnergyModel:
        # Same as Tank for now
        return EnergyModel(
            existence_cost=0.05,
            movement_cost_multiplier=1.0,
            overflow_bank_enabled=True,
        )

    @property
    def scoring_model(self) -> ScoringModel:
        # Same as Tank
        return ScoringModel(
            primary_metric="survival_time",
            secondary_metrics=("reproduction_count", "food_consumed"),
        )

    @property
    def action_space(self) -> ActionSpace:
        # Same as Tank but no poker
        return ActionSpace(
            continuous_movement=True,
            allowed_actions=("move", "eat", "reproduce"),
            has_poker=False,
        )


class SoccerRuleSet(ModeRuleSet):
    """Rules for Soccer training mode.

    Soccer mode features:
    - Action-based agents (requires external control)
    - Stamina-based energy (recovers over time)
    - Goal-based scoring with shaped rewards
    - Kick action available
    """

    @property
    def mode_id(self) -> str:
        return "soccer"

    @property
    def display_name(self) -> str:
        return "Soccer Pitch"

    @property
    def energy_model(self) -> EnergyModel:
        return EnergyModel(
            existence_cost=0.0,  # Stamina recovers
            movement_cost_multiplier=0.5,
            turn_cost_base=0.0,  # No turn penalty in soccer
            initial_energy_ratio=1.0,  # Start at full stamina
            overflow_bank_enabled=False,  # No reproduction in soccer
        )

    @property
    def scoring_model(self) -> ScoringModel:
        return ScoringModel(
            primary_metric="goals_scored",
            secondary_metrics=("shots_on_target", "passes_completed", "possession_time"),
            survival_weight=0.0,
            reproduction_weight=0.0,
            food_weight=0.0,
            extra_rewards={
                "goal": 10.0,
                "shot": 1.0,
                "pass": 0.5,
                "possession": 0.1,
                "spacing": 0.05,
            },
        )

    @property
    def action_space(self) -> ActionSpace:
        return ActionSpace(
            continuous_movement=True,
            max_speed=8.0,  # Soccer players move faster
            acceleration=2.0,
            allowed_actions=("move", "dash", "turn", "kick"),
            has_kick=True,
            has_poker=False,
        )


class SoccerTrainingRuleSet(SoccerRuleSet):
    """Rules for Soccer training mode (inherits from Soccer).

    Same rules as Soccer with potential training-specific adjustments.
    """

    @property
    def mode_id(self) -> str:
        return "soccer_training"

    @property
    def display_name(self) -> str:
        return "Soccer Training"


# Registry of built-in rulesets
_RULESETS: Dict[str, ModeRuleSet] = {
    "tank": TankRuleSet(),
    "petri": PetriRuleSet(),
    "soccer": SoccerRuleSet(),
    "soccer_training": SoccerTrainingRuleSet(),
}


def get_ruleset(mode_id: str) -> Optional[ModeRuleSet]:
    """Get a ruleset by mode ID.

    Args:
        mode_id: Mode identifier

    Returns:
        ModeRuleSet or None if not found
    """
    return _RULESETS.get(mode_id)


def register_ruleset(ruleset: ModeRuleSet) -> None:
    """Register a custom ruleset.

    Args:
        ruleset: The ruleset to register
    """
    _RULESETS[ruleset.mode_id] = ruleset


def list_rulesets() -> List[str]:
    """List all registered ruleset mode IDs.

    Returns:
        List of mode ID strings
    """
    return list(_RULESETS.keys())
