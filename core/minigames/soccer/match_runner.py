"""Match runner for soccer evolution experiments and benchmarks.

This module provides a thin wrapper around the RCSS-Lite engine for running
evaluation episodes. It's designed for training/benchmarking, not interactive play.

Key features:
- Deterministic seeded episodes
- Batch stepping (no observation building overhead)
- Fitness extraction from engine stats
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from core.minigames.soccer.engine import RCSSCommand, RCSSLiteEngine, RCSSVector
from core.minigames.soccer.params import RCSSParams

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
    winner: Optional[str]  # "left", "right", or None (draw)


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
        params: Optional[RCSSParams] = None,
        genome_code_pool: Optional[GenomeCodePool] = None,
    ):
        """Initialize the match runner.

        Args:
            team_size: Number of players per team
            params: RCSS physics parameters (uses defaults if None)
            genome_code_pool: Pool for policy lookup
        """
        self.team_size = team_size
        self._params = params or RCSSParams(
            field_length=100.0,
            field_width=60.0,
        )
        self._genome_code_pool = genome_code_pool
        self._engine: Optional[RCSSLiteEngine] = None

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

        # Initialize per-player stats
        player_stats: dict[str, PlayerStats] = {}
        for pid in player_ids:
            player = self._engine.get_player(pid)
            player_stats[pid] = PlayerStats(player_id=pid, team=player.team if player else "left")

        # Run episode
        for frame in range(frames):
            # Queue autopolicy commands
            self._queue_autopolicy_commands(player_stats)

            # Step engine
            step_result = self._engine.step_cycle()

            # Track goals (events tracked by engine)
            for event in step_result.get("events", []):
                if event.get("type") == "goal":
                    # Could track scoring player or award assists here
                    pass

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
                rng = random.Random(seed)
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

    def _queue_autopolicy_commands(self, player_stats: dict[str, PlayerStats]) -> None:
        """Queue autopolicy commands for all players."""
        if self._engine is None:
            return

        ball = self._engine.get_ball()
        ball_pos = ball.position

        for pid, stats in player_stats.items():
            player = self._engine.get_player(pid)
            if player is None:
                continue

            # Simple chase-ball autopolicy
            dx = ball_pos.x - player.position.x
            dy = ball_pos.y - player.position.y
            dist_to_ball = math.sqrt(dx * dx + dy * dy)

            # Angle to ball relative to player facing
            angle_to_ball = math.atan2(dy, dx)
            relative_angle = angle_to_ball - player.body_angle

            # Normalize to [-pi, pi]
            while relative_angle > math.pi:
                relative_angle -= 2 * math.pi
            while relative_angle < -math.pi:
                relative_angle += 2 * math.pi

            # Track possession
            if dist_to_ball < self._params.kickable_margin + self._params.ball_size:
                stats.possessions += 1

            # Determine team's goal direction
            team = player.team
            goal_x = (
                self._params.field_length / 2 if team == "left" else -self._params.field_length / 2
            )

            if dist_to_ball < self._params.kickable_margin + self._params.ball_size:
                # Can kick - kick toward opponent's goal
                kick_dir = math.atan2(-player.position.y * 0.1, goal_x - ball_pos.x)
                kick_dir_rel = math.degrees(kick_dir - player.body_angle)
                self._engine.queue_command(pid, RCSSCommand.kick(80, kick_dir_rel))
                stats.kicks += 1
            elif abs(relative_angle) > 0.2:
                # Turn toward ball
                turn_moment = math.degrees(relative_angle) * 0.5
                turn_moment = max(-180, min(180, turn_moment))
                self._engine.queue_command(pid, RCSSCommand.turn(turn_moment))
            else:
                # Dash toward ball
                power = min(100, dist_to_ball * 5)
                self._engine.queue_command(pid, RCSSCommand.dash(power, 0))
