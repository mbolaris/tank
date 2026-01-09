"""Soccer match manager using RCSS-Lite engine.

This module manages soccer matches with RCSS-compatible physics. It outputs
**field-space coordinates** (meters, centered at origin) - the frontend is
responsible for scaling to pixel coordinates.

Key design decisions:
- Entity-agnostic: uses SoccerParticipant protocol, not Fish directly
- Field-space output: all coordinates in meters, origin at field center
- Snapshot includes field dimensions so frontend can scale dynamically
- Uses GenomeCodePool directly for policy execution (no local copying)
- Deterministic RNG forked per player for reproducible matches
"""

from __future__ import annotations

import logging
import math
import random as pyrandom
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from core.code_pool.safety import fork_rng
from core.minigames.soccer.engine import RCSSLiteEngine, RCSSVector
from core.minigames.soccer.params import RCSSParams
from core.minigames.soccer.participant import create_participants_from_fish

if TYPE_CHECKING:
    from core.code_pool import GenomeCodePool
    from core.entities import Fish

logger = logging.getLogger(__name__)


@dataclass
class FieldDimensions:
    """Field dimensions in meters for snapshot output."""

    length: float  # x-axis (horizontal)
    width: float  # y-axis (vertical)
    goal_width: float
    goal_depth: float


class SoccerMatch:
    """Manages a soccer match simulation using RCSS-Lite physics.

    This class uses the RCSS-Lite engine which implements rcssserver-compatible
    physics including:
    - Cycle-based stepping (100ms per cycle)
    - Command queue semantics (commands applied at cycle end)
    - RCSS velocity decay model

    Output coordinates are in **field-space** (meters), not pixels.
    The snapshot includes field dimensions so the frontend can scale.
    """

    def __init__(
        self,
        match_id: str,
        fish_players: list[Fish],
        duration_frames: int = 3000,
        code_source: GenomeCodePool | None = None,
        view_mode: str = "side",
        seed: int | None = None,
    ):
        """Initialize a new soccer match.

        Args:
            match_id: Unique identifier for this match
            fish_players: List of fish entities to participate
            duration_frames: Match duration in cycles (default 3000 = 5 minutes at 10Hz)
            code_source: Optional code pool for policy lookup
            view_mode: Rendering style ("side" for fish, "top" for microbes)
            seed: Random seed for deterministic matches
        """
        self.match_id = match_id
        self.duration_frames = duration_frames
        self.current_frame = 0
        self.game_over = False
        self.winner_team: str | None = None
        self.message = "Match starting..."
        self.view_mode = view_mode

        # Convert fish to participants
        self.participants, self.player_map = create_participants_from_fish(fish_players)

        # Store code source for policy lookup (used directly, no copying)
        self._code_source = code_source

        # Initialize deterministic RNG from match seed
        # Use hash of match_id if no seed provided (deterministic, no global random)
        self._match_seed = seed if seed is not None else hash(match_id) & 0xFFFFFFFF
        self._rng = pyrandom.Random(self._match_seed)

        # Configure RCSS-Lite engine
        self._params = RCSSParams(
            field_length=100.0,
            field_width=60.0,
        )

        # Field dimensions for snapshot output
        self._field = FieldDimensions(
            length=self._params.field_length,
            width=self._params.field_width,
            goal_width=self._params.goal_width,
            goal_depth=self._params.goal_depth,
        )

        # Initialize RCSS-Lite engine
        self._engine = RCSSLiteEngine(params=self._params, seed=seed)

        # Add players to engine with formation positions
        team_size = len(self.participants) // 2
        self._setup_formations(team_size)

        # Stable ID mapping for entity IDs (player/ball -> stable int)
        self._entity_ids: dict[str, int] = {}
        self._next_id = 1

        logger.info(
            f"Soccer Match {match_id} initialized with {len(self.participants)} players "
            f"({team_size} vs {team_size})"
        )

    def _setup_formations(self, team_size: int) -> None:
        """Set up initial player formations."""
        half_length = self._params.field_length / 2

        for i in range(team_size):
            # Left team - face right (0 radians)
            left_id = f"left_{i + 1}"
            x = -half_length / 2 + (i % 4) * 8 - 10
            y = (i // 4 - team_size // 8) * 12
            self._engine.add_player(left_id, "left", RCSSVector(x, y), body_angle=0.0)

            # Right team - face left (pi radians)
            right_id = f"right_{i + 1}"
            x = half_length / 2 - (i % 4) * 8 + 10
            y = (i // 4 - team_size // 8) * 12
            self._engine.add_player(right_id, "right", RCSSVector(x, y), body_angle=math.pi)

    def step(self, num_steps: int = 1) -> dict[str, Any]:
        """Advance the match by one or more cycles.

        Args:
            num_steps: Number of simulation cycles to advance (default 1)

        Returns:
            Current match state for rendering (field-space coordinates)
        """
        if self.game_over:
            return self.get_state()

        for _ in range(num_steps):
            if self.game_over:
                break

            # Queue autopolicy commands for each player
            self._queue_autopolicy_commands()

            # Step the RCSS-Lite engine (applies queued commands)
            step_result = self._engine.step_cycle()

            self.current_frame += 1

            # Check for goals
            for event in step_result.get("events", []):
                if event.get("type") == "goal":
                    # Goal was scored - engine already reset ball
                    pass

            if self.current_frame >= self.duration_frames:
                break

        # Check game end
        score = self._engine.score
        left_score = score.get("left", 0)
        right_score = score.get("right", 0)

        if self.current_frame >= self.duration_frames:
            self.game_over = True
            if left_score > right_score:
                self.winner_team = "left"
                self.message = f"Left Team Wins! ({left_score}-{right_score})"
            elif right_score > left_score:
                self.winner_team = "right"
                self.message = f"Right Team Wins! ({right_score}-{left_score})"
            else:
                self.winner_team = "draw"
                self.message = f"Match Draw! ({left_score}-{right_score})"
        else:
            self.message = (
                f"Time: {self.current_frame}/{self.duration_frames} | "
                f"Score: {left_score}-{right_score}"
            )

        return self.get_state()

    def _queue_autopolicy_commands(self) -> None:
        """Queue autopolicy commands for all players using shared adapter.

        Uses GenomeCodePool directly (no local copying) and forks RNG per player
        to ensure deterministic but independent policy execution.
        """
        from core.minigames.soccer.policy_adapter import (
            action_to_command,
            build_observation,
            run_policy,
        )

        for participant in self.participants:
            player_id = participant.participant_id

            # Build observation
            obs = build_observation(self._engine, player_id, self._params)
            if not obs:
                continue

            # Fork RNG for this player's policy execution (deterministic per player)
            player_rng = fork_rng(self._rng)

            # Run policy using _code_source directly (not a local copy)
            action = run_policy(
                code_source=self._code_source,
                genome=participant.genome_ref,
                observation=obs,
                rng=player_rng,
                dt=0.1,  # 100ms RCSS cycle
            )

            # Convert to command
            cmd = action_to_command(action, self._params)

            if cmd:
                self._engine.queue_command(player_id, cmd)

    def _get_stable_id(self, key: str) -> int:
        """Get or assign a stable integer ID for an entity key."""
        stable = self._entity_ids.get(key)
        if stable is None:
            stable = self._next_id
            self._next_id += 1
            self._entity_ids[key] = stable
        return stable

    def get_state(self) -> dict[str, Any]:
        """Get renderable state for frontend.

        Returns state with **field-space coordinates** (meters).
        Frontend is responsible for scaling to canvas pixels.
        """
        score = self._engine.score
        entities_dicts = []

        # Build ball entity (field-space coordinates)
        ball = self._engine.get_ball()
        entities_dicts.append(
            {
                "id": self._get_stable_id("ball"),
                "type": "ball",
                "x": ball.position.x,
                "y": ball.position.y,
                "width": self._params.ball_size * 2,
                "height": self._params.ball_size * 2,
                "radius": self._params.ball_size,
                "vel_x": ball.velocity.x,
                "vel_y": ball.velocity.y,
                "render_hint": {
                    "style": "soccer",
                    "sprite": "ball",
                    "velocity_x": ball.velocity.x,
                    "velocity_y": ball.velocity.y,
                },
            }
        )

        # Build player entities (field-space coordinates)
        for participant in self.participants:
            player_id = participant.participant_id
            player = self._engine.get_player(player_id)
            if player is None:
                continue

            jersey_num = int(player_id.split("_")[-1])

            entities_dicts.append(
                {
                    "id": self._get_stable_id(f"player:{player_id}"),
                    "type": "player",
                    "x": player.position.x,
                    "y": player.position.y,
                    "width": self._params.player_size * 2,
                    "height": self._params.player_size * 2,
                    "radius": self._params.player_size,
                    "vel_x": player.velocity.x,
                    "vel_y": player.velocity.y,
                    "energy": player.stamina,
                    "team": player.team,
                    "jersey_number": jersey_num,
                    "facing": player.body_angle,
                    "genome_data": participant.render_hint,
                    "render_hint": {
                        "style": "soccer",
                        "sprite": "player",
                        "team": player.team,
                        "jersey_number": jersey_num,
                        "stamina": player.stamina,
                        "facing_angle": player.body_angle,
                        "has_ball": False,
                    },
                }
            )

        # Sort by z-order: players first, then ball on top
        z_order = {"player": 5, "ball": 10}
        entities_dicts.sort(key=lambda e: z_order.get(e.get("type", ""), 0))

        # Get team rosters from participants
        left_ids = [
            self.player_map[p.participant_id].fish_id
            for p in self.participants
            if p.team == "left" and p.participant_id in self.player_map
        ]
        right_ids = [
            self.player_map[p.participant_id].fish_id
            for p in self.participants
            if p.team == "right" and p.participant_id in self.player_map
        ]

        return {
            "match_id": self.match_id,
            "game_over": self.game_over,
            "winner_team": self.winner_team,
            "message": self.message,
            "frame": self.current_frame,
            "score": score,
            "entities": entities_dicts,
            "view_mode": self.view_mode,
            "teams": {
                "left": left_ids,
                "right": right_ids,
            },
            # Field dimensions for frontend scaling
            "field": {
                "length": self._field.length,
                "width": self._field.width,
                "goal_width": self._field.goal_width,
                "goal_depth": self._field.goal_depth,
            },
        }
