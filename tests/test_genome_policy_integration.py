"""Integration tests for universal genome-based policy system.

Tests that Tank fish, Petri microbes, and Soccer agents can all use the same
genome-based policy construction mechanism via GenomeCodePool.
"""

import random

import pytest

from core.code_pool import (
    BUILTIN_CHASE_BALL_SOCCER_ID,
    BUILTIN_DEFENSIVE_SOCCER_ID,
    BUILTIN_FLEE_FROM_THREAT_ID,
    BUILTIN_SEEK_NEAREST_FOOD_ID,
    BUILTIN_STRIKER_SOCCER_ID,
    GenomePolicySet,
    create_default_genome_code_pool,
)
from core.environment import Environment
from core.genetics import Genome
from core.genetics.code_policy_traits import apply_policy_set_to_behavioral
from core.genetics.trait import GeneticTrait
from core.math_utils import Vector2
from core.movement_strategy import AlgorithmicMovement
from core.worlds.soccer_training.config import SoccerTrainingConfig
from core.worlds.soccer_training.world import SoccerTrainingWorldBackendAdapter


class TestGenomeCodePoolCreation:
    """Test that the default GenomeCodePool has all expected builtins."""

    def test_create_default_pool_has_movement_policies(self):
        pool = create_default_genome_code_pool()

        # Should have movement policies
        movement_components = pool.get_components_by_kind("movement_policy")
        assert BUILTIN_SEEK_NEAREST_FOOD_ID in movement_components
        assert BUILTIN_FLEE_FROM_THREAT_ID in movement_components

        # Should have default for required movement_policy
        assert pool.get_default("movement_policy") == BUILTIN_SEEK_NEAREST_FOOD_ID

    def test_create_default_pool_has_soccer_policies(self):
        pool = create_default_genome_code_pool()

        # Should have soccer policies
        soccer_components = pool.get_components_by_kind("soccer_policy")
        assert BUILTIN_CHASE_BALL_SOCCER_ID in soccer_components
        assert BUILTIN_DEFENSIVE_SOCCER_ID in soccer_components
        assert BUILTIN_STRIKER_SOCCER_ID in soccer_components

        # Should have default for soccer
        assert pool.get_default("soccer_policy") == BUILTIN_CHASE_BALL_SOCCER_ID


class TestTankFishWithGenomeCodePool:
    """Test that Tank fish can use genome-based policies from GenomeCodePool."""

    def test_fish_uses_seek_food_policy(self):
        """Fish with seek_food policy should move toward food."""
        rng = random.Random(42)
        env = Environment(width=800, height=600, rng=rng)

        # Environment now has genome_code_pool by default
        assert env.genome_code_pool is not None
        assert env.genome_code_pool.has_component(BUILTIN_SEEK_NEAREST_FOOD_ID)

        # Create a fish with movement policy via GenomePolicySet
        from core.entities.fish import Fish

        fish = Fish(
            environment=env,
            movement_strategy=AlgorithmicMovement(),
            species="test_fish",
            x=100,
            y=100,
            speed=2.0,
        )
        fish.vel = Vector2(0, 0)

        # Apply policy set to genome
        policy_set = GenomePolicySet()
        policy_set.set_policy("movement_policy", BUILTIN_SEEK_NEAREST_FOOD_ID)
        apply_policy_set_to_behavioral(fish.genome.behavioral, policy_set, rng)

        # Add food to environment
        from core.entities import Food

        food = Food(environment=env, x=200, y=100)
        env.spatial_grid.insert(food)

        # Execute movement - should move toward food
        fish.movement_strategy.move(fish)

        # Fish should move toward food (positive x direction)
        assert fish.vel.x > 0.0
        assert abs(fish.vel.y) < 0.1  # Should be roughly horizontal

    def test_fish_uses_flee_policy(self):
        """Fish with flee_from_threat policy should move away from threats."""
        rng = random.Random(123)
        env = Environment(width=800, height=600, rng=rng)

        from core.entities.fish import Fish

        fish = Fish(
            environment=env,
            movement_strategy=AlgorithmicMovement(),
            species="test_fish",
            x=100,
            y=100,
            speed=2.0,
        )
        fish.vel = Vector2(0, 0)

        # Apply flee policy
        policy_set = GenomePolicySet()
        policy_set.set_policy("movement_policy", BUILTIN_FLEE_FROM_THREAT_ID)
        apply_policy_set_to_behavioral(fish.genome.behavioral, policy_set, rng)

        # Add threat (crab) to environment
        from core.entities import Crab

        crab = Crab(environment=env, x=150, y=100, speed=1.0)
        env.spatial_grid.insert(crab)

        # Execute movement - should flee from crab
        fish.movement_strategy.move(fish)

        # Fish should flee away from crab (negative x direction)
        assert fish.vel.x < 0.0
        assert abs(fish.vel.y) < 0.1

    def test_policy_swapping(self):
        """Swapping policies should change behavior."""
        rng = random.Random(456)
        env = Environment(width=800, height=600, rng=rng)

        from core.entities.fish import Fish

        fish = Fish(
            environment=env,
            movement_strategy=AlgorithmicMovement(),
            species="test_fish",
            x=100,
            y=100,
            speed=2.0,
        )

        # Start with seek food
        policy_set = GenomePolicySet()
        policy_set.set_policy("movement_policy", BUILTIN_SEEK_NEAREST_FOOD_ID)
        apply_policy_set_to_behavioral(fish.genome.behavioral, policy_set, rng)

        # Swap to flee
        policy_set.set_policy("movement_policy", BUILTIN_FLEE_FROM_THREAT_ID)
        apply_policy_set_to_behavioral(fish.genome.behavioral, policy_set, rng)

        # Verify genome was updated
        assert fish.genome.behavioral.code_policy_component_id.value == BUILTIN_FLEE_FROM_THREAT_ID


class TestSoccerWithGenomeCodePool:
    """Test that Soccer agents can use genome-based policies."""

    def test_soccer_world_with_genome_code_pool(self):
        """Soccer world should use genome_code_pool to execute policies."""
        genome_pool = create_default_genome_code_pool()
        config = SoccerTrainingConfig(team_size=1, half_time_duration=100)

        world = SoccerTrainingWorldBackendAdapter(
            seed=789, config=config, genome_code_pool=genome_pool
        )

        result = world.reset(seed=789)

        # World should have players
        assert "left_1" in result.obs_by_agent
        assert "right_1" in result.obs_by_agent

    def test_soccer_player_uses_chase_ball_policy(self):
        """Player with chase_ball policy should pursue the ball."""
        genome_pool = create_default_genome_code_pool()
        config = SoccerTrainingConfig(team_size=1, half_time_duration=10)

        world = SoccerTrainingWorldBackendAdapter(
            seed=111, config=config, genome_code_pool=genome_pool
        )

        world.reset(seed=111)

        # Assign chase_ball policy to left player
        left_player = world._players["left_1"]
        policy_set = GenomePolicySet()
        policy_set.set_policy("soccer_policy", BUILTIN_CHASE_BALL_SOCCER_ID)

        rng = random.Random(111)
        apply_policy_set_to_behavioral(left_player.genome.behavioral, policy_set, rng)

        # Step without explicit actions - should use genome policy
        result = world.step()

        # Should complete without errors
        assert result.done is False

    def test_different_soccer_policies(self):
        """Different soccer policies should be available and usable."""
        genome_pool = create_default_genome_code_pool()

        # All three soccer policies should be registered
        assert genome_pool.has_component(BUILTIN_CHASE_BALL_SOCCER_ID)
        assert genome_pool.has_component(BUILTIN_DEFENSIVE_SOCCER_ID)
        assert genome_pool.has_component(BUILTIN_STRIKER_SOCCER_ID)


class TestDeterminismAndSafety:
    """Test that policies are deterministic and safe."""

    def test_policy_execution_is_deterministic(self):
        """Same seed should produce same behavior."""
        # Execute policy twice with same seed
        pool = create_default_genome_code_pool()

        observation = {
            "position": {"x": 0.0, "y": 0.0},
            "velocity": {"x": 0.0, "y": 0.0},
            "nearest_food_vector": {"x": 10.0, "y": 5.0},
            "nearest_threat_vector": {"x": 0.0, "y": 0.0},
            "energy": 50.0,
            "age": 100,
            "can_play_poker": False,
        }

        rng1 = random.Random(999)
        result1 = pool.execute_policy(
            component_id=BUILTIN_SEEK_NEAREST_FOOD_ID,
            observation=observation,
            rng=rng1,
            dt=1.0,
        )

        rng2 = random.Random(999)
        result2 = pool.execute_policy(
            component_id=BUILTIN_SEEK_NEAREST_FOOD_ID,
            observation=observation,
            rng=rng2,
            dt=1.0,
        )

        # Should produce identical results
        assert result1.success == result2.success
        assert result1.output == result2.output

    def test_invalid_component_id_fails_gracefully(self):
        """Executing non-existent policy should fail gracefully."""
        pool = create_default_genome_code_pool()

        observation = {"position": {"x": 0.0, "y": 0.0}}
        rng = random.Random(111)

        result = pool.execute_policy(
            component_id="non_existent_policy_id",
            observation=observation,
            rng=rng,
            dt=1.0,
        )

        # Should fail gracefully
        assert result.success is False
        assert result.error_message is not None
        assert "not found" in result.error_message.lower()


class TestGenomePolicySetOperations:
    """Test genetic operations on policy sets."""

    def test_mutation_can_swap_policies(self):
        """Mutation should be able to swap between different policies."""
        pool = create_default_genome_code_pool()
        rng = random.Random(222)

        # Start with one policy
        policy_set = GenomePolicySet()
        policy_set.set_policy("movement_policy", BUILTIN_SEEK_NEAREST_FOOD_ID)

        # Mutate multiple times - should eventually swap
        original_id = policy_set.get_component_id("movement_policy")
        swapped = False

        for _ in range(50):  # Try many times to ensure mutation happens
            mutated = pool.mutate_policy_set(policy_set, rng, mutation_rate=0.5)
            new_id = mutated.get_component_id("movement_policy")
            if new_id != original_id and new_id is not None:
                swapped = True
                break

        assert swapped, "Mutation should eventually swap policies"

    def test_crossover_combines_parents(self):
        """Crossover should combine policies from both parents."""
        pool = create_default_genome_code_pool()
        rng = random.Random(333)

        # Parent 1: seek food
        parent1 = GenomePolicySet()
        parent1.set_policy("movement_policy", BUILTIN_SEEK_NEAREST_FOOD_ID)

        # Parent 2: flee threat
        parent2 = GenomePolicySet()
        parent2.set_policy("movement_policy", BUILTIN_FLEE_FROM_THREAT_ID)

        # Crossover
        offspring = pool.crossover_policy_sets(parent1, parent2, rng, weight1=0.5)

        # Offspring should have a valid movement policy from one parent
        offspring_policy = offspring.get_component_id("movement_policy")
        assert offspring_policy in [BUILTIN_SEEK_NEAREST_FOOD_ID, BUILTIN_FLEE_FROM_THREAT_ID]

    def test_multi_policy_genome(self):
        """Genome can hold both movement and soccer policies simultaneously."""
        pool = create_default_genome_code_pool()
        rng = random.Random(444)

        # Create policy set with both movement and soccer policies
        policy_set = GenomePolicySet()
        policy_set.set_policy("movement_policy", BUILTIN_SEEK_NEAREST_FOOD_ID)
        policy_set.set_policy("soccer_policy", BUILTIN_CHASE_BALL_SOCCER_ID)

        # Apply to a genome
        genome = Genome(rng=rng)
        apply_policy_set_to_behavioral(genome.behavioral, policy_set, rng)

        # Extract and verify both policies are present
        from core.genetics.code_policy_traits import extract_policy_set_from_behavioral

        extracted = extract_policy_set_from_behavioral(genome.behavioral)
        assert extracted.get_component_id("movement_policy") == BUILTIN_SEEK_NEAREST_FOOD_ID
        assert extracted.get_component_id("soccer_policy") == BUILTIN_CHASE_BALL_SOCCER_ID
