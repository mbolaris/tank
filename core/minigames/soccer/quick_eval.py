"""Quick deterministic soccer evaluation using RCSS-Lite engine.

This module provides fast, deterministic soccer episode evaluation for:
- Evolution fitness evaluation
- CI determinism tests
- Quick benchmarking

Uses RCSSLiteEngine directly without Fish/Match overhead.
This is the canonical evaluation path for soccer simulations (shared params preset
with SoccerMatch/SoccerMatchRunner via SOCCER_CANONICAL_PARAMS).

Example:
    >>> config = QuickEvalConfig(seed=42, max_cycles=200)
    >>> result = run_quick_eval(config)
    >>> print(result.score, result.episode_hash)
    >>> print(result.telemetry.teams["left"].ball_progress)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from core.minigames.soccer.engine import RCSSLiteEngine, RCSSVector
from core.minigames.soccer.params import SOCCER_CANONICAL_PARAMS, RCSSParams
from core.minigames.soccer.participant import SoccerParticipant
from core.minigames.soccer.policy_adapter import (action_to_command,
                                                  build_observation,
                                                  default_policy_action)
from core.minigames.soccer.telemetry_collector import SoccerTelemetryCollector
from core.minigames.soccer.types import SoccerTelemetry


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
    params: RCSSParams = field(
        default_factory=lambda: RCSSParams.from_dict(SOCCER_CANONICAL_PARAMS.to_dict())
    )
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

    # Setup players and create participants for telemetry
    participants: list[SoccerParticipant] = []
    player_ids: list[str] = []
    for team in sorted(config.initial_players):
        positions = config.initial_players[team]
        for i, (x, y) in enumerate(positions):
            player_id = f"{team}_{i + 1}"
            # Face toward opponent goal
            body_angle = 0.0 if team == "left" else 3.14159
            engine.add_player(player_id, team, RCSSVector(x, y), body_angle=body_angle)
            player_ids.append(player_id)
            # Create participant for telemetry collector
            participants.append(
                SoccerParticipant(
                    participant_id=player_id,
                    team=team,
                    genome_ref=None,
                    render_hint=None,
                )
            )

    # Sort for deterministic iteration
    player_ids.sort()

    # Setup ball
    if config.initial_ball:
        engine.set_ball_position(config.initial_ball[0], config.initial_ball[1])
    else:
        engine.set_ball_position(0.0, 0.0)

    # Initialize telemetry collector (single source of truth)
    telemetry_collector = SoccerTelemetryCollector(
        engine=engine,
        params=config.params,
        participants=participants,
    )

    event_log: list[tuple[int, str, str, str | None]] = []

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

        # Update telemetry (via collector - single source of truth)
        telemetry_collector.step()

        # Build event log (for hash computation)
        touch_info = engine.last_touch_info()
        if touch_info["player_id"]:
            # Track touch events for determinism hash
            # Only log new touches (not every cycle with same toucher)
            if not event_log or event_log[-1][3] != touch_info["player_id"]:
                player = engine.get_player(touch_info["player_id"])
                if player:
                    event_log.append((cycle, "touch", player.team, touch_info["player_id"]))

        # Log goals
        for event in step_result.get("events", []):
            if event.get("type") == "goal":
                scoring_team = event["team"]
                event_log.append((cycle, "goal", scoring_team, event.get("scorer_id")))

    # Calculate deterministic hash from final state
    ball = engine.get_ball()
    final_player_pos: list[tuple[str, float, float]] = []
    for pid in player_ids:
        player = engine.get_player(pid)
        if player is None:
            continue
        final_player_pos.append(
            (
                pid,
                round(player.position.x, 6),
                round(player.position.y, 6),
            )
        )
    final_state = {
        "event_log": event_log,
        "final_ball_pos": (round(ball.position.x, 6), round(ball.position.y, 6)),
        "final_player_pos": final_player_pos,
        "final_score": engine.score,
    }
    state_str = json.dumps(final_state, sort_keys=True)
    episode_hash = hashlib.sha256(state_str.encode()).hexdigest()

    # Get final telemetry from collector
    final_telemetry = telemetry_collector.get_telemetry()

    # Legacy outputs (derived from telemetry to avoid drift)
    touches: dict[str, int] = {
        "left": final_telemetry.teams["left"].touches,
        "right": final_telemetry.teams["right"].touches,
    }
    possession_cycles: dict[str, int] = {
        "left": final_telemetry.teams["left"].possession_frames,
        "right": final_telemetry.teams["right"].possession_frames,
    }

    return QuickEvalResult(
        seed=config.seed,
        cycles=config.max_cycles,
        score=engine.score,
        touches=touches,
        possession_cycles=possession_cycles,
        episode_hash=episode_hash,
        telemetry=final_telemetry,
    )
