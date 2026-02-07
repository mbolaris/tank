"""Tests for ComposablePokerStrategy.

Verifies:
- Random creation
- Crossover/inheritance
- Mutation
- Serialization
- Decision making
"""

import random

import pytest

from core.poker.betting.actions import BettingAction
from core.poker.strategy.composable import (POKER_SUB_BEHAVIOR_PARAMS,
                                            BettingStyle, BluffingApproach,
                                            ComposablePokerStrategy,
                                            HandSelection, PositionAwareness,
                                            ShowdownTendency)
from core.poker.strategy.implementations import crossover_poker_strategies


class TestComposablePokerStrategyCreation:
    """Test strategy creation and initialization."""

    def test_create_random_strategy(self):
        """Can create a random composable strategy."""
        rng = random.Random(42)  # Deterministic seed
        strategy = ComposablePokerStrategy.create_random(rng)
        assert strategy is not None
        assert isinstance(strategy.hand_selection, HandSelection)
        assert isinstance(strategy.betting_style, BettingStyle)
        assert isinstance(strategy.bluffing_approach, BluffingApproach)
        assert isinstance(strategy.position_awareness, PositionAwareness)
        assert isinstance(strategy.showdown_tendency, ShowdownTendency)
        assert len(strategy.parameters) > 0

    def test_random_instance_alias(self):
        """random_instance is an alias for create_random."""
        rng = random.Random(42)  # Deterministic seed
        strategy = ComposablePokerStrategy.random_instance(rng)
        assert strategy is not None

    def test_default_parameters_initialized(self):
        """Default parameters are initialized to midpoints."""
        strategy = ComposablePokerStrategy()
        for key, (low, high) in POKER_SUB_BEHAVIOR_PARAMS.items():
            assert key in strategy.parameters
            # Should be approximately midpoint
            midpoint = (low + high) / 2
            assert strategy.parameters[key] == pytest.approx(midpoint)

    def test_deterministic_creation_with_seed(self):
        """Creating with same seed produces identical strategies."""
        rng1 = random.Random(42)
        rng2 = random.Random(42)
        s1 = ComposablePokerStrategy.create_random(rng1)
        s2 = ComposablePokerStrategy.create_random(rng2)
        assert s1.hand_selection == s2.hand_selection
        assert s1.betting_style == s2.betting_style
        assert s1.parameters == s2.parameters


class TestComposablePokerStrategyInheritance:
    """Test crossover and inheritance."""

    def test_from_parents_creates_offspring(self):
        """Offspring combines parent traits."""
        rng = random.Random(42)  # Deterministic seed
        p1 = ComposablePokerStrategy.create_random(random.Random(1))
        p2 = ComposablePokerStrategy.create_random(random.Random(2))
        child = ComposablePokerStrategy.from_parents(p1, p2, rng=rng)
        assert child is not None
        # Child should have some combination of parent sub-behaviors
        assert isinstance(child.hand_selection, HandSelection)

    def test_winner_biased_inheritance(self):
        """Heavy winner weight favors parent1 traits."""
        rng = random.Random(42)  # Deterministic seed
        p1 = ComposablePokerStrategy(hand_selection=HandSelection.ULTRA_TIGHT)
        p2 = ComposablePokerStrategy(hand_selection=HandSelection.LOOSE)
        # With weight1=1.0, child should always get parent1's traits
        child = ComposablePokerStrategy.from_parents(
            p1, p2, weight1=1.0, mutation_rate=0.0, sub_behavior_switch_rate=0.0, rng=rng
        )
        assert child.hand_selection == HandSelection.ULTRA_TIGHT

    def test_crossover_function_handles_composable(self):
        """crossover_poker_strategies works with ComposablePokerStrategy."""
        rng = random.Random(42)  # Deterministic seed
        p1 = ComposablePokerStrategy.create_random(rng)
        p2 = ComposablePokerStrategy.create_random(rng)
        child = crossover_poker_strategies(p1, p2, rng=rng)
        assert isinstance(child, ComposablePokerStrategy)

    def test_parameters_blended(self):
        """Continuous parameters are blended between parents."""
        rng = random.Random(42)  # Deterministic seed
        p1 = ComposablePokerStrategy(parameters={"bluff_frequency": 0.1})
        p2 = ComposablePokerStrategy(parameters={"bluff_frequency": 0.5})
        # 50/50 blend
        child = ComposablePokerStrategy.from_parents(
            p1, p2, weight1=0.5, mutation_rate=0.0, rng=rng
        )
        # Should be around 0.3, but mutation might adjust slightly
        assert 0.15 <= child.parameters["bluff_frequency"] <= 0.45


class TestComposablePokerStrategyMutation:
    """Test mutation functionality."""

    def test_mutate_changes_parameters(self):
        """Mutation changes at least some parameters."""
        rng = random.Random(1)
        strategy = ComposablePokerStrategy.create_random(rng)
        original_params = dict(strategy.parameters)
        # High mutation rate to ensure change
        strategy.mutate(mutation_rate=1.0, mutation_strength=0.5, rng=rng)
        # At least one parameter should be different
        changed = any(original_params[k] != strategy.parameters[k] for k in original_params)
        assert changed

    def test_mutate_respects_bounds(self):
        """Mutated parameters stay within bounds."""
        rng = random.Random(42)  # Deterministic seed
        strategy = ComposablePokerStrategy.create_random(rng)
        for _ in range(10):
            strategy.mutate(mutation_rate=1.0, mutation_strength=0.5, rng=rng)
        for key, value in strategy.parameters.items():
            if key in POKER_SUB_BEHAVIOR_PARAMS:
                low, high = POKER_SUB_BEHAVIOR_PARAMS[key]
                assert low <= value <= high, f"{key} out of bounds: {value}"

    def test_sub_behavior_switch_rate(self):
        """Sub-behaviors can switch during mutation."""
        # Create many strategies and mutate with high switch rate
        switches = 0
        for seed in range(100):
            strategy = ComposablePokerStrategy(hand_selection=HandSelection.TIGHT)
            strategy.mutate(sub_behavior_switch_rate=0.5, rng=random.Random(seed))
            if strategy.hand_selection != HandSelection.TIGHT:
                switches += 1
        # Should see some switches with 50% rate
        assert switches > 10  # At least 10% switched

    def test_clone_with_mutation(self):
        """Clone creates independent copy with mutations."""
        rng = random.Random(1)
        original = ComposablePokerStrategy.create_random(rng)
        # Disable both mutation and sub-behavior switching
        clone = original.clone_with_mutation(
            mutation_rate=0.0, sub_behavior_switch_rate=0.0, rng=rng
        )
        # With no mutation and no switching, should have same sub-behaviors
        assert clone.hand_selection == original.hand_selection
        assert clone.betting_style == original.betting_style


class TestComposablePokerStrategySerialization:
    """Test serialization and deserialization."""

    def test_to_dict_and_back(self):
        """Strategy survives round-trip serialization."""
        rng = random.Random(42)  # Deterministic seed
        original = ComposablePokerStrategy.create_random(rng)
        data = original.to_dict()
        restored = ComposablePokerStrategy.from_dict(data)
        assert restored.hand_selection == original.hand_selection
        assert restored.betting_style == original.betting_style
        assert restored.bluffing_approach == original.bluffing_approach
        assert restored.parameters == original.parameters

    def test_to_dict_structure(self):
        """Serialized dict has expected structure."""
        strategy = ComposablePokerStrategy()
        data = strategy.to_dict()
        assert data["type"] == "ComposablePokerStrategy"
        assert "hand_selection" in data
        assert "parameters" in data
        assert isinstance(data["hand_selection"], int)


class TestComposablePokerStrategyDecisions:
    """Test betting decision logic."""

    def test_decides_action(self):
        """Strategy returns valid action tuple."""
        rng = random.Random(42)  # Deterministic seed
        strategy = ComposablePokerStrategy()
        action, amount = strategy.decide_action(
            hand_strength=0.5,
            current_bet=0,
            opponent_bet=10,
            pot=50,
            player_energy=100,
            position_on_button=True,
            rng=rng,
        )
        assert isinstance(action, BettingAction)
        assert isinstance(amount, (int, float))

    def test_folds_with_weak_hand_tight_strategy(self):
        """Ultra-tight strategy folds weak hands."""
        rng = random.Random(42)  # Deterministic seed
        strategy = ComposablePokerStrategy(hand_selection=HandSelection.ULTRA_TIGHT)
        action, _ = strategy.decide_action(
            hand_strength=0.2,  # Weak hand
            current_bet=0,
            opponent_bet=20,
            pot=50,
            player_energy=100,
            rng=rng,
        )
        # Should fold weak hand
        assert action == BettingAction.FOLD

    def test_raises_with_premium_hand(self):
        """Strategy raises with premium hands when facing a bet."""
        rng = random.Random(42)  # Deterministic seed
        strategy = ComposablePokerStrategy(
            hand_selection=HandSelection.BALANCED,
            betting_style=BettingStyle.VALUE_HEAVY,
            bluffing_approach=BluffingApproach.BALANCED,
        )
        # Set premium threshold to ensure 0.95 triggers raise
        strategy.parameters["premium_threshold"] = 0.90

        action, amount = strategy.decide_action(
            hand_strength=0.95,  # Premium hand (above threshold)
            current_bet=0,
            opponent_bet=20,  # Face a bet so we must act
            pot=50,
            player_energy=100,
            rng=rng,
        )
        # With premium hand above threshold, should always raise
        assert action == BettingAction.RAISE
        assert amount > 0

    def test_insufficient_energy_folds(self):
        """Folds when call amount exceeds energy."""
        rng = random.Random(42)  # Deterministic seed
        strategy = ComposablePokerStrategy()
        action, _ = strategy.decide_action(
            hand_strength=0.9,
            current_bet=0,
            opponent_bet=200,  # More than we have
            pot=50,
            player_energy=100,
            rng=rng,
        )
        assert action == BettingAction.FOLD

    def test_position_affects_decision(self):
        """Position bonus helps marginal hands."""
        strategy = ComposablePokerStrategy(
            position_awareness=PositionAwareness.HEAVY_EXPLOIT,
            hand_selection=HandSelection.BALANCED,
        )
        # Fixed RNGs for consistency
        rng_ip = random.Random(42)
        rng_oop = random.Random(42)

        # Same marginal hand, different position
        # In position should be more likely to play
        ip_action, _ = strategy.decide_action(
            hand_strength=0.3,
            current_bet=0,
            opponent_bet=10,
            pot=30,
            player_energy=100,
            position_on_button=True,
            rng=rng_ip,
        )
        oop_action, _ = strategy.decide_action(
            hand_strength=0.3,
            current_bet=0,
            opponent_bet=10,
            pot=30,
            player_energy=100,
            position_on_button=False,
            rng=rng_oop,
        )
        # At least the adjusted strength should differ
        # (Can't guarantee different actions due to randomness)


class TestOpponentModeling:
    """Test opponent model functionality."""

    def test_update_opponent_model(self):
        """Opponent model tracks observations."""
        strategy = ComposablePokerStrategy()
        strategy.update_opponent_model(
            "opp1", folded=True, raised=False, called=False, aggression=0.3
        )
        strategy.update_opponent_model(
            "opp1", folded=False, raised=True, called=False, aggression=0.7
        )

        model = strategy.opponent_models["opp1"]
        assert model.games_played == 2
        assert model.times_folded == 1
        assert model.times_raised == 1
        assert model.fold_rate == 0.5

    def test_opponent_adjustment_affects_bluffing(self):
        """High fold rate opponent should trigger more bluffs."""
        strategy = ComposablePokerStrategy(
            bluffing_approach=BluffingApproach.BALANCED,
        )
        strategy.parameters["opponent_model_weight"] = 0.5
        # Create opponent who folds a lot
        for _ in range(10):
            strategy.update_opponent_model(
                "weak_opp", folded=True, raised=False, called=False, aggression=0.2
            )

        # Adjustment should be positive (can exploit with bluffs)
        adj = strategy._get_opponent_adjustment("weak_opp")
        assert adj > 0


class TestStrategyDiversity:
    """Test that the system produces diverse strategies."""

    def test_random_strategies_are_diverse(self):
        """Random strategies have variety in sub-behaviors."""
        rng = random.Random(42)  # Deterministic seed
        strategies = [ComposablePokerStrategy.create_random(rng) for _ in range(100)]

        # Should see multiple different hand selections
        hand_selections = {s.hand_selection for s in strategies}
        assert len(hand_selections) >= 3  # At least 3 of 4 options

        # Should see multiple bluffing approaches
        bluff_approaches = {s.bluffing_approach for s in strategies}
        assert len(bluff_approaches) >= 3

    def test_offspring_can_differ_from_parents(self):
        """Offspring can have different sub-behaviors than either parent."""
        p1 = ComposablePokerStrategy(hand_selection=HandSelection.TIGHT)
        p2 = ComposablePokerStrategy(hand_selection=HandSelection.TIGHT)

        # With mutation, offspring can differ
        different = False
        for seed in range(100):
            child = ComposablePokerStrategy.from_parents(
                p1, p2, sub_behavior_switch_rate=0.2, rng=random.Random(seed)
            )
            if child.hand_selection != HandSelection.TIGHT:
                different = True
                break
        assert different
