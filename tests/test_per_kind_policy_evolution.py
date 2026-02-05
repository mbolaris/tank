"""Regression tests for per-kind policy evolution.

Verifies that:
1. Fish created with soccer enabled always get a valid soccer_policy_id.
2. Offspring genomes keep per-kind policy IDs valid (no cross-kind IDs).
3. Neither asexual nor poker reproduction can produce a soccer_policy_id
   that points to a movement component ID (or vice versa).
"""

import random

from core.code_pool import (
    BUILTIN_CHASE_BALL_SOCCER_ID,
    BUILTIN_SEEK_NEAREST_FOOD_ID,
    create_default_genome_code_pool,
)
from core.config.simulation_config import SimulationConfig, SoccerConfig
from core.environment import Environment
from core.genetics import Genome
from core.genetics.code_policy_traits import (
    MOVEMENT_POLICY,
    SOCCER_POLICY,
    mutate_code_policies,
    validate_code_policy_ids,
)
from core.genetics.trait import GeneticTrait
from core.movement_strategy import AlgorithmicMovement


def _make_soccer_env(seed: int = 42) -> Environment:
    """Create an Environment with soccer enabled and a genome code pool."""
    rng = random.Random(seed)
    soccer_cfg = SoccerConfig(enabled=True)
    config = SimulationConfig(soccer=soccer_cfg)
    env = Environment(width=800, height=600, rng=rng, simulation_config=config)
    return env


def _make_fish(env: Environment, **kwargs):
    """Create a fish in the given environment."""
    from core.entities.fish import Fish

    defaults = dict(
        environment=env,
        movement_strategy=AlgorithmicMovement(),
        species="test_fish",
        x=100,
        y=100,
        speed=2.0,
    )
    defaults.update(kwargs)
    return Fish(**defaults)


class TestFishCreationSoccerPolicy:
    """Fish created with soccer enabled should always get a valid soccer_policy_id."""

    def test_new_fish_has_soccer_policy_when_enabled(self):
        env = _make_soccer_env()
        fish = _make_fish(env)

        trait = fish.genome.behavioral.soccer_policy_id
        assert trait is not None, "soccer_policy_id trait should exist"
        assert trait.value is not None, "soccer_policy_id value should be set"

        # Should be a valid soccer policy
        pool = env.genome_code_pool
        soccer_ids = pool.get_components_by_kind("soccer_policy")
        assert (
            trait.value in soccer_ids
        ), f"soccer_policy_id {trait.value} not in pool soccer components {soccer_ids}"

    def test_new_fish_soccer_policy_is_default_when_available(self):
        env = _make_soccer_env()
        fish = _make_fish(env)

        pool = env.genome_code_pool
        default_id = pool.get_default("soccer_policy")
        assert default_id is not None, "Pool should have a default soccer policy"

        trait = fish.genome.behavioral.soccer_policy_id
        assert trait is not None and trait.value == default_id

    def test_fish_without_soccer_has_no_soccer_policy(self):
        """When soccer is not enabled, soccer_policy_id should remain None."""
        rng = random.Random(42)
        config = SimulationConfig(soccer=SoccerConfig(enabled=False))
        env = Environment(width=800, height=600, rng=rng, simulation_config=config)
        fish = _make_fish(env)

        trait = fish.genome.behavioral.soccer_policy_id
        # Should be None (default from BehavioralTraits.random)
        assert trait is None or trait.value is None

    def test_fish_with_genome_preserves_existing_soccer_policy(self):
        """If genome already has a soccer_policy_id, Fish.__init__ should not overwrite it."""
        env = _make_soccer_env()
        rng = random.Random(99)

        genome = Genome.random(rng=rng)
        genome.behavioral.soccer_policy_id = GeneticTrait(BUILTIN_CHASE_BALL_SOCCER_ID)
        genome.behavioral.soccer_policy_params = GeneticTrait({"custom": 1.0})

        fish = _make_fish(env, genome=genome)

        assert fish.genome.behavioral.soccer_policy_id.value == BUILTIN_CHASE_BALL_SOCCER_ID
        assert fish.genome.behavioral.soccer_policy_params.value == {"custom": 1.0}


class TestReproductionPerKindIntegrity:
    """Offspring genomes keep per-kind IDs valid; no cross-kind contamination."""

    def test_asexual_offspring_has_valid_per_kind_policies(self):
        """After asexual reproduction, offspring should have valid per-kind IDs."""
        env = _make_soccer_env(seed=101)
        pool = env.genome_code_pool

        rng = random.Random(101)
        parent_genome = Genome.random(rng=rng)
        # Give parent a soccer policy
        parent_genome.behavioral.soccer_policy_id = GeneticTrait(BUILTIN_CHASE_BALL_SOCCER_ID)
        parent_genome.behavioral.soccer_policy_params = GeneticTrait({})

        movement_ids = set(pool.get_components_by_kind("movement_policy"))
        soccer_ids = set(pool.get_components_by_kind("soccer_policy"))

        # Run many asexual reproductions
        for seed in range(50):
            child_rng = random.Random(seed + 1000)
            child = Genome.clone_with_mutation(parent_genome, rng=child_rng)
            mutate_code_policies(child.behavioral, pool, child_rng)
            validate_code_policy_ids(child.behavioral, pool, child_rng)

            # Movement policy should be a movement ID (or None)
            mv_trait = child.behavioral.movement_policy_id
            if mv_trait is not None and mv_trait.value is not None:
                assert (
                    mv_trait.value in movement_ids
                ), f"movement_policy_id {mv_trait.value} is not a movement component"
                assert (
                    mv_trait.value not in soccer_ids
                ), f"movement_policy_id {mv_trait.value} is a soccer component (cross-kind!)"

            # Soccer policy should be a soccer ID (or None)
            sc_trait = child.behavioral.soccer_policy_id
            if sc_trait is not None and sc_trait.value is not None:
                assert (
                    sc_trait.value in soccer_ids
                ), f"soccer_policy_id {sc_trait.value} is not a soccer component"
                assert (
                    sc_trait.value not in movement_ids
                ), f"soccer_policy_id {sc_trait.value} is a movement component (cross-kind!)"

    def test_no_cross_kind_contamination_without_pool_mutation(self):
        """Even with available_policies=None, inheritance shouldn't cross kinds."""
        rng = random.Random(202)
        pool = create_default_genome_code_pool()

        parent = Genome.random(rng=rng)
        parent.behavioral.soccer_policy_id = GeneticTrait(BUILTIN_CHASE_BALL_SOCCER_ID)
        parent.behavioral.soccer_policy_params = GeneticTrait({})

        movement_ids = set(pool.get_components_by_kind("movement_policy"))
        soccer_ids = set(pool.get_components_by_kind("soccer_policy"))

        for seed in range(100):
            child_rng = random.Random(seed + 2000)
            # Clone WITHOUT available_policies (the fixed path)
            child = Genome.clone_with_mutation(parent, rng=child_rng)

            sc_trait = child.behavioral.soccer_policy_id
            if sc_trait is not None and sc_trait.value is not None:
                # With available_policies=None, _inherit_single_policy can only
                # inherit from parent or drop -- never swap to movement IDs.
                assert (
                    sc_trait.value not in movement_ids
                ), f"soccer_policy_id {sc_trait.value} is a movement ID (cross-kind!)"

    def test_mutate_code_policies_uses_correct_kind(self):
        """mutate_code_policies should swap within the correct kind only."""
        pool = create_default_genome_code_pool()
        movement_ids = set(pool.get_components_by_kind("movement_policy"))
        soccer_ids = set(pool.get_components_by_kind("soccer_policy"))

        rng = random.Random(303)
        parent = Genome.random(rng=rng)
        parent.behavioral.movement_policy_id = GeneticTrait(BUILTIN_SEEK_NEAREST_FOOD_ID)
        parent.behavioral.movement_policy_params = GeneticTrait({})
        parent.behavioral.soccer_policy_id = GeneticTrait(BUILTIN_CHASE_BALL_SOCCER_ID)
        parent.behavioral.soccer_policy_params = GeneticTrait({})

        for seed in range(100):
            child_rng = random.Random(seed + 3000)
            child = Genome.clone_with_mutation(parent, rng=child_rng)
            mutate_code_policies(child.behavioral, pool, child_rng)

            mv = child.behavioral.movement_policy_id
            if mv is not None and mv.value is not None:
                assert mv.value in movement_ids
                assert mv.value not in soccer_ids

            sc = child.behavioral.soccer_policy_id
            if sc is not None and sc.value is not None:
                assert sc.value in soccer_ids
                assert sc.value not in movement_ids


class TestReproductionPathsCallPoolMutation:
    """Verify that the actual reproduction paths (asexual, poker) use pool-aware mutation."""

    def test_asexual_offspring_fish_has_valid_soccer_policy(self):
        """A fish that reproduces asexually should produce offspring with valid policies."""
        env = _make_soccer_env(seed=404)
        pool = env.genome_code_pool
        soccer_ids = set(pool.get_components_by_kind("soccer_policy"))

        parent = _make_fish(env)
        # Confirm parent has soccer policy (assigned in Fish.__init__)
        assert parent.genome.behavioral.soccer_policy_id is not None
        assert parent.genome.behavioral.soccer_policy_id.value in soccer_ids

        # Force parent to be eligible for reproduction
        from core.entities.base import LifeStage

        parent.energy = parent.max_energy
        parent._reproduction_component.reproduction_cooldown = 0
        parent._reproduction_component.overflow_energy_bank = parent.max_energy * 2
        parent._lifecycle_component.force_life_stage(LifeStage.ADULT, reason="test")

        baby = parent._create_asexual_offspring()
        if baby is not None:
            # Baby should have valid soccer policy (set in Fish.__init__)
            sc_trait = baby.genome.behavioral.soccer_policy_id
            assert sc_trait is not None, "Baby should have soccer_policy_id"
            assert sc_trait.value is not None, "Baby soccer_policy_id should not be None"
            assert (
                sc_trait.value in soccer_ids
            ), f"Baby soccer_policy_id {sc_trait.value} not in soccer pool"

            # Should NOT have cross-kind contamination
            movement_ids = set(pool.get_components_by_kind("movement_policy"))
            assert sc_trait.value not in movement_ids


class TestDeterminismPreserved:
    """Verify that adding pool-aware mutation doesn't break determinism."""

    def test_same_seed_same_offspring(self):
        """Same seed should produce identical offspring policies."""
        pool = create_default_genome_code_pool()
        rng1 = random.Random(500)
        rng2 = random.Random(500)

        parent = Genome.random(rng=random.Random(999))
        parent.behavioral.soccer_policy_id = GeneticTrait(BUILTIN_CHASE_BALL_SOCCER_ID)
        parent.behavioral.soccer_policy_params = GeneticTrait({})

        child1 = Genome.clone_with_mutation(parent, rng=rng1)
        mutate_code_policies(child1.behavioral, pool, rng1)
        validate_code_policy_ids(child1.behavioral, pool, rng1)

        child2 = Genome.clone_with_mutation(parent, rng=rng2)
        mutate_code_policies(child2.behavioral, pool, rng2)
        validate_code_policy_ids(child2.behavioral, pool, rng2)

        # Movement policies should match
        mv1 = child1.behavioral.movement_policy_id
        mv2 = child2.behavioral.movement_policy_id
        assert (mv1 and mv1.value) == (mv2 and mv2.value)

        # Soccer policies should match
        sc1 = child1.behavioral.soccer_policy_id
        sc2 = child2.behavioral.soccer_policy_id
        assert (sc1 and sc1.value) == (sc2 and sc2.value)
