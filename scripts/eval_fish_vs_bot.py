"""Evaluate evolved fish soccer teams against the league's Bot Balanced team.

The soccer league (core/minigames/soccer/league_runtime.py) pits tank fish
against "Bot Balanced" - a team of genome-less BotEntity players that fall back
to ``default_policy_action`` (policy_adapter.py). Fish instead execute their
genome's ``soccer_policy_id`` builtin from the GenomeCodePool.

This script reproduces that matchup deterministically so we can measure whether
fish policies actually beat the bot team, and how evolved ``soccer_policy_params``
shift the result.

Usage:
    python scripts/eval_fish_vs_bot.py --seeds 8 --frames 3000
    python scripts/eval_fish_vs_bot.py --policy builtin_striker_soccer --params '{"intercept_lead": 4.0}'
    python scripts/eval_fish_vs_bot.py --evolve --generations 10   # hill-climb params vs bot
"""

from __future__ import annotations

import argparse
import json
import random as pyrandom
import sys
from dataclasses import dataclass
from typing import Any

from core.code_pool import create_default_genome_code_pool
from core.genetics import Genome
from core.genetics.trait import GeneticTrait
from core.minigames.soccer.match import SoccerMatch


class _FishStub:
    """Minimal fish-like entity carrying a genome (mirrors league Fish usage)."""

    _next_id = 1

    def __init__(self, genome: Genome):
        self.fish_id = _FishStub._next_id
        _FishStub._next_id += 1
        self.genome = genome
        self.energy = 1000.0


class _BotStub:
    """Genome-less entity: run_policy falls back to default_policy_action,
    exactly like the league's BotEntity (Bot Balanced players)."""

    _next_id = 100000

    def __init__(self) -> None:
        self.fish_id = _BotStub._next_id
        _BotStub._next_id += 1
        self.energy = 1000.0


@dataclass
class MatchResult:
    fish_goals: int
    bot_goals: int

    @property
    def outcome(self) -> str:
        if self.fish_goals > self.bot_goals:
            return "W"
        if self.fish_goals < self.bot_goals:
            return "L"
        return "D"


MIXED_TEAM_ID = "mixed"
_MIXED_ROTATION = (
    "builtin_defensive_soccer",
    "builtin_chase_ball_soccer",
    "builtin_striker_soccer",
)


def _make_fish_genomes(
    seed: int,
    team_size: int,
    policy_id: str,
    params: dict[str, float] | None,
) -> list[Genome]:
    rng = pyrandom.Random(seed)
    genomes = []
    for i in range(team_size):
        g = Genome.random(use_algorithm=False, rng=rng)
        pid = _MIXED_ROTATION[i % len(_MIXED_ROTATION)] if policy_id == MIXED_TEAM_ID else policy_id
        g.behavioral.soccer_policy_id = GeneticTrait(pid)
        g.behavioral.soccer_policy_params = GeneticTrait(dict(params) if params else {})
        genomes.append(g)
    return genomes


def play_match(
    genomes: list[Genome],
    pool: Any,
    seed: int,
    frames: int,
    fish_side: str,
) -> MatchResult:
    """Run one fish-vs-bot match; fish on `fish_side` ('left' or 'right')."""
    team_size = len(genomes)
    fish = [_FishStub(g) for g in genomes]
    bots = [_BotStub() for _ in range(team_size)]

    entities: list[Any] = fish + bots if fish_side == "left" else bots + fish

    match = SoccerMatch(
        match_id=f"eval_{seed}_{fish_side}",
        entities=entities,
        duration_frames=frames,
        code_source=pool,
        seed=seed,
    )
    while not match.game_over:
        match.step(num_steps=50)

    score = match._engine.score
    if fish_side == "left":
        return MatchResult(fish_goals=score["left"], bot_goals=score["right"])
    return MatchResult(fish_goals=score["right"], bot_goals=score["left"])


def evaluate(
    policy_id: str,
    params: dict[str, float] | None,
    seeds: list[int],
    frames: int,
    team_size: int,
    pool: Any,
    verbose: bool = True,
) -> dict[str, Any]:
    """Play each seed twice (fish left, fish right) to cancel side bias."""
    results: list[MatchResult] = []
    for seed in seeds:
        genomes = _make_fish_genomes(seed, team_size, policy_id, params)
        for side in ("left", "right"):
            r = play_match(genomes, pool, seed=seed, frames=frames, fish_side=side)
            results.append(r)
            if verbose:
                print(
                    f"  seed={seed} fish={side:<5} fish {r.fish_goals} - {r.bot_goals} bot  [{r.outcome}]",
                    file=sys.stderr,
                )

    wins = sum(1 for r in results if r.outcome == "W")
    draws = sum(1 for r in results if r.outcome == "D")
    losses = sum(1 for r in results if r.outcome == "L")
    gf = sum(r.fish_goals for r in results)
    ga = sum(r.bot_goals for r in results)
    return {
        "policy_id": policy_id,
        "params": params or {},
        "matches": len(results),
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "win_rate": wins / len(results) if results else 0.0,
        "points_rate": (3 * wins + draws) / (3 * len(results)) if results else 0.0,
        "goals_for": gf,
        "goals_against": ga,
        "goal_diff": gf - ga,
    }


def hill_climb_params(
    policy_id: str,
    start_params: dict[str, float],
    seeds: list[int],
    frames: int,
    team_size: int,
    pool: Any,
    generations: int,
    seed: int,
) -> dict[str, Any]:
    """Simple (1+1) evolution of soccer_policy_params against the bot team.

    Mirrors in-world mutation: Gaussian jitter on existing keys only.
    Fitness = (points_rate, goal_diff).
    """
    rng = pyrandom.Random(seed)

    def fitness(params: dict[str, float]) -> tuple[float, int, dict[str, Any]]:
        res = evaluate(policy_id, params, seeds, frames, team_size, pool, verbose=False)
        return (res["points_rate"], res["goal_diff"], res)

    best_params = dict(start_params)
    best_fit = fitness(best_params)
    print(
        f"gen 0: points_rate={best_fit[0]:.3f} goal_diff={best_fit[1]} params={best_params}",
        file=sys.stderr,
    )

    for gen in range(1, generations + 1):
        cand = {k: max(-10.0, min(10.0, v + rng.gauss(0, 0.35))) for k, v in best_params.items()}
        cand_fit = fitness(cand)
        if (cand_fit[0], cand_fit[1]) >= (best_fit[0], best_fit[1]):
            best_params, best_fit = cand, cand_fit
        print(
            f"gen {gen}: points_rate={best_fit[0]:.3f} goal_diff={best_fit[1]} params={best_params}",
            file=sys.stderr,
        )

    result = best_fit[2]
    result["evolved_params"] = best_params
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=5, help="Number of seeds (each played twice)")
    parser.add_argument("--seed-base", type=int, default=42)
    parser.add_argument("--frames", type=int, default=3000, help="Match length in cycles")
    parser.add_argument("--team-size", type=int, default=3)
    parser.add_argument("--policy", type=str, default=None, help="Single policy id to evaluate")
    parser.add_argument("--params", type=str, default=None, help="JSON dict of policy params")
    parser.add_argument("--evolve", action="store_true", help="Hill-climb params vs the bot team")
    parser.add_argument("--generations", type=int, default=10)
    args = parser.parse_args()

    pool = create_default_genome_code_pool()
    seeds = [args.seed_base + i for i in range(args.seeds)]
    params = json.loads(args.params) if args.params else None

    policies = [args.policy] if args.policy else pool.get_components_by_kind("soccer_policy")

    out: list[dict[str, Any]] = []
    for policy_id in policies:
        print(f"=== {policy_id} vs Bot Balanced ===", file=sys.stderr)
        if args.evolve:
            base = params or {}
            if not base:
                # Start from the policy's registered default params if any
                from core.code_pool.pool import default_soccer_policy_params

                base = default_soccer_policy_params(policy_id)
            res = hill_climb_params(
                policy_id,
                base,
                seeds,
                args.frames,
                args.team_size,
                pool,
                generations=args.generations,
                seed=args.seed_base,
            )
        else:
            res = evaluate(policy_id, params, seeds, args.frames, args.team_size, pool)
        out.append(res)
        print(
            f"  -> W{res['wins']} D{res['draws']} L{res['losses']}  "
            f"GF {res['goals_for']} GA {res['goals_against']}  "
            f"win_rate={res['win_rate']:.2f}",
            file=sys.stderr,
        )

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
