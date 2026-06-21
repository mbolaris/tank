"""Determinism tests for SoccerMatchRunner.

These specifically cover the GenomeCodePool execution path, which is the
canonical path used for evolution.
"""

import random


def test_match_runner_deterministic_with_code_pool():
    """Same seed + same genomes => identical fitness outputs."""
    from typing import cast

    from core.code_pool import GenomeCodePool
    from core.code_pool.pool import BUILTIN_CHASE_BALL_SOCCER_ID, chase_ball_soccer_policy
    from core.genetics import Genome
    from core.genetics.trait import GeneticTrait
    from core.minigames.soccer.match_runner import SoccerMatchRunner

    pool = GenomeCodePool()
    pool.register_builtin(BUILTIN_CHASE_BALL_SOCCER_ID, "soccer_policy", chase_ball_soccer_policy)

    def build_population(seed: int) -> list[Genome]:
        rng = random.Random(seed)
        population = [Genome.random(use_algorithm=False, rng=rng) for _ in range(4)]
        for genome in population:
            genome.behavioral.soccer_policy_id = GeneticTrait(
                cast(str | None, BUILTIN_CHASE_BALL_SOCCER_ID)
            )
        return population

    pop1 = build_population(42)
    pop2 = build_population(42)

    runner = SoccerMatchRunner(team_size=2, genome_code_pool=pool)

    _, results1 = runner.run_episode(genomes=pop1, seed=123, frames=200)
    _, results2 = runner.run_episode(genomes=pop2, seed=123, frames=200)

    out1 = sorted([(r.player_id, r.goals, r.fitness) for r in results1], key=lambda x: x[0])
    out2 = sorted([(r.player_id, r.goals, r.fitness) for r in results2], key=lambda x: x[0])

    assert out1 == out2


def test_match_runner_sensitive_to_seed():
    """Different seed => different outcomes/fitness results when noise is enabled."""
    from typing import cast

    from core.code_pool import GenomeCodePool
    from core.code_pool.pool import BUILTIN_CHASE_BALL_SOCCER_ID, chase_ball_soccer_policy
    from core.genetics import Genome
    from core.genetics.trait import GeneticTrait
    from core.minigames.soccer.match_runner import SoccerMatchRunner
    from core.minigames.soccer.params import RCSSParams

    pool = GenomeCodePool()
    pool.register_builtin(BUILTIN_CHASE_BALL_SOCCER_ID, "soccer_policy", chase_ball_soccer_policy)

    def build_population(seed: int) -> list[Genome]:
        rng = random.Random(seed)
        population = [Genome.random(use_algorithm=False, rng=rng) for _ in range(4)]
        for genome in population:
            genome.behavioral.soccer_policy_id = GeneticTrait(
                cast(str | None, BUILTIN_CHASE_BALL_SOCCER_ID)
            )
        return population

    pop = build_population(42)

    # Enable noise so that the seed affects the simulation physics and player trajectories
    noisy_params = RCSSParams(noise_enabled=True)
    runner = SoccerMatchRunner(team_size=2, params=noisy_params, genome_code_pool=pool)

    # Run with different seeds
    _, results1 = runner.run_episode(genomes=pop, seed=123, frames=200)
    _, results2 = runner.run_episode(genomes=pop, seed=456, frames=200)

    out1 = sorted([(r.player_id, r.goals, r.fitness) for r in results1], key=lambda x: x[0])
    out2 = sorted([(r.player_id, r.goals, r.fitness) for r in results2], key=lambda x: x[0])

    # They must not be exactly identical because seed influences player physics noise
    assert out1 != out2
