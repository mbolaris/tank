"""Soccer world backend adapter implementing MultiAgentWorldBackend.

This provides a pure-python training environment for evolving soccer policies.
It can be used standalone or as a component in a larger simulation.
"""

import logging
import random
from typing import Any, Dict, List, Optional

from core.policies.soccer_interfaces import (
    BallState,
    PlayerID,
    PlayerState,
    SoccerAction,
    SoccerObservation,
    SoccerReward,
    TeamID,
    Vector2D,
)
from core.worlds.interfaces import FAST_STEP_ACTION, MultiAgentWorldBackend, StepResult
from core.worlds.soccer.config import SoccerWorldConfig
from core.worlds.soccer.physics import Ball, FieldBounds, Player, SoccerPhysics

logger = logging.getLogger(__name__)


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
        **config_overrides,
    ):
        """Initialize the soccer world backend.

        Args:
            seed: Random seed for deterministic simulation
            config: Complete SoccerWorldConfig (if provided, overrides are ignored)
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
        self.rng = random.Random(seed)

        # Game state (initialized in reset())
        self._players: Dict[PlayerID, Player] = {}
        self._ball: Optional[Ball] = None
        self._field: Optional[FieldBounds] = None
        self._physics: Optional[SoccerPhysics] = None

        # Match state
        self._frame = 0
        self._score = {"left": 0, "right": 0}
        self._play_mode = "before_kick_off"
        self._possession_tracker: Dict[TeamID, int] = {"left": 0, "right": 0}
        self._last_ball_distances: Dict[PlayerID, float] = {}

        # Event tracking
        self._recent_events: List[Dict[str, Any]] = []

        self.supports_fast_step = True

    def reset(
        self, seed: Optional[int] = None, config: Optional[Dict[str, Any]] = None
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
        self.rng = random.Random(reset_seed)

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
            rng=self.rng,
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
                team=team, team_size=self._config.team_size, rng=self.rng
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
        )

    def step(
        self, actions_by_agent: Optional[Dict[str, Any]] = None
    ) -> StepResult:
        """Advance the simulation by one timestep.

        Args:
            actions_by_agent: Dict mapping player_id to action dict
                Action dict format: {
                    "move_target": {"x": float, "y": float} or None,
                    "face_angle": float or None,
                    "kick_power": float (0-1),
                    "kick_angle": float (radians),
                }

        Returns:
            StepResult with observations, events, metrics, and done flag
        """
        fast_step = bool(actions_by_agent and actions_by_agent.get(FAST_STEP_ACTION))
        self._recent_events = []

        # Process player actions
        if actions_by_agent:
            self._process_actions(actions_by_agent)

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
        )

    def get_current_snapshot(self) -> Dict[str, Any]:
        """Get current world state for rendering."""
        return self._build_snapshot()

    def get_current_metrics(self) -> Dict[str, Any]:
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

    def _process_actions(self, actions_by_agent: Dict[str, Any]) -> None:
        """Process actions from all agents."""
        for player_id, action_data in actions_by_agent.items():
            if player_id == FAST_STEP_ACTION or player_id not in self._players:
                continue

            player = self._players[player_id]

            # Parse action
            try:
                action = SoccerAction.from_dict(action_data)
            except Exception as e:
                logger.warning(f"Invalid action for {player_id}: {e}")
                continue

            # Validate action
            if not action.is_valid():
                logger.warning(f"Invalid action bounds for {player_id}")
                continue

            # Update movement
            move_target = action.move_target
            face_angle = action.face_angle
            self._physics.update_player_movement(player, move_target, face_angle)

            # Handle kick
            if action.kick_power > 0:
                success = self._physics.kick_ball(
                    player, self._ball, action.kick_power, action.kick_angle
                )
                if success:
                    # Consume stamina for kick
                    player.stamina = max(
                        0.0, player.stamina - self._config.stamina_kick_cost
                    )
                    self._recent_events.append({
                        "type": "kick",
                        "player_id": player_id,
                        "team": player.team,
                        "power": action.kick_power,
                        "frame": self._frame,
                    })

    def _update_physics(self) -> None:
        """Update ball and player physics."""
        # Update ball
        self._physics.update_ball(self._ball)

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
                player.stamina = max(
                    0.0, player.stamina - self._config.stamina_sprint_cost
                )
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

        self._recent_events.append({
            "type": "goal",
            "team": scoring_team,
            "scorer": scorer_id,
            "frame": self._frame,
            "score": self._score.copy(),
        })

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
        result = self._physics.find_closest_player_to_ball(
            self._ball, list(self._players.values())
        )

        if result:
            closest_player, distance = result
            # Consider possession if within 2 meters
            if distance < 2.0:
                self._possession_tracker[closest_player.team] += 1

    def _build_observations(self) -> Dict[PlayerID, Dict[str, Any]]:
        """Build observations for all players."""
        observations = {}

        for player_id, player in self._players.items():
            # Get teammates and opponents
            teammates = [
                p for pid, p in self._players.items()
                if p.team == player.team and pid != player_id
            ]
            opponents = [
                p for p in self._players.values()
                if p.team != player.team
            ]

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

    def _build_snapshot(self) -> Dict[str, Any]:
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

    def calculate_rewards(self) -> Dict[PlayerID, SoccerReward]:
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
            result = self._physics.find_closest_player_to_ball(
                self._ball, [player]
            )
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
