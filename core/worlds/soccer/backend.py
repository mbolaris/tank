"""Soccer world backend adapter implementing MultiAgentWorldBackend.

This provides a pure-python training environment for evolving soccer policies.
It can be used standalone or as a component in a larger simulation.
With GenomeCodePool integration, supports autopolicy-driven evolution.
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from core.worlds.interfaces import FAST_STEP_ACTION, MultiAgentWorldBackend, StepResult
from core.worlds.soccer.config import SoccerWorldConfig
from core.worlds.soccer.physics import Ball, FieldBounds, Player, SoccerPhysics
from core.worlds.soccer.types import (
    BallState,
    PlayerID,
    PlayerState,
    SoccerAction,
    SoccerObservation,
    SoccerReward,
    TeamID,
    Vector2D,
)

if TYPE_CHECKING:
    from core.code_pool import GenomeCodePool
    from core.genetics import Genome

logger = logging.getLogger(__name__)


@dataclass
class PlayerStats:
    """Per-player statistics for fitness calculation."""

    goals: int = 0
    assists: int = 0
    possessions: int = 0
    kicks: int = 0

    def fitness(self) -> float:
        """Calculate fitness from stats."""
        return self.goals * 100.0 + self.assists * 50.0 + self.possessions * 0.1


class SoccerWorldBackendAdapter(MultiAgentWorldBackend):
    """Pure-python soccer training world implementing MultiAgentWorldBackend.

    This adapter provides:
    - Deterministic 2D physics simulation
    - Configurable team sizes (1v1 to 11v11)
    - Reward shaping for training
    - Event tracking (goals, shots, passes)
    - Stamina/energy accounting

    Future extension point for rcssserver evaluation mode.

    Args:
        seed: Random seed for deterministic simulation
        config: Soccer world configuration
        **config_overrides: Override specific config parameters

    Example:
        >>> adapter = SoccerWorldBackendAdapter(seed=42, team_size=3)
        >>> result = adapter.reset(seed=42)
        >>> actions = {"left_1": {"move_target": {"x": 10, "y": 5}, "kick_power": 0.5}}
        >>> result = adapter.step(actions_by_agent=actions)
    """

    def __init__(
        self,
        seed: Optional[int] = None,
        config: Optional[SoccerWorldConfig] = None,
        genome_code_pool: Optional[GenomeCodePool] = None,
        **config_overrides,
    ):
        """Initialize the soccer world backend.

        Args:
            seed: Random seed for deterministic simulation
            config: Complete SoccerWorldConfig (if provided, overrides are ignored)
            genome_code_pool: Optional GenomeCodePool for autopolicy-driven stepping
            **config_overrides: Individual config parameters to override
        """
        self._seed = seed
        self._config_overrides = config_overrides

        # Create config from overrides if not provided
        if config is None:
            config = SoccerWorldConfig(**config_overrides)

        config.validate()
        self._config = config

        # Initialize RNG for determinism
        self._rng = random.Random(seed)

        # Game state (initialized in reset())
        self._players: dict[PlayerID, Player] = {}
        self._ball: Optional[Ball] = None
        self._field: Optional[FieldBounds] = None
        self._physics: Optional[SoccerPhysics] = None

        # Match state
        self._frame = 0
        self._score = {"left": 0, "right": 0}
        self._play_mode = "before_kick_off"
        self._possession_tracker: dict[TeamID, int] = {"left": 0, "right": 0}
        self._last_ball_distances: dict[PlayerID, float] = {}

        # Event tracking
        self._recent_events: list[dict[str, Any]] = []

        # Pause state (stored but doesn't affect soccer physics)
        self._paused = False

        # GenomeCodePool for autopolicy-driven evolution
        self._genome_code_pool = genome_code_pool
        self._genome_by_player: dict[PlayerID, Genome] = {}
        self._stats_by_player: dict[PlayerID, PlayerStats] = {}

        self.supports_fast_step = True

    def reset(
        self, seed: Optional[int] = None, config: Optional[dict[str, Any]] = None
    ) -> StepResult:
        """Reset the soccer world to initial state.

        Args:
            seed: Random seed (overrides constructor seed if provided)
            config: Soccer-specific configuration overrides

        Returns:
            StepResult with initial observations and snapshot
        """
        # Use provided seed or fall back to constructor seed
        reset_seed = seed if seed is not None else self._seed
        self._rng = random.Random(reset_seed)

        if config:
            merged = {**self._config.to_dict(), **config}
            self._config = SoccerWorldConfig.from_dict(merged)
            self._config.validate()

        # Initialize field and physics
        self._field = FieldBounds(
            width=self._config.field_width,
            height=self._config.field_height,
        )
        self._physics = SoccerPhysics(
            field_bounds=self._field,
            ball_friction=self._config.ball_friction,
            player_max_speed=self._config.player_max_speed,
            player_acceleration=self._config.player_acceleration,
            ball_kick_power_max=self._config.ball_kick_power_max,
            rng=self._rng,
        )

        # Create ball at center
        self._ball = Ball(
            position=self._field.get_initial_ball_position(),
            velocity=Vector2D(0.0, 0.0),
            radius=self._config.ball_radius,
        )

        # Create players for both teams
        self._players = {}
        for team in ["left", "right"]:
            positions = self._field.get_initial_player_positions(
                team=team, team_size=self._config.team_size, rng=self._rng
            )
            for i, pos in enumerate(positions):
                player_id = f"{team}_{i + 1}"
                facing = 0.0 if team == "left" else 3.14159  # Face opponent goal
                self._players[player_id] = Player(
                    player_id=player_id,
                    team=team,
                    position=pos,
                    velocity=Vector2D(0.0, 0.0),
                    facing_angle=facing,
                    stamina=self._config.stamina_max,
                    radius=self._config.player_radius,
                    max_stamina=self._config.stamina_max,
                )

        # Reset match state
        self._frame = 0
        self._score = {"left": 0, "right": 0}
        self._play_mode = "kick_off_left"
        self._possession_tracker = {"left": 0, "right": 0}
        self._last_ball_distances = {}
        self._recent_events = []

        # Reset genome and stats tracking (preserve genomes if they exist)
        self._stats_by_player = {pid: PlayerStats() for pid in self._players}

        logger.info(
            f"Soccer world reset with seed={reset_seed}, "
            f"team_size={self._config.team_size}, "
            f"field={self._config.field_width}x{self._config.field_height}"
        )

        # Return initial state
        return StepResult(
            obs_by_agent=self._build_observations(),
            snapshot=self._build_snapshot(),
            events=[],
            metrics=self.get_current_metrics(),
            done=False,
            info={"frame": self._frame, "seed": reset_seed},
            spawns=[],
            removals=[],
            energy_deltas=[],
            render_hint={
                "style": "topdown",
                "entity_style": "player",
            },
        )

    def step(self, actions_by_agent: Optional[dict[str, Any]] = None) -> StepResult:
        """Advance the simulation by one timestep.

        Args:
            actions_by_agent: Dict mapping player_id to action dict. If an action
                is missing for a player and genome_code_pool is set, the action
                is computed via autopolicy.

                Action dict format (normalized): {
                    "turn": float (-1 to 1),
                    "dash": float (-1 to 1),
                    "kick_power": float (0-1),
                    "kick_angle": float (radians),
                }

        Returns:
            StepResult with observations, events, metrics, and done flag
        """
        fast_step = bool(actions_by_agent and actions_by_agent.get(FAST_STEP_ACTION))
        self._recent_events = []

        # Fill in missing actions via autopolicy if genome_code_pool is set
        all_actions = self._fill_actions_via_autopolicy(actions_by_agent or {})

        # Process player actions
        if all_actions:
            self._process_actions(all_actions)

        # Update physics
        self._update_physics()

        # Update stamina
        self._update_stamina()

        # Check for goals
        scoring_team = self._field.is_goal(self._ball.position)
        if scoring_team:
            self._handle_goal(scoring_team)

        # Track possession
        self._update_possession()

        # Increment frame
        self._frame += 1

        # Check if match is done
        done = self._frame >= self._config.half_time_duration * 2

        # Build result (skip expensive operations in fast mode)
        events = [] if fast_step else self._recent_events.copy()
        metrics = {} if fast_step else self.get_current_metrics()
        obs = {} if fast_step else self._build_observations()

        return StepResult(
            obs_by_agent=obs,
            snapshot=self._build_snapshot(),
            events=events,
            metrics=metrics,
            done=done,
            info={"frame": self._frame},
            spawns=[],
            removals=[],
            energy_deltas=[],
            render_hint={
                "style": "topdown",
                "entity_style": "player",
            },
        )

    def _fill_actions_via_autopolicy(self, actions_by_agent: dict[str, Any]) -> dict[str, Any]:
        """Fill in missing actions using autopolicy from GenomeCodePool.

        For each player without an action, computes action via:
        1. Their assigned genome's soccer_policy_id (if set)
        2. The pool's default soccer policy (fallback)
        3. A built-in chase-ball default (if no pool)
        """
        if not self._genome_code_pool:
            # No pool - return actions as-is (players with no action do nothing)
            return actions_by_agent

        # Build observations once for all players who need autopolicy
        observations: Optional[dict[PlayerID, dict[str, Any]]] = None

        result = dict(actions_by_agent)
        for player_id in sorted(self._players.keys()):
            if player_id in result and player_id != FAST_STEP_ACTION:
                continue  # Already have action

            # Lazy-build observations
            if observations is None:
                observations = self._build_observations()

            player_obs = observations.get(player_id, {})
            action = self._compute_autopolicy_action(player_id, player_obs)
            if action:
                result[player_id] = action.to_dict()

        return result

    def _compute_autopolicy_action(
        self, player_id: PlayerID, observation: dict[str, Any]
    ) -> Optional[SoccerAction]:
        """Compute action for a player using their genome's policy."""
        from core.genetics.code_policy_traits import extract_policy_set_from_behavioral

        genome = self._genome_by_player.get(player_id)
        if genome is None:
            # No genome assigned - use default policy
            return self._default_chase_ball_action(observation)

        # Extract policy set from genome
        policy_set = extract_policy_set_from_behavioral(genome.behavioral)
        component_id = policy_set.get_component_id("soccer_policy")

        if component_id is None:
            # No soccer policy set - try pool default
            default_id = self._genome_code_pool.get_default("soccer_policy")
            if default_id:
                component_id = default_id
            else:
                return self._default_chase_ball_action(observation)

        # Execute policy
        params = policy_set.get_params("soccer_policy")
        dt = 1.0 / self._config.frame_rate

        result = self._genome_code_pool.execute_policy(
            component_id=component_id,
            observation=observation,
            rng=self._rng,
            dt=dt,
            params=params,
        )

        if not result.success:
            logger.warning(
                "Policy %s failed for %s: %s",
                component_id,
                player_id,
                result.error_message,
            )
            return self._default_chase_ball_action(observation)

        # Coerce output to SoccerAction
        action = self._coerce_output_to_action(result.output)
        if action is None or not action.is_valid():
            logger.warning("Policy %s returned invalid action for %s", component_id, player_id)
            return self._default_chase_ball_action(observation)

        return action

    def _coerce_output_to_action(self, output: Any) -> Optional[SoccerAction]:
        """Coerce policy output to SoccerAction."""
        if isinstance(output, SoccerAction):
            return output
        if isinstance(output, dict):
            if "turn" in output or "dash" in output:
                return SoccerAction.from_dict(output)
        if isinstance(output, (tuple, list)) and len(output) >= 4:
            try:
                return SoccerAction(
                    turn=float(output[0]),
                    dash=float(output[1]),
                    kick_power=float(output[2]),
                    kick_angle=float(output[3]),
                )
            except (TypeError, ValueError):
                return None
        return None

    def _default_chase_ball_action(self, observation: dict[str, Any]) -> SoccerAction:
        """Default policy: chase ball and kick toward goal."""
        try:
            self_x = float(observation.get("position", {}).get("x", 0.0))
            self_y = float(observation.get("position", {}).get("y", 0.0))
            ball_x = float(observation.get("ball_position", {}).get("x", 0.0))
            ball_y = float(observation.get("ball_position", {}).get("y", 0.0))
            field_width = float(observation.get("field_width", 100.0))
            facing_angle = float(observation.get("facing_angle", 0.0))

            # Calculate direction to ball
            dx = ball_x - self_x
            dy = ball_y - self_y
            dist_sq = dx * dx + dy * dy
            dist = math.sqrt(dist_sq) if dist_sq > 0 else 0.0

            # Calculate turn needed to face ball
            target_angle = math.atan2(dy, dx)
            angle_delta = target_angle - facing_angle
            while angle_delta > math.pi:
                angle_delta -= 2 * math.pi
            while angle_delta < -math.pi:
                angle_delta += 2 * math.pi
            turn = max(-1.0, min(1.0, angle_delta / 0.35))

            # Dash toward ball if not too close
            dash = 1.0 if dist > 0.5 else 0.0

            # Kick if close to ball
            kick_power = 0.0
            kick_angle = 0.0
            if dist < 2.0:
                # Kick toward opponent goal (right side)
                goal_x = field_width / 2.0
                goal_y = 0.0
                goal_dx = goal_x - ball_x
                goal_dy = goal_y - ball_y
                kick_angle = math.atan2(goal_dy, goal_dx) - facing_angle
                kick_power = 0.8

            return SoccerAction(
                turn=turn,
                dash=dash,
                kick_power=kick_power,
                kick_angle=kick_angle,
            )
        except (TypeError, ValueError, KeyError):
            return SoccerAction()

    def get_current_snapshot(self) -> dict[str, Any]:
        """Get current world state for rendering."""
        return self._build_snapshot()

    def get_current_metrics(self) -> dict[str, Any]:
        """Get current simulation metrics."""
        return {
            "frame": self._frame,
            "score_left": self._score["left"],
            "score_right": self._score["right"],
            "possession_left": self._possession_tracker["left"],
            "possession_right": self._possession_tracker["right"],
            "num_players": len(self._players),
            "ball_speed": self._ball.velocity.magnitude() if self._ball else 0.0,
            "play_mode": self._play_mode,
        }

    # =========================================================================
    # Public API for evolution experiments
    # =========================================================================

    def list_agents(self) -> list[PlayerID]:
        """Return list of all player IDs.

        Returns:
            List of player IDs like ["left_1", "left_2", "right_1", ...]
        """
        return list(self._players.keys())

    def set_player_genome(self, player_id: PlayerID, genome: Genome) -> None:
        """Assign a genome to a player.

        The genome's soccer_policy_id will be used for autopolicy actions.

        Args:
            player_id: Player to assign genome to
            genome: Genome with soccer_policy_id set
        """
        if player_id not in self._players:
            logger.warning("set_player_genome: player %s not found", player_id)
            return
        self._genome_by_player[player_id] = genome

    def assign_team_policy(self, team: TeamID, component_id: str) -> None:
        """Assign a soccer policy to all players on a team.

        Convenience method for benchmarks/tests. Creates or updates genomes
        for all players on the team with the specified soccer policy.

        Args:
            team: "left" or "right"
            component_id: Soccer policy component ID from the pool
        """
        from core.genetics import Genome
        from core.genetics.trait import GeneticTrait

        for player_id, player in self._players.items():
            if player.team != team:
                continue

            # Get existing genome or create new one
            genome = self._genome_by_player.get(player_id)
            if genome is None:
                genome = Genome.random(use_algorithm=False, rng=self._rng)
                self._genome_by_player[player_id] = genome

            # Update soccer policy
            genome.behavioral.soccer_policy_id = GeneticTrait(component_id)
            genome.behavioral.soccer_policy_params = GeneticTrait({})

    def get_fitness_summary(self) -> dict[str, Any]:
        """Get fitness summary for all players.

        Returns a dict with:
        - score: {left: int, right: int}
        - team_fitness: {left: float, right: float}
        - agent_fitness: {player_id: {...stats...}}
        """
        per_agent: dict[str, Any] = {}
        for player_id, player in self._players.items():
            stats = self._stats_by_player.get(player_id, PlayerStats())
            per_agent[player_id] = {
                "team": player.team,
                "goals": stats.goals,
                "assists": stats.assists,
                "possessions": stats.possessions,
                "kicks": stats.kicks,
                "stamina": player.stamina,
                "fitness": stats.fitness(),
            }

        team_fitness = {
            "left": sum(
                self._stats_by_player.get(pid, PlayerStats()).fitness()
                for pid, p in self._players.items()
                if p.team == "left"
            ),
            "right": sum(
                self._stats_by_player.get(pid, PlayerStats()).fitness()
                for pid, p in self._players.items()
                if p.team == "right"
            ),
        }

        return {
            "score": dict(self._score),
            "team_fitness": team_fitness,
            "agent_fitness": per_agent,
        }

    def _process_actions(self, actions_by_agent: dict[str, Any]) -> None:
        """Process actions from all agents.

        Only supports normalized format (turn/dash/kick_power/kick_angle).
        Legacy formats are rejected.
        """
        import math

        for player_id, action_data in actions_by_agent.items():
            if player_id == FAST_STEP_ACTION or player_id not in self._players:
                continue

            player = self._players[player_id]

            # Parse action
            action = self._parse_action(action_data, player)
            if action is None or not action.is_valid():
                logger.warning(f"Invalid action for {player_id}")
                continue

            # Apply turn
            if action.turn != 0.0:
                turn_delta = action.turn * self._config.player_turn_rate
                player.facing_angle = self._normalize_angle(player.facing_angle + turn_delta)

            # Apply dash
            if action.dash != 0.0:
                direction = Vector2D(
                    math.cos(player.facing_angle),
                    math.sin(player.facing_angle),
                )
                accel_x = direction.x * action.dash * self._config.player_acceleration
                accel_y = direction.y * action.dash * self._config.player_acceleration
                new_vx = player.velocity.x + accel_x
                new_vy = player.velocity.y + accel_y
                # Clamp to max speed
                speed = math.sqrt(new_vx**2 + new_vy**2)
                if speed > self._config.player_max_speed:
                    scale = self._config.player_max_speed / speed
                    new_vx *= scale
                    new_vy *= scale
                player.velocity = Vector2D(new_vx, new_vy)

            # Handle kick
            if action.kick_power > 0:
                success = self._physics.kick_ball(
                    player, self._ball, action.kick_power, action.kick_angle
                )
                if success:
                    # Consume stamina for kick
                    player.stamina = max(0.0, player.stamina - self._config.stamina_kick_cost)
                    # Track kick in stats
                    if player_id in self._stats_by_player:
                        self._stats_by_player[player_id].kicks += 1
                    self._recent_events.append(
                        {
                            "type": "kick",
                            "player_id": player_id,
                            "team": player.team,
                            "power": action.kick_power,
                            "frame": self._frame,
                        }
                    )

    def _parse_action(self, action_data: Any, player: Player) -> Optional[SoccerAction]:
        """Parse action from dict - normalized format only.

        Legacy move_target/face_angle formats are NOT supported and will return None.
        """
        if isinstance(action_data, SoccerAction):
            return action_data

        if not isinstance(action_data, dict):
            return None

        # Only normalized format (turn/dash) is supported
        # We also check for kick_power/kick_angle as valid components of a normalized action
        if (
            "turn" in action_data
            or "dash" in action_data
            or "kick_power" in action_data
            or "kick_angle" in action_data
        ):
            return SoccerAction.from_dict(action_data)

        # Legacy formats are explicitly rejected
        if "move_target" in action_data or "face_angle" in action_data:
            logger.warning(
                "Legacy soccer action format (move_target/face_angle) is no longer supported. "
                "Use normalized format (turn/dash/kick_power/kick_angle) instead."
            )
            return None

        return None

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        """Normalize angle to [-pi, pi]."""
        import math

        while angle > math.pi:
            angle -= 2 * math.pi
        while angle < -math.pi:
            angle += 2 * math.pi
        return angle

    @staticmethod
    def _clamp(value: float, min_val: float, max_val: float) -> float:
        return max(min_val, min(max_val, value))

    def _update_physics(self) -> None:
        """Update ball and player physics."""
        # Update ball
        self._physics.update_ball(self._ball)

        # Update player positions from velocities
        for player in self._players.values():
            # Apply friction
            player.velocity = Vector2D(
                player.velocity.x * 0.95,
                player.velocity.y * 0.95,
            )
            # Update position
            new_x = player.position.x + player.velocity.x
            new_y = player.position.y + player.velocity.y
            # Clamp to field bounds
            new_x = max(-self._config.field_width / 2, min(self._config.field_width / 2, new_x))
            new_y = max(-self._config.field_height / 2, min(self._config.field_height / 2, new_y))
            player.position = Vector2D(new_x, new_y)

        # Handle player collisions
        self._physics.check_player_collisions(list(self._players.values()))

    def _update_stamina(self) -> None:
        """Update stamina for all players."""
        for player in self._players.values():
            # Check if sprinting (high velocity)
            speed = player.velocity.magnitude()
            is_sprinting = speed > self._config.player_max_speed * 0.7

            if is_sprinting:
                # Consume stamina
                player.stamina = max(0.0, player.stamina - self._config.stamina_sprint_cost)
            else:
                # Recover stamina
                player.stamina = min(
                    player.max_stamina,
                    player.stamina + self._config.stamina_recovery_rate,
                )

    def _handle_goal(self, scoring_team: TeamID) -> None:
        """Handle goal scored event."""
        self._score[scoring_team] += 1

        # Find closest player to ball (gets credit for goal)
        result = self._physics.find_closest_player_to_ball(
            self._ball,
            [p for p in self._players.values() if p.team == scoring_team],
        )

        scorer_id = result[0].player_id if result else "unknown"

        # Track stats for scorer
        if scorer_id in self._stats_by_player:
            self._stats_by_player[scorer_id].goals += 1

        self._recent_events.append(
            {
                "type": "goal",
                "team": scoring_team,
                "scorer": scorer_id,
                "frame": self._frame,
                "score": self._score.copy(),
            }
        )

        # Reset to center for kickoff
        self._ball.position = self._field.get_initial_ball_position()
        self._ball.velocity = Vector2D(0.0, 0.0)

        # Set play mode
        other_team = "left" if scoring_team == "right" else "right"
        self._play_mode = f"kick_off_{other_team}"

        logger.info(
            f"Goal! {scoring_team} scores (by {scorer_id}). "
            f"Score: {self._score['left']}-{self._score['right']}"
        )

    def _update_possession(self) -> None:
        """Track which team has possession of the ball."""
        result = self._physics.find_closest_player_to_ball(self._ball, list(self._players.values()))

        if result:
            closest_player, distance = result
            # Consider possession if within 2 meters
            if distance < 2.0:
                self._possession_tracker[closest_player.team] += 1
                # Track stats
                if closest_player.player_id in self._stats_by_player:
                    self._stats_by_player[closest_player.player_id].possessions += 1

    def _build_observations(self) -> dict[PlayerID, dict[str, Any]]:
        """Build observations for all players."""
        observations = {}

        for player_id, player in self._players.items():
            # Get teammates and opponents
            teammates = [
                p for pid, p in self._players.items() if p.team == player.team and pid != player_id
            ]
            opponents = [p for p in self._players.values() if p.team != player.team]

            # Build observation
            obs = SoccerObservation(
                self_state=PlayerState(
                    player_id=player.player_id,
                    team=player.team,
                    position=player.position,
                    velocity=player.velocity,
                    stamina=player.stamina / player.max_stamina,
                    facing_angle=player.facing_angle,
                ),
                ball=BallState(
                    position=self._ball.position,
                    velocity=self._ball.velocity,
                ),
                teammates=[
                    PlayerState(
                        player_id=tm.player_id,
                        team=tm.team,
                        position=tm.position,
                        velocity=tm.velocity,
                        stamina=tm.stamina / tm.max_stamina,
                        facing_angle=tm.facing_angle,
                    )
                    for tm in teammates
                ],
                opponents=[
                    PlayerState(
                        player_id=opp.player_id,
                        team=opp.team,
                        position=opp.position,
                        velocity=opp.velocity,
                        stamina=opp.stamina / opp.max_stamina,
                        facing_angle=opp.facing_angle,
                    )
                    for opp in opponents
                ],
                game_time=self._frame / self._config.frame_rate,
                play_mode=self._play_mode,
                field_bounds=(self._config.field_width, self._config.field_height),
            )

            observations[player_id] = obs.to_dict()

        return observations

    def _build_snapshot(self) -> dict[str, Any]:
        """Build snapshot for rendering/persistence."""
        return {
            "frame": self._frame,
            "ball": {
                "x": self._ball.position.x,
                "y": self._ball.position.y,
                "vx": self._ball.velocity.x,
                "vy": self._ball.velocity.y,
            },
            "players": [
                {
                    "id": player.player_id,
                    "team": player.team,
                    "x": player.position.x,
                    "y": player.position.y,
                    "vx": player.velocity.x,
                    "vy": player.velocity.y,
                    "facing": player.facing_angle,
                    "stamina": player.stamina / player.max_stamina,
                }
                for player in self._players.values()
            ],
            "field": {
                "width": self._config.field_width,
                "height": self._config.field_height,
                "goal_width": self._field.goal_width,
            },
            "score": self._score.copy(),
            "play_mode": self._play_mode,
        }

    def calculate_rewards(self) -> dict[PlayerID, SoccerReward]:
        """Calculate shaped rewards for all players (training only).

        Returns:
            Dict mapping player_id to SoccerReward
        """
        rewards = {}

        for player_id, player in self._players.items():
            reward = SoccerReward()

            # Goal rewards (from recent events)
            for event in self._recent_events:
                if event["type"] == "goal":
                    if event["team"] == player.team:
                        if event.get("scorer") == player_id:
                            reward.goal_scored = self._config.goal_reward
                        else:
                            reward.goal_scored = self._config.goal_reward * 0.5
                    else:
                        reward.goal_conceded = -self._config.goal_reward * 0.5

                elif event["type"] == "kick" and event["player_id"] == player_id:
                    # Check if shot on goal
                    ball_to_goal_dist = abs(
                        self._ball.position.x - self._field.x_max
                        if player.team == "left"
                        else self._ball.position.x - self._field.x_min
                    )
                    if ball_to_goal_dist < 20.0:  # Within shooting range
                        reward.shot_on_goal = self._config.shot_reward

            # Possession reward
            result = self._physics.find_closest_player_to_ball(self._ball, [player])
            if result and result[1] < 2.0:
                reward.ball_possession = self._config.possession_reward

            # Distance to ball delta (reward approaching ball)
            current_dist = player.distance_to(self._ball.position)
            if player_id in self._last_ball_distances:
                prev_dist = self._last_ball_distances[player_id]
                delta = prev_dist - current_dist
                reward.distance_to_ball_delta = delta * 0.1
            self._last_ball_distances[player_id] = current_dist

            # Stamina efficiency (penalize low stamina)
            if player.stamina < 20.0:
                reward.stamina_efficiency = -0.1

            rewards[player_id] = reward

        return rewards

    # =========================================================================
    # Protocol methods for world-agnostic backend support
    # =========================================================================

    @property
    def rng(self) -> Any:
        """Access the world's random number generator (protocol override)."""
        return self._rng

    @property
    def paused(self) -> bool:
        """Whether the simulation is paused (stores state for protocol compatibility)."""
        return self._paused

    @paused.setter
    def paused(self, value: bool) -> None:
        """Set the simulation paused state."""
        self._paused = value

    @property
    def is_paused(self) -> bool:
        """Whether the simulation is paused (protocol method)."""
        return self._paused

    def set_paused(self, value: bool) -> None:
        """Set the simulation paused state (protocol method)."""
        self._paused = value

    def get_entities_for_snapshot(self) -> list[Any]:
        """Get entities for snapshot building (protocol method).

        Soccer uses a different rendering model (players/ball in snapshot),
        not entities. Returns empty list.
        """
        return []

    @property
    def entities_list(self) -> list[Any]:
        """Legacy access to entities list (protocol method).

        Soccer doesn't use entities in the same way as tank/petri.
        Returns empty list.
        """
        return []

    def capture_state_for_save(self) -> dict[str, Any]:
        """Capture complete world state for persistence (protocol method).

        Soccer matches are ephemeral and don't support saving.
        """
        return {}

    def restore_state_from_save(self, state: dict[str, Any]) -> None:
        """Restore world state from a saved snapshot (protocol method).

        Soccer matches are ephemeral and don't support restoration.
        """
        pass
