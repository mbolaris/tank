"""Tests for ModeRuleSet abstraction.

Tests the ruleset definitions, energy models, scoring models,
and action spaces for different simulation modes.
"""

from __future__ import annotations

import dataclasses

import pytest

from core.modes.rulesets import (
    ActionSpace,
    EnergyModel,
    PetriRuleSet,
    ScoringModel,
    SoccerRuleSet,
    TankRuleSet,
    get_ruleset,
    list_rulesets,
    register_ruleset,
)


class TestEnergyModel:
    """Tests for EnergyModel dataclass."""

    def test_default_values(self):
        """Should have sensible defaults."""
        model = EnergyModel()
        assert model.existence_cost == 0.05
        assert model.movement_cost_multiplier == 1.0
        assert model.overflow_bank_enabled is True

    def test_immutable(self):
        """Should be frozen/immutable."""
        model = EnergyModel()
        with pytest.raises(dataclasses.FrozenInstanceError):
            model.existence_cost = 0.1


class TestScoringModel:
    """Tests for ScoringModel dataclass."""

    def test_default_values(self):
        """Should have sensible defaults."""
        model = ScoringModel()
        assert model.primary_metric == "survival_time"
        assert "reproduction_count" in model.secondary_metrics

    def test_extra_rewards_default_empty(self):
        """Extra rewards should default to empty dict."""
        model = ScoringModel()
        assert model.extra_rewards == {}


class TestActionSpace:
    """Tests for ActionSpace dataclass."""

    def test_default_values(self):
        """Should have sensible defaults."""
        space = ActionSpace()
        assert space.continuous_movement is True
        assert "move" in space.allowed_actions
        assert space.has_kick is False
        assert space.has_poker is False


class TestTankRuleSet:
    """Tests for TankRuleSet."""

    def test_mode_id(self):
        """Should have correct mode ID."""
        ruleset = TankRuleSet()
        assert ruleset.mode_id == "tank"

    def test_display_name(self):
        """Should have human-readable name."""
        ruleset = TankRuleSet()
        assert ruleset.display_name == "Tank"

    def test_has_poker(self):
        """Tank mode should have poker enabled."""
        ruleset = TankRuleSet()
        assert ruleset.action_space.has_poker is True

    def test_has_reproduction(self):
        """Tank mode should allow reproduction."""
        ruleset = TankRuleSet()
        assert "reproduce" in ruleset.get_allowed_actions()

    def test_overflow_bank_enabled(self):
        """Tank mode should bank overflow energy."""
        ruleset = TankRuleSet()
        assert ruleset.energy_model.overflow_bank_enabled is True

    def test_tracks_poker_winnings(self):
        """Tank mode should track poker winnings."""
        ruleset = TankRuleSet()
        assert "poker_winnings" in ruleset.scoring_model.secondary_metrics


class TestPetriRuleSet:
    """Tests for PetriRuleSet."""

    def test_mode_id(self):
        """Should have correct mode ID."""
        ruleset = PetriRuleSet()
        assert ruleset.mode_id == "petri"

    def test_no_poker(self):
        """Petri mode should not have poker."""
        ruleset = PetriRuleSet()
        assert ruleset.action_space.has_poker is False

    def test_similar_to_tank(self):
        """Petri mode should use similar energy model to Tank."""
        tank = TankRuleSet()
        petri = PetriRuleSet()
        assert tank.energy_model.existence_cost == petri.energy_model.existence_cost


class TestSoccerRuleSet:
    """Tests for SoccerRuleSet."""

    def test_mode_id(self):
        """Should have correct mode ID."""
        ruleset = SoccerRuleSet()
        assert ruleset.mode_id == "soccer"

    def test_display_name(self):
        """Should have human-readable name."""
        ruleset = SoccerRuleSet()
        assert ruleset.display_name == "Soccer Pitch"

    def test_has_kick(self):
        """Soccer mode should have kick action."""
        ruleset = SoccerRuleSet()
        assert ruleset.action_space.has_kick is True

    def test_no_poker(self):
        """Soccer mode should not have poker."""
        ruleset = SoccerRuleSet()
        assert ruleset.action_space.has_poker is False

    def test_goal_based_scoring(self):
        """Soccer mode should track goals as primary metric."""
        ruleset = SoccerRuleSet()
        assert ruleset.scoring_model.primary_metric == "goals_scored"

    def test_no_overflow_bank(self):
        """Soccer mode should not bank overflow (no reproduction)."""
        ruleset = SoccerRuleSet()
        assert ruleset.energy_model.overflow_bank_enabled is False

    def test_has_shaped_rewards(self):
        """Soccer mode should have shaped reward components."""
        ruleset = SoccerRuleSet()
        assert "goal" in ruleset.scoring_model.extra_rewards
        assert ruleset.scoring_model.extra_rewards["goal"] > 0

    def test_faster_movement(self):
        """Soccer players should move faster than fish."""
        tank = TankRuleSet()
        soccer = SoccerRuleSet()
        assert soccer.action_space.max_speed > tank.action_space.max_speed


class TestRulesetRegistry:
    """Tests for ruleset registry functions."""

    def test_get_builtin_rulesets(self):
        """Should get built-in rulesets by mode ID."""
        assert get_ruleset("tank") is not None
        assert get_ruleset("petri") is not None
        assert get_ruleset("soccer") is not None

    def test_get_unknown_returns_none(self):
        """Should return None for unknown mode ID."""
        assert get_ruleset("unknown_mode") is None

    def test_list_includes_builtins(self):
        """Should list all built-in rulesets."""
        modes = list_rulesets()
        assert "tank" in modes
        assert "petri" in modes
        assert "soccer" in modes

    def test_register_custom_ruleset(self):
        """Should be able to register custom rulesets."""

        class CustomRuleSet(TankRuleSet):
            @property
            def mode_id(self) -> str:
                return "custom_test"

            @property
            def display_name(self) -> str:
                return "Custom Test"

        custom = CustomRuleSet()
        register_ruleset(custom)

        assert get_ruleset("custom_test") is custom
        assert "custom_test" in list_rulesets()


class TestModeRuleSetProtocol:
    """Tests for ModeRuleSet abstract base class."""

    def test_get_allowed_actions(self):
        """All rulesets should return allowed actions list."""
        for mode_id in ["tank", "petri", "soccer"]:
            ruleset = get_ruleset(mode_id)
            assert ruleset is not None
            actions = ruleset.get_allowed_actions()
            assert isinstance(actions, list)
            assert len(actions) > 0

    def test_validate_action_valid(self):
        """Should validate allowed actions as valid."""
        ruleset = TankRuleSet()
        assert ruleset.validate_action({"type": "move"}) is True
        assert ruleset.validate_action({"type": "eat"}) is True

    def test_validate_action_invalid(self):
        """Should reject disallowed actions."""
        ruleset = TankRuleSet()
        assert ruleset.validate_action({"type": "kick"}) is False  # No kick in tank
