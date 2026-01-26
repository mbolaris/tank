"""Match runner for soccer evolution experiments and benchmarks.

This module provides a thin wrapper around the RCSS-Lite engine for running
evaluation episodes. It's designed for training/benchmarking, not interactive play.

Key features:
- Deterministic seeded episodes with forked RNG per player
- Batch stepping (no observation building overhead)
- Fitness extraction from engine stats
- Uses GenomeCodePool.execute_policy() for safe policy execution
"""

from __future__ import annotations

import math
import random as pyrandom
from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.code_pool.safety import fork_rng
from core.minigames.soccer.engine import RCSSLiteEngine, RCSSVector
from core.minigames.soccer.params import SOCCER_CANONICAL_PARAMS, RCSSParams
from core.minigames.soccer.participant import SoccerParticipant
from core.minigames.soccer.rewards import calculate_shaped_bonuses
from core.minigames.soccer.telemetry_collector import SoccerTelemetryCollector

if TYPE_CHECKING:
    from core.code_pool import GenomeCodePool
    from core.genetics import Genome


@dataclass
class PlayerStats:
    """Per-player statistics for fitness calculation."""

    player_id: str
    team: str
    goals: int = 0
    assists: int = 0
    possessions: int = 0
    kicks: int = 0
    total_reward: float = 0.0

    def fitness(self, goal_weight: float = 100.0, possession_weight: float = 0.1) -> float:
        """Calculate fitness from stats, incorporating shaped reward."""
        return (
            self.goals * goal_weight
            + self.assists * 50.0
            + self.possessions * possession_weight
            + self.total_reward
        )


@dataclass
class EpisodeResult:
    """Result of a single evaluation episode."""

    seed: int
    frames: int
    score_left: int
    score_right: int
    player_stats: dict[str, PlayerStats]
    winner: str | None  # "left", "right", or None (draw)


@dataclass
class AgentResult:
    """Results for a single agent after an episode."""

    player_id: str
    team: str
    goals: int
    fitness: float
    genome: Genome


class SoccerMatchRunner:
    """Runs soccer evaluation episodes using RCSS-Lite engine.

    This is optimized for training: minimal overhead, no rendering,
    just physics and fitness extraction.
    """

    def __init__(
        self,
        team_size: int = 3,
        params: RCSSParams | None = None,
        genome_code_pool: GenomeCodePool | None = None,
    ):
        """Initialize the match runner.

        Args:
            team_size: Number of players per team
            params: RCSS physics parameters (uses SOCCER_CANONICAL_PARAMS if None)
            genome_code_pool: Pool for policy lookup
        """
        self.team_size = team_size
        self._params = params or SOCCER_CANONICAL_PARAMS
        self._genome_code_pool = genome_code_pool
        self._engine: RCSSLiteEngine | None = None

    def run_episode(
        self,
        genomes: list[Genome],
        seed: int,
        frames: int = 300,
        goal_weight: float = 100.0,
    ) -> tuple[EpisodeResult, list[AgentResult]]:
        """Run a single evaluation episode.

        Args:
            genomes: List of genomes to evaluate (split into teams)
            seed: Random seed for determinism
            frames: Number of simulation cycles to run
            goal_weight: Weight for goals in fitness calculation

        Returns:
            Tuple of (EpisodeResult, list of AgentResult)
        """
        # Ensure even team sizes
        actual_team_size = min(self.team_size, len(genomes) // 2)

        # Initialize engine with seed
        self._engine = RCSSLiteEngine(params=self._params, seed=seed)

        # Set up players with formations
        player_ids: list[str] = []
        genome_by_player: dict[str, Genome] = {}

        half_length = self._params.field_length / 2

        for i in range(actual_team_size):
            # Left team
            left_id = f"left_{i + 1}"
            x = -half_length / 2 + (i % 4) * 8 - 10
            y = (i // 4 - actual_team_size // 8) * 12
            self._engine.add_player(left_id, "left", RCSSVector(x, y), body_angle=0.0)
            player_ids.append(left_id)
            if i < len(genomes):
                genome_by_player[left_id] = genomes[i]

            # Right team
            right_id = f"right_{i + 1}"
            x = half_length / 2 - (i % 4) * 8 + 10
            y = (i // 4 - actual_team_size // 8) * 12
            self._engine.add_player(right_id, "right", RCSSVector(x, y), body_angle=math.pi)
            player_ids.append(right_id)
            if actual_team_size + i < len(genomes):
                genome_by_player[right_id] = genomes[actual_team_size + i]

        # Sort for deterministic iteration.
        player_ids.sort()

        participants: list[SoccerParticipant] = []
        for pid in player_ids:
            player = self._engine.get_player(pid)
            participants.append(
                SoccerParticipant(participant_id=pid, team=player.team if player else "left")
            )

        telemetry_collector = SoccerTelemetryCollector(
            engine=self._engine,
            params=self._params,
            participants=participants,
        )

        # Initialize per-player stats
        player_stats: dict[str, PlayerStats] = {}
        for pid in player_ids:
            player = self._engine.get_player(pid)
            player_stats[pid] = PlayerStats(player_id=pid, team=player.team if player else "left")

        # Create deterministic RNG from seed for policy execution
        episode_rng = pyrandom.Random(seed)

        # Run episode
        for _ in range(frames):
            # Queue autopolicy commands with forked RNG
            self._queue_autopolicy_commands(player_stats, genome_by_player, episode_rng)

            # Step engine
            step_result = self._engine.step_cycle()

            telemetry_collector.step()

            # Track goals and assists from engine events
            for event in step_result.get("events", []):
                if event.get("type") == "goal":
                    scorer_id = event.get("scorer_id")
                    assist_id = event.get("assist_id")

                    # Increment goal for scorer
                    if scorer_id and scorer_id in player_stats:
                        player_stats[scorer_id].goals += 1

                    # Increment assist for assister
                    if assist_id and assist_id in player_stats:
                        player_stats[assist_id].assists += 1

        # Fold telemetry-derived stats and shaped bonuses into fitness inputs.
        final_telemetry = telemetry_collector.get_telemetry()
        shaped_bonuses = calculate_shaped_bonuses(final_telemetry)
        for pid in player_ids:
            stats = player_stats[pid]
            player_tel = final_telemetry.players.get(pid)
            if player_tel:
                stats.kicks = player_tel.kicks
                stats.possessions = player_tel.possession_frames
            stats.total_reward += shaped_bonuses.get(pid, 0.0)

        # Extract final score
        score = self._engine.score
        score_left = score.get("left", 0)
        score_right = score.get("right", 0)

        # Determine winner
        if score_left > score_right:
            winner = "left"
        elif score_right > score_left:
            winner = "right"
        else:
            winner = None

        # Build results
        episode_result = EpisodeResult(
            seed=seed,
            frames=frames,
            score_left=score_left,
            score_right=score_right,
            player_stats=player_stats,
            winner=winner,
        )

        agent_results: list[AgentResult] = []
        for pid in player_ids:
            stats = player_stats[pid]
            genome = genome_by_player.get(pid)
            if genome is None:
                rng = pyrandom.Random(seed)
                from core.genetics import Genome as GenomeClass

                genome = GenomeClass.random(use_algorithm=False, rng=rng)

            fitness = stats.fitness(goal_weight=goal_weight)

            # Award team bonus for winning
            if winner == stats.team:
                fitness += 50.0  # Winning team bonus

            agent_results.append(
                AgentResult(
                    player_id=pid,
                    team=stats.team,
                    goals=stats.goals,
                    fitness=fitness,
                    genome=genome,
                )
            )

        return episode_result, agent_results

    def _queue_autopolicy_commands(
        self,
        player_stats: dict[str, PlayerStats],
        genome_by_player: dict[str, Genome],
        episode_rng: pyrandom.Random,
    ) -> None:
        """Queue autopolicy commands for all players.

        Args:
            player_stats: Per-player stats for tracking
            genome_by_player: Mapping of player ID to genome
            episode_rng: Episode-level RNG (forked per player for determinism)
        """
        if self._engine is None:
            return

        from core.minigames.soccer.policy_adapter import (
            action_to_command,
            build_observation,
            run_policy,
        )

        for pid in sorted(player_stats):
            # Build observation
            obs = build_observation(self._engine, pid, self._params)
            if not obs:
                continue

            # Get genome
            genome = genome_by_player.get(pid)

            # Fork RNG for this player's policy execution
            player_rng = fork_rng(episode_rng)

            # Run policy with forked RNG for determinism
            action = run_policy(
                code_source=self._genome_code_pool,
                genome=genome,
                observation=obs,
                rng=player_rng,
                dt=0.1,  # 100ms RCSS cycle
            )

            # Convert to command
            cmd = action_to_command(action, self._params)

            if cmd:
                self._engine.queue_command(pid, cmd)
