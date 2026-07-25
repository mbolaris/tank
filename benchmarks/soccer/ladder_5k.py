"""Soccer Ladder Benchmark (5k frames per match).

Measures the absolute team skill of the evolvable soccer substrate (the builtin
soccer policy at neutral, all-zero params - what founder fish receive) against a
frozen ladder of reference teams, from a do-nothing floor to a role-playing
formation. The training benchmarks score one evolving population playing
*itself*, so their score is relative; because these rungs never change, goal
difference against each rung is an absolute, longitudinally comparable measure:
improving the substrate moves it, re-tuning ecosystem config does not.

Ladder rungs (weak to strong by design intent, see
``core/minigames/soccer/reference_teams.py``):

    L0 stationary_v1  - never moves (skill floor)
    L1 random_walk_v1 - random turns and dashes, ignores the ball
    L2 chase_shoot_v1 - frozen snapshot of the neutral substrate chaser, so
                        "goal diff vs L2" reads as "improvement since freeze"
    L3 formation_v1   - defender + chaser + striker playing role geometry

Every rung is played twice per seed with the sides swapped on the same engine
seed, which cancels the left/right formation and kickoff advantage, and
aggregated over ``n_seeds`` consecutive seeds. Score is the mean goal difference
per 5k-frame match across rungs (higher is better; 0 vs a rung means the
substrate is level with that ruler).
"""

from __future__ import annotations

import math
import random
import sys
import time
from typing import Any

from core.code_pool import create_default_genome_code_pool, default_soccer_policy_params
from core.code_pool.genome_code_pool import GenomeCodePool
from core.genetics import Genome
from core.genetics.trait import GeneticTrait
from core.minigames.soccer import SoccerMatchRunner
from core.minigames.soccer.reference_teams import (
    REFERENCE_LADDER,
    ReferenceTeam,
    register_reference_policies,
)
from core.skill import RungResult, SkillLadderSummary, ladder_position_index

SKILL_DOMAIN = "soccer"
SKILL_METRIC_NAME = "goal_diff_per_match"

BENCHMARK_ID = "soccer/ladder_5k"
FRAMES = 5000
DEFAULT_N_SEEDS = 3
TEAM_SIZE = 3
EXPECTED_RUNTIME_SECONDS = 45

# 95% normal-approximation multiplier. With n = 2 * n_seeds matches per rung the
# interval is indicative, not a strong significance claim - reported so readers
# can see the spread rather than trust a point estimate.
_CI_Z = 1.96

# Effective configuration captured by the champion config hash
# (core/solutions/config_hash.py). Anything that changes the score belongs here.
CONFIG: dict[str, Any] = {
    "frames": FRAMES,
    "n_seeds": DEFAULT_N_SEEDS,
    "team_size": TEAM_SIZE,
    "hero": "soccer_policy_neutral_default",
    "ladder_rungs": [team.rung_id for team in REFERENCE_LADDER],
    "score_mode": "mean goal difference per match across rungs",
}


def _hero_genomes(pool: GenomeCodePool, count: int, rng: random.Random) -> list[Genome]:
    """Build the evaluated substrate: the default soccer policy at neutral params.

    Neutral (all-zero) params are what the policy's hand-tuned baseline reduces
    to, and the founding population's jitter is drawn around them. Pinning the
    hero here - instead of jittering like ``training_5k`` - keeps the ladder
    measuring the substrate itself rather than one sampled founder population.
    """
    default_id = pool.get_default("soccer_policy")
    genomes: list[Genome] = []
    for _ in range(count):
        genome = Genome.random(use_algorithm=False, rng=rng)
        genome.behavioral.soccer_policy_id = GeneticTrait(default_id)
        genome.behavioral.soccer_policy_params = GeneticTrait(
            default_soccer_policy_params(default_id)
        )
        genomes.append(genome)
    return genomes


def _reference_genomes(team: ReferenceTeam, count: int, rng: random.Random) -> list[Genome]:
    """Build one frozen reference team, binding each slot to its ruler policy.

    Ruler genomes carry no ``soccer_policy_params`` at all, so no evolvable
    parameters reach the ruler even if the substrate's param space changes.
    """
    genomes: list[Genome] = []
    for slot in range(count):
        genome = Genome.random(use_algorithm=False, rng=rng)
        genome.behavioral.soccer_policy_id = GeneticTrait(team.policy_id_for_slot(slot))
        genome.behavioral.soccer_policy_params = GeneticTrait(None)
        genomes.append(genome)
    return genomes


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _ci_95(values: list[float]) -> tuple[float, float]:
    """Normal-approximation 95% CI on the mean of ``values``."""
    mean = _mean(values)
    if len(values) < 2:
        return (mean, mean)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    margin = _CI_Z * math.sqrt(variance / len(values))
    return (mean - margin, mean + margin)


def _play_match(
    runner: SoccerMatchRunner,
    hero: list[Genome],
    reference: list[Genome],
    *,
    seed: int,
    frames: int,
    hero_on_left: bool,
) -> dict[str, Any]:
    """Play one match and return the result from the hero's perspective."""
    genomes = hero + reference if hero_on_left else reference + hero
    episode, _agents = runner.run_episode(genomes=genomes, seed=seed, frames=frames)

    hero_goals = episode.score_left if hero_on_left else episode.score_right
    reference_goals = episode.score_right if hero_on_left else episode.score_left
    return {
        "seed": seed,
        "hero_side": "left" if hero_on_left else "right",
        "hero_goals": hero_goals,
        "reference_goals": reference_goals,
        "goal_diff": hero_goals - reference_goals,
    }


def run(
    seed: int,
    *,
    n_seeds: int = DEFAULT_N_SEEDS,
    frames: int = FRAMES,
    team_size: int = TEAM_SIZE,
) -> dict[str, Any]:
    """Run the benchmark deterministically.

    Args:
        seed: Base seed; the ladder aggregates over ``seed .. seed + n_seeds - 1``
        n_seeds: Number of consecutive seeds to aggregate over
        frames: Frames per match
        team_size: Players per team

    Returns:
        Result dictionary with score, per-rung metrics, and skill metadata
    """
    start_time = time.time()

    pool = create_default_genome_code_pool()
    register_reference_policies(pool)
    runner = SoccerMatchRunner(team_size=team_size, genome_code_pool=pool)

    seeds = [seed + offset for offset in range(n_seeds)]

    per_rung: list[dict[str, Any]] = []
    rung_results: list[RungResult] = []
    rung_scores: dict[str, float] = {}

    for team in REFERENCE_LADDER:
        print(
            f"  Rung {team.rung} ({team.rung_id}): "
            f"{len(seeds)} seeds x 2 sides x {frames} frames...",
            file=sys.stderr,
        )

        matches: list[dict[str, Any]] = []
        for match_seed in seeds:
            # One genome RNG per seed, so a rung's populations depend only on the
            # seed - never on how many rungs ran before it.
            genome_rng = random.Random(match_seed)
            hero = _hero_genomes(pool, team_size, genome_rng)
            reference = _reference_genomes(team, team_size, genome_rng)

            for hero_on_left in (True, False):
                matches.append(
                    _play_match(
                        runner,
                        hero,
                        reference,
                        seed=match_seed,
                        frames=frames,
                        hero_on_left=hero_on_left,
                    )
                )

        diffs = [float(match["goal_diff"]) for match in matches]
        mean_diff = _mean(diffs)
        ci_low, ci_high = _ci_95(diffs)
        # "Beaten" = the substrate outscores the ruler on average. The CI is
        # reported alongside so a thin margin is visible as a thin margin.
        beaten = mean_diff > 0.0

        rung_scores[team.rung_id] = mean_diff
        per_rung.append(
            {
                "rung": team.rung,
                "rung_id": team.rung_id,
                "description": team.description,
                "goal_diff_mean": mean_diff,
                "goal_diff_ci_95": [ci_low, ci_high],
                "hero_goals_mean": _mean([float(m["hero_goals"]) for m in matches]),
                "reference_goals_mean": _mean([float(m["reference_goals"]) for m in matches]),
                "matches_played": len(matches),
                "significant": ci_low > 0.0 or ci_high < 0.0,
                "beaten": beaten,
                "matches": matches,
            }
        )
        rung_results.append(
            RungResult(
                rung=team.rung,
                rung_id=team.rung_id,
                metric=mean_diff,
                ci_95=(ci_low, ci_high),
                beaten=beaten,
                detail={
                    "matches_played": len(matches),
                    "hero_goals_mean": _mean([float(m["hero_goals"]) for m in matches]),
                    "reference_goals_mean": _mean([float(m["reference_goals"]) for m in matches]),
                },
            )
        )

    score = _mean(list(rung_scores.values()))
    # The scalar score averages every rung (matching the poker ladder), so the
    # trivial rungs dominate it in absolute size. The competitive mean below is
    # the part that actually moves when the substrate plays better football.
    competitive = [
        entry["goal_diff_mean"] for entry in per_rung if entry["rung"] not in ("L0", "L1")
    ]
    runtime = time.time() - start_time

    skill = SkillLadderSummary(
        domain=SKILL_DOMAIN,
        benchmark_id=BENCHMARK_ID,
        metric_name=SKILL_METRIC_NAME,
        skill_index=ladder_position_index(tuple(rung_results)),
        rungs=tuple(rung_results),
        notes=(
            "Ladder-position index: 100 = beats every current rung (ceiling "
            "saturated, add a taller rung). L3 formation_v1 is the strongest "
            "scripted ruler, not an upper bound on soccer play; rung order is "
            "design intent, and measured strength may be non-monotonic."
        ),
    )

    return {
        "benchmark_id": BENCHMARK_ID,
        "seed": seed,
        "score": score,
        "score_breakdown": dict(rung_scores),
        "runtime_seconds": runtime,
        "metadata": {
            "hero": "soccer_policy_neutral_default",
            "ladder_rungs": [team.rung_id for team in REFERENCE_LADDER],
            "rungs_beaten": skill.rungs_beaten,
            "total_rungs": skill.total_rungs,
            "frames": frames,
            "team_size": team_size,
            "n_seeds": n_seeds,
            "seeds": seeds,
            "matches_per_rung": 2 * len(seeds),
            "score_mode": "mean goal difference per match across ladder rungs (side-swapped)",
            "competitive_goal_diff_mean": _mean(competitive),
            "competitive_rungs_note": (
                "Mean over the non-trivial rungs (L2+). The headline score "
                "includes L0/L1, whose large margins any working substrate "
                "earns; judge real progress on the ladder index and this value."
            ),
            "vs_top_rung_goal_diff": rung_scores.get(REFERENCE_LADDER[-1].rung_id, 0.0),
            "per_rung_results": per_rung,
            "skill": skill.to_dict(),
        },
    }


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--verify-determinism", action="store_true")
    args = parser.parse_args()

    if args.verify_determinism:
        res1 = run(args.seed)
        res2 = run(args.seed)
        score_diff = abs(res1["score"] - res2["score"])
        if score_diff > 1e-9:
            print(f"DETERMINISM FAILED: {res1['score']} != {res2['score']}", file=sys.stderr)
            sys.exit(1)
        print(f"DETERMINISM PASSED: {res1['score']}")
    else:
        result = run(args.seed)
        print(json.dumps(result, indent=2))
