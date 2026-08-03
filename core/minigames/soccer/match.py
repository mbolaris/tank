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

import hashlib
import logging
import math
import random as pyrandom
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from core.code_pool.safety import fork_rng
from core.minigames.soccer.engine import RCSSLiteEngine, RCSSVector
from core.minigames.soccer.broadcast_metadata import build_match_broadcast_metadata
from core.minigames.soccer.field_profiles import geometry_for_params
from core.minigames.soccer.formation import build_default_formation
from core.minigames.soccer.params import SOCCER_CANONICAL_PARAMS
from core.minigames.soccer.participant import create_participants
from core.minigames.soccer.roster_snapshot import SoccerRosterSnapshot, snapshot_roster
from core.minigames.soccer.telemetry_collector import SoccerTelemetryCollector

if TYPE_CHECKING:
    from core.code_pool import GenomeCodePool

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
        entities: list[Any] | None = None,
        duration_frames: int = 3000,
        code_source: GenomeCodePool | None = None,
        view_mode: str = "side",
        seed: int | None = None,
        target_pursuit_module_enabled: bool | None = None,
        roster_snapshot: SoccerRosterSnapshot | None = None,
    ):
        """Initialize a new soccer match.

        Args:
            match_id: Unique identifier for this match
            entities: List of entities to participate (Fish or SoccerParticipant)
            duration_frames: Match duration in cycles (default 3000 = 5 minutes at 10Hz)
            code_source: Optional code pool for policy lookup
            view_mode: Rendering style ("side" for fish, "top" for microbes)
            seed: Random seed for deterministic matches
            target_pursuit_module_enabled: Whether to enable target pursuit module interception
            roster_snapshot: Optional immutable roster to replay without source entities
        """
        if roster_snapshot is None and entities is None:
            raise ValueError("SoccerMatch requires entities or a roster_snapshot")
        self.match_id = match_id
        self.duration_frames = duration_frames
        self.current_frame = 0
        self.game_over = False
        self.winner_team: str | None = None
        self.message = "Match starting..."
        self.view_mode = view_mode
        self._last_goal_event: dict[str, Any] | None = None
        self.target_pursuit_module_enabled = target_pursuit_module_enabled or False
        # Every goal event of the match (for per-player scoring stats)
        self.goal_log: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self.command_log: list[dict[str, Any]] = []

        # Snapshot before any match execution. This consumes no match RNG and
        # leaves source fish entirely outside the execution graph. A supplied
        # snapshot is reused verbatim for deterministic replay.
        if roster_snapshot is None:
            selected_participants, _selected_entity_map = create_participants(entities or [])
            self.roster_snapshot = snapshot_roster(selected_participants)
        else:
            self.roster_snapshot = roster_snapshot
        self.participants = self.roster_snapshot.detached_participants()
        self._entity_by_participant_id = {p.participant_id: p for p in self.participants}

        # Physics, policy, and rendering all use detached participants.
        self.player_map = self._entity_by_participant_id

        # Store code source for policy lookup (used directly, no copying)
        self._code_source = code_source

        # Initialize deterministic RNG from match seed
        # Use a stable hash of match_id if no seed provided (deterministic, no global random)
        if seed is not None:
            self._match_seed = seed
        else:
            seed_material = match_id.encode("utf-8")
            self._match_seed = (
                int.from_bytes(hashlib.sha256(seed_material).digest()[:4], "little") & 0xFFFFFFFF
            )
        self._rng = pyrandom.Random(self._match_seed)

        # Configure RCSS-Lite engine with the canonical soccer params preset.
        self._params = SOCCER_CANONICAL_PARAMS

        # Field dimensions for snapshot output
        self._geometry = geometry_for_params(self._params)
        self._field = FieldDimensions(
            length=self._params.field_length,
            width=self._params.field_width,
            goal_width=self._params.goal_width,
            goal_depth=self._params.goal_depth,
        )

        # Initialize RCSS-Lite engine with deterministic seed
        self._engine = RCSSLiteEngine(params=self._params, seed=self._match_seed)

        # Store initial positions for resets (x, y, angle)
        self._initial_positions: dict[str, tuple[float, float, float]] = {}

        # Add players to engine with formation positions
        team_size = len(self.participants) // 2
        self._setup_formations(team_size)
        self._emit_event(kind="kickoff", frame=0)

        # Stable ID mapping for entity IDs (player/ball -> stable int)
        self._entity_ids: dict[str, int] = {}
        self._next_id = 1

        # Initialize telemetry collector (single source of truth)
        self._telemetry_collector = SoccerTelemetryCollector(
            engine=self._engine,
            params=self._params,
            participants=self.participants,
        )

        # Expose telemetry for external access
        self.telemetry = self._telemetry_collector.get_telemetry()

        logger.info(
            f"Soccer Match {match_id} initialized with {len(self.participants)} players "
            f"({team_size} vs {team_size})"
        )

    @classmethod
    def from_roster_snapshot(
        cls,
        roster_snapshot: SoccerRosterSnapshot,
        *,
        match_id: str,
        duration_frames: int = 3000,
        code_source: GenomeCodePool | None = None,
        view_mode: str = "side",
        seed: int | None = None,
        target_pursuit_module_enabled: bool | None = None,
    ) -> SoccerMatch:
        """Replay a match from immutable roster data without source entities."""
        return cls(
            match_id=match_id,
            entities=None,
            duration_frames=duration_frames,
            code_source=code_source,
            view_mode=view_mode,
            seed=seed,
            target_pursuit_module_enabled=target_pursuit_module_enabled,
            roster_snapshot=roster_snapshot,
        )

    def _setup_formations(self, team_size: int) -> None:
        """Set up initial player formations."""
        for spec in build_default_formation(team_size=team_size, params=self._params):
            self._initial_positions[spec.player_id] = (spec.x, spec.y, spec.body_angle)
            self._engine.add_player(
                spec.player_id,
                spec.team,
                RCSSVector(spec.x, spec.y),
                body_angle=spec.body_angle,
            )

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

            # Update telemetry after step (via collector)
            self._telemetry_collector.step()

            # Check for goals
            for event in step_result.get("events", []):
                if event.get("type") == "goal":
                    event = dict(event)
                    event["frame"] = self.current_frame
                    self._last_goal_event = event
                    self.goal_log.append(event)
                    self._emit_event(
                        kind="goal",
                        frame=self.current_frame,
                        side=event.get("team"),
                        actor=event.get("scorer_id"),
                        assist=event.get("assist_id"),
                    )
                    # Goal was scored - engine reset ball/mode, we reset players
                    self._reset_players()

            # Check for half-time
            if self.current_frame == self.duration_frames // 2:
                self._handle_half_time()
                self._emit_event(kind="half_time", frame=self.current_frame)

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
            self._emit_event(kind="full_time", frame=self.current_frame)
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
            attach_target_pursuit_vector,
            build_observation,
            run_policy,
        )

        for participant in self.participants:
            player_id = participant.participant_id

            # Build observation
            obs = build_observation(self._engine, player_id, self._params)
            if not obs:
                continue

            # Inject target pursuit module if enabled
            if self.target_pursuit_module_enabled:
                genome = getattr(participant, "genome_ref", None) or getattr(
                    participant, "genome", None
                )
                module = None
                if genome is not None:
                    module_trait = getattr(genome.behavioral, "target_pursuit_module", None)
                    module = module_trait.value if module_trait is not None else None
                attach_target_pursuit_vector(obs, module)
            else:
                obs["soccer_target_pursuit_enabled"] = False

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
                self.command_log.append(
                    {
                        "frame": self.current_frame,
                        "participant_id": player_id,
                        "type": cmd.cmd_type.value,
                        "power": cmd.power,
                        "direction": cmd.direction,
                    }
                )
                self._engine.queue_command(player_id, cmd)

    def _reset_players(self) -> None:
        """Reset all players to their initial positions (start or after goal)."""
        for player_id, (x, y, angle) in self._initial_positions.items():
            player = self._engine.get_player(player_id)
            if player:
                player.position = RCSSVector(x, y)
                player.velocity = RCSSVector(0.0, 0.0)
                player.acceleration = RCSSVector(0.0, 0.0)
                player.body_angle = angle
                # We do not reset stamina to preserve fatigue mechanics

    def _handle_half_time(self) -> None:
        """Handle half-time side switch."""
        logger.info("Half-time! Switching sides.")
        self.message = "Half Time! Switching Sides"

        # 1. Update engine side-swap state
        self._engine.set_swapped_sides(True)

        # 2. Update initial positions for side swap (invert all)
        # x -> -x, y -> -y (rotate 180 degrees around center)
        # angle -> angle + pi
        new_positions = {}
        for pid, (x, y, angle) in self._initial_positions.items():
            new_angle = angle + math.pi
            # Normalize angle
            while new_angle > math.pi:
                new_angle -= 2 * math.pi
            new_positions[pid] = (-x, -y, new_angle)
        self._initial_positions = new_positions

        # 3. Reset players to new positions
        self._reset_players()

        # 4. Reset ball to center and set kick-off
        self._engine.set_ball_position(0.0, 0.0)
        # 2nd half kick-off usually by Right team (if Left started)
        # But if sides swapped, Right Team is on Left Side.
        # kick_off_right means Right Team kicks.
        self._engine.set_play_mode("kick_off_right")

    def _get_stable_id(self, key: str) -> int:
        """Get or assign a stable integer ID for an entity key."""
        stable = self._entity_ids.get(key)
        if stable is None:
            stable = self._next_id
            self._next_id += 1
            self._entity_ids[key] = stable
        return stable

    def _emit_event(
        self,
        *,
        kind: str,
        frame: int,
        side: str | None = None,
        actor: str | None = None,
        assist: str | None = None,
    ) -> dict[str, Any]:
        seq = len(self.events)
        event: dict[str, Any] = {
            "frame": int(frame),
            "seq": seq,
            "event_id": f"{self.match_id}-{kind}-{frame}-{seq}",
            "kind": kind,
        }
        if side is not None:
            event["side"] = side
        if actor is not None:
            event["actor"] = actor
        if assist is not None:
            event["assist"] = assist
        self.events.append(event)
        return event

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
                    "participant_id": player_id,
                    "genome_data": participant.render_hint,
                    "render_hint": {
                        # New physical-state join key.  Identity duplication
                        # below is the deprecated §10.1 compatibility bridge:
                        # SoccerTopDownRenderer still reads these fields.
                        "participant_id": player_id,
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

        def _z_key(entity: dict[str, Any]) -> int:
            entity_type = entity.get("type")
            return z_order.get(entity_type, 0) if isinstance(entity_type, str) else 0

        entities_dicts.sort(key=_z_key)

        left_ids = []
        for p in self.participants:
            if p.team == "left" and p.participant_id in self.player_map:
                entity = self.player_map[p.participant_id]
                entity_id = getattr(entity, "fish_id", None)
                if entity_id is None:
                    entity_id = p.participant_id
                left_ids.append(entity_id)

        right_ids = []
        for p in self.participants:
            if p.team == "right" and p.participant_id in self.player_map:
                entity = self.player_map[p.participant_id]
                entity_id = getattr(entity, "fish_id", None)
                if entity_id is None:
                    entity_id = p.participant_id
                right_ids.append(entity_id)

        return {
            "match_id": self.match_id,
            "game_over": self.game_over,
            "winner_team": self.winner_team,
            "message": self.message,
            "frame": self.current_frame,
            "score": score,
            **build_match_broadcast_metadata(self),
            "last_goal": self._last_goal_event,
            "events": list(self.events),
            "participants": [p.to_wire_dict() for p in self.roster_snapshot.participants],
            "geometry": self._geometry.to_dict(),
            # Explicit legacy default keeps the existing renderer's y-down
            # convention intact until its canonical boundary lands.
            "coord_space": "legacy_render",
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
