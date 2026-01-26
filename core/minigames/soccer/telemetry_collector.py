"""Unified telemetry collector for soccer matches.

This module provides a single source of truth for collecting soccer telemetry
during matches. It's used by both SoccerMatch and quick_eval to ensure
consistent telemetry computation without code duplication.

Key features:
- Deterministic: no random iteration, sorted player IDs
- Tracks per-player and per-team statistics
- Computes touches, possession, ball progress, shots, distance run
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Sequence

from core.minigames.soccer.types import PlayerTelemetry, SoccerTelemetry, TeamTelemetry

if TYPE_CHECKING:
    from core.minigames.soccer.engine import RCSSLiteEngine
    from core.minigames.soccer.params import RCSSParams
    from core.minigames.soccer.participant import SoccerParticipant


class SoccerTelemetryCollector:
    """Collects telemetry for soccer matches in a deterministic manner.

    This collector maintains internal state to track:
    - Player distance traveled
    - Ball touches per player/team
    - Possession cycles per team
    - Ball progress (movement toward goals) per team
    - Shots and shots on target per team
    """

    def __init__(
        self,
        engine: RCSSLiteEngine,
        params: RCSSParams,
        participants: Sequence[SoccerParticipant],
    ):
        """Initialize telemetry collector.

        Args:
            engine: The RCSS-Lite engine to monitor
            params: RCSS physics parameters (for field dimensions)
            participants: List of participants in the match
        """
        self._engine = engine
        self._params = params

        # Initialize telemetry structures
        self.telemetry = SoccerTelemetry()
        for team in ["left", "right"]:
            self.telemetry.teams[team] = TeamTelemetry(team=team)

        # Initialize player telemetry (sorted for determinism)
        self._player_ids = sorted([p.participant_id for p in participants])
        self._player_teams: dict[str, str] = {}
        for p in participants:
            self.telemetry.players[p.participant_id] = PlayerTelemetry(
                player_id=p.participant_id, team=p.team
            )
            self._player_teams[p.participant_id] = p.team

        # Track previous positions for distance calculation
        self._prev_positions: dict[str, tuple[float, float]] = {}
        for player_id in self._player_ids:
            player = self._engine.get_player(player_id)
            if player:
                self._prev_positions[player_id] = (player.position.x, player.position.y)

        # Track ball position for progress calculation
        self._prev_ball_x = self._engine.get_ball().position.x

        # Track last touch for detecting new touches
        self._last_touch_id: str | None = None

        # Cycle counter
        self._cycle_count = 0

    def step(self) -> None:
        """Update telemetry for one simulation cycle.

        This should be called after each engine.step_cycle().
        Uses deterministic iteration (sorted player IDs) to ensure reproducibility.
        """
        self._cycle_count += 1

        # Track player distance traveled (deterministic: sorted IDs)
        for player_id in self._player_ids:
            player = self._engine.get_player(player_id)
            if player and player_id in self._prev_positions:
                px, py = self._prev_positions[player_id]
                dx = player.position.x - px
                dy = player.position.y - py
                dist = math.sqrt(dx * dx + dy * dy)
                self.telemetry.players[player_id].distance_run += dist
                self._prev_positions[player_id] = (player.position.x, player.position.y)

        # Track ball progress
        ball = self._engine.get_ball()
        ball_dx = ball.position.x - self._prev_ball_x

        # Attribute ball progress to team with possession
        touch_info = self._engine.last_touch_info()
        current_touch_id = touch_info["player_id"]
        if current_touch_id:
            touch_player = self._engine.get_player(current_touch_id)
            if touch_player:
                team = touch_player.team
                # Left team wants ball to go right (+x), right team wants left (-x)
                progress = ball_dx if team == "left" else -ball_dx
                self.telemetry.teams[team].ball_progress += progress

        self._prev_ball_x = ball.position.x

        # Track touches via last_touch_player_id
        if current_touch_id and current_touch_id != self._last_touch_id:
            player = self._engine.get_player(current_touch_id)
            if player:
                team = player.team
                self.telemetry.teams[team].touches += 1
                self.telemetry.players[current_touch_id].touches += 1
                self.telemetry.players[current_touch_id].kicks += 1

                # Check if this is a shot (kick toward opponent goal)
                ball_vx = ball.velocity.x
                is_shot = (team == "left" and ball_vx > 0.5) or (team == "right" and ball_vx < -0.5)
                if is_shot:
                    self.telemetry.teams[team].shots += 1

                    # Shot on target = ball trajectory intersects goal
                    half_length = self._params.field_length / 2
                    goal_x = half_length if team == "left" else -half_length
                    if abs(ball_vx) > 0.01:
                        t_to_goal = (goal_x - ball.position.x) / ball_vx
                        if t_to_goal > 0:
                            predicted_y = ball.position.y + ball.velocity.y * t_to_goal
                            if abs(predicted_y) < self._params.goal_width / 2:
                                self.telemetry.teams[team].shots_on_target += 1

            self._last_touch_id = current_touch_id

        # Track possession
        if current_touch_id:
            player = self._engine.get_player(current_touch_id)
            if player:
                self.telemetry.teams[player.team].possession_frames += 1

        # Update total cycles
        self.telemetry.total_cycles = self._cycle_count

    def get_telemetry(self) -> SoccerTelemetry:
        """Get the current telemetry state.

        Returns:
            SoccerTelemetry with all accumulated statistics
        """
        return self.telemetry
