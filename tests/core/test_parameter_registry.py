"""Tests for the unified ParameterRegistry and runtime bounds clamping.

Covers backlog item 3.2: the registry composes the three existing bounds
tables (SUB_BEHAVIOR_PARAMS, POKER_SUB_BEHAVIOR_PARAMS,
ALGORITHM_PARAMETER_BOUNDS) without moving them, and the mutation/crossover
boundaries clamp evolved parameters so they can never silently leave their
design range.

Determinism contract: clamping consumes no RNG and leaves in-range values
bit-identical.
"""

import random

from core.algorithms.base import ALGORITHM_PARAMETER_BOUNDS
from core.algorithms.composable.behavior import ComposableBehavior
from core.algorithms.composable.definitions import SUB_BEHAVIOR_PARAMS
from core.algorithms.registry import ALGORITHM_REGISTRY
from core.parameters import (
    ALGORITHM_DOMAIN_PREFIX,
    DOMAIN_BEHAVIOR,
    DOMAIN_POKER,
    ParameterRegistry,
)
from core.poker.strategy.composable.definitions import POKER_SUB_BEHAVIOR_PARAMS
from core.poker.strategy.composable.strategy import ComposablePokerStrategy
from core.poker.strategy.composable.validator import PokerStrategyValidator


class TestRegistryCoverage:
    """The registry must expose every entry of all three source tables."""

    def test_covers_all_behavior_params(self):
        for key, (low, high) in SUB_BEHAVIOR_PARAMS.items():
            assert ParameterRegistry.get_bounds(DOMAIN_BEHAVIOR, key) == (low, high)

    def test_covers_all_poker_params(self):
        for key, (low, high) in POKER_SUB_BEHAVIOR_PARAMS.items():
            assert ParameterRegistry.get_bounds(DOMAIN_POKER, key) == (low, high)

    def test_covers_all_algorithm_params(self):
        for algo_id, table in ALGORITHM_PARAMETER_BOUNDS.items():
            domain = f"{ALGORITHM_DOMAIN_PREFIX}{algo_id}"
            for key, (low, high) in table.items():
                assert ParameterRegistry.get_bounds(domain, key) == (low, high)

    def test_domains_listing(self):
        domains = ParameterRegistry.domains()
        assert DOMAIN_BEHAVIOR in domains
        assert DOMAIN_POKER in domains
        assert f"{ALGORITHM_DOMAIN_PREFIX}greedy_food_seeker" in domains
        assert len(domains) == 2 + len(ALGORITHM_PARAMETER_BOUNDS)

    def test_iter_parameters_covers_all_three_sources(self):
        entries = list(ParameterRegistry.iter_parameters())
        expected = (
            len(SUB_BEHAVIOR_PARAMS)
            + len(POKER_SUB_BEHAVIOR_PARAMS)
            + sum(len(t) for t in ALGORITHM_PARAMETER_BOUNDS.values())
        )
        assert len(entries) == expected
        for domain, name, low, high in entries:
            assert low <= high
            assert ParameterRegistry.get_bounds(domain, name) == (low, high)

    def test_unknown_lookups_return_none(self):
        assert ParameterRegistry.get_bounds(DOMAIN_BEHAVIOR, "no_such_param") is None
        assert ParameterRegistry.get_bounds("no_such_domain", "pursuit_speed") is None
        assert ParameterRegistry.get_bounds(f"{ALGORITHM_DOMAIN_PREFIX}no_such_algo", "x") is None


class TestClamp:
    """Clamp semantics: enforce bounds, identity for in-range/unknown values."""

    def test_clamp_below_and_above(self):
        low, high = SUB_BEHAVIOR_PARAMS["pursuit_speed"]
        assert ParameterRegistry.clamp(DOMAIN_BEHAVIOR, "pursuit_speed", low - 1.0) == low
        assert ParameterRegistry.clamp(DOMAIN_BEHAVIOR, "pursuit_speed", high + 1.0) == high

    def test_clamp_in_range_is_bit_identical(self):
        value = 1.2345678901234567  # inside pursuit_speed bounds (0.9, 1.6)
        assert ParameterRegistry.clamp(DOMAIN_BEHAVIOR, "pursuit_speed", value) == value
        low, high = SUB_BEHAVIOR_PARAMS["pursuit_speed"]
        assert ParameterRegistry.clamp(DOMAIN_BEHAVIOR, "pursuit_speed", low) == low
        assert ParameterRegistry.clamp(DOMAIN_BEHAVIOR, "pursuit_speed", high) == high

    def test_clamp_unknown_is_identity(self):
        assert ParameterRegistry.clamp(DOMAIN_BEHAVIOR, "no_such_param", 1e9) == 1e9
        assert ParameterRegistry.clamp("no_such_domain", "pursuit_speed", -1e9) == -1e9
        # Poker domain must also leave undeclared keys untouched.
        assert ParameterRegistry.clamp(DOMAIN_POKER, "no_such_param", 7.0) == 7.0

    def test_clamp_algorithm_domain(self):
        low, high = ALGORITHM_PARAMETER_BOUNDS["greedy_food_seeker"]["speed_multiplier"]
        domain = f"{ALGORITHM_DOMAIN_PREFIX}greedy_food_seeker"
        assert ParameterRegistry.clamp(domain, "speed_multiplier", 99.0) == high
        assert ParameterRegistry.clamp(domain, "speed_multiplier", -99.0) == low

    def test_clamp_params_mixed_dict(self):
        params = {
            "pursuit_speed": 99.0,  # out of range -> clamped
            "circle_radius": 50.0,  # in range (30, 80) -> unchanged
            "custom_key": 42.0,  # undeclared -> untouched
            "label": "not-a-number",  # non-numeric -> untouched
        }
        result = ParameterRegistry.clamp_params(DOMAIN_BEHAVIOR, params)
        assert result["pursuit_speed"] == SUB_BEHAVIOR_PARAMS["pursuit_speed"][1]
        assert result["circle_radius"] == 50.0
        assert result["custom_key"] == 42.0
        assert result["label"] == "not-a-number"
        # Input dict must not be modified.
        assert params["pursuit_speed"] == 99.0

    def test_clamp_params_unknown_domain_copies_through(self):
        params = {"a": 1.0}
        result = ParameterRegistry.clamp_params("no_such_domain", params)
        assert result == params
        assert result is not params

    def test_poker_clamp_aligned_with_validator(self):
        """Registry poker clamping delegates to PokerStrategyValidator."""
        for key, (low, high) in POKER_SUB_BEHAVIOR_PARAMS.items():
            for value in (low - 1.0, (low + high) / 2, high + 1.0):
                assert ParameterRegistry.clamp(DOMAIN_POKER, key, value) == (
                    PokerStrategyValidator.clamp(key, value)
                )

    def test_validator_clamp_known_passthrough_for_unknown(self):
        # clamp() applies (0, 1) fallback bounds for unknown keys (legacy
        # behavior); clamp_known() must leave unknown keys untouched.
        assert PokerStrategyValidator.clamp("no_such_param", 7.0) == 1.0
        assert PokerStrategyValidator.clamp_known("no_such_param", 7.0) == 7.0


class TestRuntimeClampingComposableBehavior:
    """Mutation/crossover boundary enforcement for ComposableBehavior."""

    def test_out_of_range_value_is_clamped_without_mutation(self):
        behavior = ComposableBehavior()
        behavior.parameters["pursuit_speed"] = 99.0
        behavior.parameters["flee_threshold"] = -5.0
        behavior.mutate(
            mutation_rate=0.0,
            mutation_strength=0.0,
            sub_behavior_switch_rate=0.0,
            rng=random.Random(1),
        )
        assert behavior.parameters["pursuit_speed"] == SUB_BEHAVIOR_PARAMS["pursuit_speed"][1]
        assert behavior.parameters["flee_threshold"] == SUB_BEHAVIOR_PARAMS["flee_threshold"][0]

    def test_undeclared_key_is_not_clamped(self):
        behavior = ComposableBehavior()
        behavior.parameters["legacy_custom_param"] = 1e6
        behavior.mutate(
            mutation_rate=0.0,
            mutation_strength=0.0,
            sub_behavior_switch_rate=0.0,
            rng=random.Random(1),
        )
        assert behavior.parameters["legacy_custom_param"] == 1e6

    def test_boundary_mutation_cannot_exceed_bounds(self):
        rng = random.Random(7)
        behavior = ComposableBehavior()
        for key, (_low, high) in SUB_BEHAVIOR_PARAMS.items():
            behavior.parameters[key] = high  # start at the upper boundary
        for _ in range(50):
            behavior.mutate(
                mutation_rate=1.0, mutation_strength=1.0, sub_behavior_switch_rate=0.0, rng=rng
            )
            for key, (low, high) in SUB_BEHAVIOR_PARAMS.items():
                assert low <= behavior.parameters[key] <= high, key

    def test_clamping_consumes_no_rng_and_preserves_in_range_values(self):
        rng_a = random.Random(123)
        rng_b = random.Random(123)
        in_range = ComposableBehavior()
        before = dict(in_range.parameters)
        out_of_range = ComposableBehavior()
        out_of_range.parameters["pursuit_speed"] = 999.0

        in_range.mutate(0.0, 0.0, sub_behavior_switch_rate=0.0, rng=rng_a)
        out_of_range.mutate(0.0, 0.0, sub_behavior_switch_rate=0.0, rng=rng_b)

        # Identical RNG trajectory whether or not clamping fired.
        assert rng_a.getstate() == rng_b.getstate()
        # In-range values are bit-identical after the clamp pass.
        assert in_range.parameters == before

    def test_crossover_offspring_within_bounds(self):
        """from_parents (which ends in mutate) cannot emit out-of-range params."""
        rng = random.Random(42)
        parent1 = ComposableBehavior()
        parent2 = ComposableBehavior()
        # Simulate corrupted/legacy parents with out-of-range declared params.
        parent1.parameters["pursuit_speed"] = 50.0
        parent2.parameters["pursuit_speed"] = 70.0
        child = ComposableBehavior.from_parents(parent1, parent2, rng=rng)
        low, high = SUB_BEHAVIOR_PARAMS["pursuit_speed"]
        assert low <= child.parameters["pursuit_speed"] <= high


class TestRuntimeClampingPokerStrategy:
    """Mutation/crossover boundary enforcement for ComposablePokerStrategy."""

    def test_out_of_range_value_is_clamped_without_mutation(self):
        strategy = ComposablePokerStrategy()
        strategy.parameters["bluff_frequency"] = 5.0
        strategy.mutate(
            mutation_rate=0.0,
            mutation_strength=0.0,
            sub_behavior_switch_rate=0.0,
            rng=random.Random(1),
        )
        assert strategy.parameters["bluff_frequency"] == (
            POKER_SUB_BEHAVIOR_PARAMS["bluff_frequency"][1]
        )

    def test_undeclared_key_is_not_clamped(self):
        strategy = ComposablePokerStrategy()
        strategy.parameters["legacy_custom_param"] = 9.0
        strategy.mutate(
            mutation_rate=0.0,
            mutation_strength=0.0,
            sub_behavior_switch_rate=0.0,
            rng=random.Random(1),
        )
        assert strategy.parameters["legacy_custom_param"] == 9.0

    def test_boundary_mutation_cannot_exceed_bounds(self):
        rng = random.Random(11)
        strategy = ComposablePokerStrategy()
        for key, (_low, high) in POKER_SUB_BEHAVIOR_PARAMS.items():
            strategy.parameters[key] = high
        for _ in range(50):
            strategy.mutate(
                mutation_rate=1.0, mutation_strength=1.0, sub_behavior_switch_rate=0.0, rng=rng
            )
            for key, (low, high) in POKER_SUB_BEHAVIOR_PARAMS.items():
                assert low <= strategy.parameters[key] <= high, key


class TestRuntimeClampingBehaviorAlgorithm:
    """Mutation boundary enforcement for classic BehaviorAlgorithm instances."""

    def _make_algorithm(self):
        cls = ALGORITHM_REGISTRY["GreedyFoodSeeker"]
        return cls.random_instance(rng=random.Random(3))

    def test_out_of_range_value_is_clamped_without_mutation(self):
        algo = self._make_algorithm()
        bounds = ALGORITHM_PARAMETER_BOUNDS["greedy_food_seeker"]
        algo.parameters["speed_multiplier"] = 99.0
        algo.parameters["detection_range"] = -1.0
        # rate=0 means no parameter is perturbed; the clamp pass still runs.
        algo.mutate_parameters(
            mutation_rate=0.0,
            mutation_strength=0.2,
            use_parameter_specific=False,
            rng=random.Random(5),
        )
        assert algo.parameters["speed_multiplier"] == bounds["speed_multiplier"][1]
        assert algo.parameters["detection_range"] == bounds["detection_range"][0]

    def test_boundary_mutation_cannot_exceed_bounds(self):
        rng = random.Random(9)
        algo = self._make_algorithm()
        bounds = ALGORITHM_PARAMETER_BOUNDS["greedy_food_seeker"]
        for key, (_low, high) in bounds.items():
            algo.parameters[key] = high
        for _ in range(50):
            algo.mutate_parameters(
                mutation_rate=1.0, mutation_strength=1.0, use_parameter_specific=False, rng=rng
            )
            for key, (low, high) in bounds.items():
                assert low <= algo.parameters[key] <= high, key

    def test_unbounded_parameter_untouched_by_clamp_pass(self):
        algo = self._make_algorithm()
        algo.parameters["legacy_custom_param"] = 1e6
        algo.mutate_parameters(
            mutation_rate=0.0,
            mutation_strength=0.2,
            use_parameter_specific=False,
            rng=random.Random(5),
        )
        assert algo.parameters["legacy_custom_param"] == 1e6
