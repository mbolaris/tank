"""Quick deterministic soccer evaluation using RCSS-Lite engine.

This module provides fast, deterministic soccer episode evaluation for:
- Evolution fitness evaluation
- CI determinism tests
- Quick benchmarking

Uses RCSSLiteEngine directly without Fish/Match overhead.
This is the canonical evaluation path for soccer simulations.

Example:
    >>> config = QuickEvalConfig(seed=42, max_cycles=200)
    >>> result = run_quick_eval(config)
    >>> print(result.score, result.episode_hash)
    >>> print(result.telemetry.teams["left"].ball_progress)
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Any

from core.minigames.soccer.engine import RCSSLiteEngine, RCSSVector
from core.minigames.soccer.params import DEFAULT_RCSS_PARAMS, RCSSParams
from core.minigames.soccer.policy_adapter import (
    action_to_command,
    build_observation,
    default_policy_action,
)
from core.minigames.soccer.types import (
    PlayerTelemetry,
    SoccerTelemetry,
    TeamTelemetry,
)


@dataclass
class QuickEvalConfig:
    """Configuration for a quick deterministic soccer episode.

    Attributes:
        seed: Random seed for determinism (affects noise, kick randomness)
        max_cycles: Number of simulation cycles to run
        params: RCSS physics parameters (noise_enabled controls seed sensitivity)
        initial_ball: Optional (x, y) starting position for ball
        initial_players: Dict mapping team ("left"/"right") to list of (x, y) positions
    """

    seed: int
    max_cycles: int = 200
    params: RCSSParams = field(default_factory=lambda: DEFAULT_RCSS_PARAMS)
    initial_ball: tuple[float, float] | None = None
    initial_players: dict[str, list[tuple[float, float]]] = field(default_factory=dict)


@dataclass
class QuickEvalResult:
    """Result of a quick soccer evaluation.

    Attributes:
        seed: The seed used for this episode
        cycles: Number of cycles actually run
        score: Dict mapping team to goals scored
        touches: Dict mapping team to number of ball touches
        possession_cycles: Dict mapping team to cycles with possession
        episode_hash: SHA256 hash of final state for determinism verification
        telemetry: Detailed per-team and per-player statistics
    """

    seed: int
    cycles: int
    score: dict[str, int]
    touches: dict[str, int]
    possession_cycles: dict[str, int]
    episode_hash: str
    telemetry: SoccerTelemetry


def run_quick_eval(config: QuickEvalConfig) -> QuickEvalResult:
    """Run a deterministic soccer episode using RCSS-Lite engine.

    This is the canonical evaluation path for soccer. It uses the same
    physics engine as SoccerMatch but without Fish entity overhead.

    Args:
        config: Episode configuration

    Returns:
        QuickEvalResult with score, statistics, telemetry, and determinism hash
    """
    # Initialize engine with seed
    engine = RCSSLiteEngine(params=config.params, seed=config.seed)

    # Setup players and track team membership
    player_ids: list[str] = []
    player_teams: dict[str, str] = {}
    for team, positions in config.initial_players.items():
        for i, (x, y) in enumerate(positions):
            player_id = f"{team}_{i + 1}"
            # Face toward opponent goal
            body_angle = 0.0 if team == "left" else 3.14159
            engine.add_player(player_id, team, RCSSVector(x, y), body_angle=body_angle)
            player_ids.append(player_id)
            player_teams[player_id] = team

    # Sort for deterministic iteration
    player_ids.sort()

    # Setup ball
    if config.initial_ball:
        engine.set_ball_position(config.initial_ball[0], config.initial_ball[1])
    else:
        engine.set_ball_position(0.0, 0.0)

    # Initialize telemetry
    telemetry = SoccerTelemetry()
    for team in ["left", "right"]:
        telemetry.teams[team] = TeamTelemetry(team=team)
    for player_id, team in player_teams.items():
        telemetry.players[player_id] = PlayerTelemetry(player_id=player_id, team=team)

    # Track previous positions for distance calculation
    prev_positions: dict[str, tuple[float, float]] = {}
    for player_id in player_ids:
        player = engine.get_player(player_id)
        if player:
            prev_positions[player_id] = (player.position.x, player.position.y)

    # Track ball position for progress calculation
    prev_ball_x = engine.get_ball().position.x

    # Statistics tracking (legacy, kept for compatibility)
    touches: dict[str, int] = {"left": 0, "right": 0}
    possession_cycles: dict[str, int] = {"left": 0, "right": 0}
    event_log: list[tuple[int, str, str, str | None]] = []
    last_touch_id: str | None = None

    # Goal line positions
    half_length = config.params.field_length / 2

    # Simulation loop
    for cycle in range(config.max_cycles):
        # Queue commands for each player using default policy
        for player_id in player_ids:
            obs = build_observation(engine, player_id, config.params)
            if not obs:
                continue

            action = default_policy_action(obs)
            cmd = action_to_command(action, config.params)
            if cmd:
                engine.queue_command(player_id, cmd)

        # Step engine
        step_result = engine.step_cycle()

        # Track player distance traveled
        for player_id in player_ids:
            player = engine.get_player(player_id)
            if player and player_id in prev_positions:
                px, py = prev_positions[player_id]
                dx = player.position.x - px
                dy = player.position.y - py
                dist = math.sqrt(dx * dx + dy * dy)
                telemetry.players[player_id].distance_run += dist
                prev_positions[player_id] = (player.position.x, player.position.y)

        # Track ball progress
        ball = engine.get_ball()
        ball_dx = ball.position.x - prev_ball_x

        # Attribute ball progress to team with possession
        current_touch_id = engine._last_touch_player_id
        if current_touch_id:
            touch_player = engine.get_player(current_touch_id)
            if touch_player:
                team = touch_player.team
                # Left team wants ball to go right (+x), right team wants left (-x)
                progress = ball_dx if team == "left" else -ball_dx
                telemetry.teams[team].ball_progress += progress

        prev_ball_x = ball.position.x

        # Track touches via last_touch_player_id
        if current_touch_id and current_touch_id != last_touch_id:
            player = engine.get_player(current_touch_id)
            if player:
                team = player.team
                touches[team] += 1
                telemetry.teams[team].touches += 1
                telemetry.players[current_touch_id].touches += 1
                telemetry.players[current_touch_id].kicks += 1
                event_log.append((cycle, "touch", team, current_touch_id))

                # Check if this is a shot (kick toward opponent goal)
                # Shot = ball velocity pointing toward opponent goal
                ball_vx = ball.velocity.x
                is_shot = (team == "left" and ball_vx > 0.5) or (team == "right" and ball_vx < -0.5)
                if is_shot:
                    telemetry.teams[team].shots += 1

                    # Shot on target = ball y within goal width when it reaches goal line
                    # Approximate: check if ball trajectory intersects goal
                    goal_x = half_length if team == "left" else -half_length
                    if abs(ball_vx) > 0.01:
                        t_to_goal = (goal_x - ball.position.x) / ball_vx
                        if t_to_goal > 0:
                            predicted_y = ball.position.y + ball.velocity.y * t_to_goal
                            if abs(predicted_y) < config.params.goal_width / 2:
                                telemetry.teams[team].shots_on_target += 1

            last_touch_id = current_touch_id

        # Track possession
        if current_touch_id:
            player = engine.get_player(current_touch_id)
            if player:
                possession_cycles[player.team] += 1
                telemetry.teams[player.team].possession_frames += 1

        # Log goals
        for event in step_result.get("events", []):
            if event.get("type") == "goal":
                scoring_team = event["team"]
                telemetry.teams[scoring_team].goals += 1
                event_log.append((cycle, "goal", scoring_team, event.get("scorer_id")))

    telemetry.total_cycles = config.max_cycles

    # Calculate deterministic hash from final state
    ball = engine.get_ball()
    final_state = {
        "event_log": event_log,
        "final_ball_pos": (round(ball.position.x, 6), round(ball.position.y, 6)),
        "final_player_pos": [
            (
                pid,
                round(engine.get_player(pid).position.x, 6),
                round(engine.get_player(pid).position.y, 6),
            )
            for pid in player_ids
            if engine.get_player(pid)
        ],
        "final_score": engine.score,
    }
    state_str = json.dumps(final_state, sort_keys=True)
    episode_hash = hashlib.sha256(state_str.encode()).hexdigest()

    return QuickEvalResult(
        seed=config.seed,
        cycles=config.max_cycles,
        score=engine.score,
        touches=touches,
        possession_cycles=possession_cycles,
        episode_hash=episode_hash,
        telemetry=telemetry,
    )
