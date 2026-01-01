"""In-process soccer training world backend.

Implements a lightweight 2D soccer simulation with CodePool policies,
energy accounting, and per-agent fitness tracking.
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.code_pool import CodePool
from core.entities.base import LifeStage
from core.fish.energy_component import EnergyComponent
from core.genetics import Genome
from core.genetics.trait import GeneticTrait
from core.math_utils import Vector2
from core.worlds.interfaces import FAST_STEP_ACTION, MultiAgentWorldBackend, StepResult
from core.worlds.soccer_training.config import SoccerTrainingConfig
from core.worlds.soccer_training.interfaces import SoccerAction

try:  # Optional legacy action support
    from core.policies.soccer_interfaces import SoccerAction as LegacySoccerAction
except Exception:  # pragma: no cover - defensive fallback
    LegacySoccerAction = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

TeamID = str
PlayerID = str

LEFT_TEAM: TeamID = "left"
RIGHT_TEAM: TeamID = "right"

SOCCER_POLICY_KIND = "soccer_policy"


@dataclass
class PlayerStats:
    goals: int = 0
    assists: int = 0
    possessions: int = 0
    kicks: int = 0
    energy_gained: float = 0.0
    energy_spent: float = 0.0

    def fitness(self, config: SoccerTrainingConfig) -> float:
        _ = config
        return self.energy_gained - self.energy_spent


@dataclass
class SoccerPlayer:
    player_id: PlayerID
    team: TeamID
    position: Vector2
    velocity: Vector2
    facing_angle: float
    energy_component: EnergyComponent
    genome: Genome
    stats: PlayerStats = field(default_factory=PlayerStats)
    life_stage: LifeStage = LifeStage.ADULT

    @property
    def energy(self) -> float:
        return self.energy_component.energy

    @property
    def max_energy(self) -> float:
        return self.energy_component.max_energy

    def modify_energy(self, amount: float) -> float:
        before = self.energy_component.energy
        self.energy_component.modify_energy(amount)
        return self.energy_component.energy - before

    def energy_ratio(self) -> float:
        return self.energy_component.get_energy_ratio()

    def distance_to(self, target: Vector2) -> float:
        return Vector2.distance_between(self.position, target)


@dataclass
class SoccerBall:
    position: Vector2
    velocity: Vector2
    radius: float


@dataclass(frozen=True)
class FieldBounds:
    width: float
    height: float
    goal_width: float

    @property
    def x_min(self) -> float:
        return -self.width / 2.0

    @property
    def x_max(self) -> float:
        return self.width / 2.0

    @property
    def y_min(self) -> float:
        return -self.height / 2.0

    @property
    def y_max(self) -> float:
        return self.height / 2.0

    def is_goal(self, position: Vector2) -> Optional[TeamID]:
        goal_half = self.goal_width / 2.0
        if position.x < self.x_min and abs(position.y) <= goal_half:
            return RIGHT_TEAM
        if position.x > self.x_max and abs(position.y) <= goal_half:
            return LEFT_TEAM
        return None


class SoccerTrainingWorldBackendAdapter(MultiAgentWorldBackend):
    """Lightweight soccer training world using in-process physics."""

    def __init__(
        self,
        seed: Optional[int] = None,
        config: Optional[SoccerTrainingConfig] = None,
        code_pool: Optional[CodePool] = None,
        **config_overrides: Any,
    ) -> None:
        self._seed = seed
        if config is None:
            config = SoccerTrainingConfig(**config_overrides)
        self._config = config
        self._config.validate()

        self._rng = random.Random(seed)
        self._players: Dict[PlayerID, SoccerPlayer] = {}
        self._ball: Optional[SoccerBall] = None
        self._field: Optional[FieldBounds] = None
        self._frame = 0
        self._score = {LEFT_TEAM: 0, RIGHT_TEAM: 0}
        self._recent_events: List[Dict[str, Any]] = []
        self._last_touch: Optional[Tuple[PlayerID, TeamID, int]] = None
        self._prev_touch: Optional[Tuple[PlayerID, TeamID, int]] = None

        self.code_pool = code_pool
        self.supports_fast_step = True

    def reset(
        self, seed: Optional[int] = None, config: Optional[Dict[str, Any]] = None
    ) -> StepResult:
        reset_seed = seed if seed is not None else self._seed
        self._rng = random.Random(reset_seed)

        if config:
            merged = {**self._config.to_dict(), **config}
            self._config = SoccerTrainingConfig.from_dict(merged)
            self._config.validate()

        self._field = FieldBounds(
            width=self._config.field_width,
            height=self._config.field_height,
            goal_width=self._config.goal_width,
        )
        self._ball = SoccerBall(
            position=Vector2(0.0, 0.0),
            velocity=Vector2(0.0, 0.0),
            radius=self._config.ball_radius,
        )
        self._players = self._spawn_players()
        self._frame = 0
        self._score = {LEFT_TEAM: 0, RIGHT_TEAM: 0}
        self._recent_events = []
        self._last_touch = None
        self._prev_touch = None

        return StepResult(
            obs_by_agent=self._build_observations(),
            snapshot=self._build_snapshot(),
            events=[],
            metrics=self.get_current_metrics(),
            done=False,
            info={"frame": self._frame, "seed": reset_seed},
        )

    def step(self, actions_by_agent: Optional[Dict[str, Any]] = None) -> StepResult:
        fast_step = bool(actions_by_agent and actions_by_agent.get(FAST_STEP_ACTION))
        self._recent_events = []

        if actions_by_agent is None or not actions_by_agent:
            actions_by_agent = self._actions_from_policies()
        else:
            actions_by_agent = dict(actions_by_agent)

        self._process_actions(actions_by_agent)
        self._update_positions()
        self._consume_energy()
        self._update_ball()

        scoring_team = self._field.is_goal(self._ball.position) if self._field else None
        if scoring_team:
            self._handle_goal(scoring_team)

        self._update_possession()

        self._frame += 1
        done = False

        events = [] if fast_step else list(self._recent_events)
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
        return self._build_snapshot()

    def get_current_metrics(self) -> Dict[str, Any]:
        return {
            "frame": self._frame,
            "score_left": self._score[LEFT_TEAM],
            "score_right": self._score[RIGHT_TEAM],
            "num_players": len(self._players),
            "ball_speed": self._ball.velocity.length() if self._ball else 0.0,
        }

    def get_fitness_summary(self) -> Dict[str, Any]:
        per_agent: Dict[str, Any] = {}
        for player_id, player in self._players.items():
            per_agent[player_id] = {
                "team": player.team,
                "goals": player.stats.goals,
                "assists": player.stats.assists,
                "possessions": player.stats.possessions,
                "kicks": player.stats.kicks,
                "energy": player.energy,
                "fitness": player.energy,
            }

        team_fitness = {
            LEFT_TEAM: sum(p.energy for p in self._players.values() if p.team == LEFT_TEAM),
            RIGHT_TEAM: sum(p.energy for p in self._players.values() if p.team == RIGHT_TEAM),
        }

        return {
            "score": dict(self._score),
            "team_fitness": team_fitness,
            "agent_fitness": per_agent,
        }

    def assign_team_policy(self, team: TeamID, component_id: str) -> None:
        for player in self._players.values():
            if player.team != team:
                continue
            player.genome.behavioral.code_policy_kind = GeneticTrait(SOCCER_POLICY_KIND)
            player.genome.behavioral.code_policy_component_id = GeneticTrait(component_id)

    def _spawn_players(self) -> Dict[PlayerID, SoccerPlayer]:
        players: Dict[PlayerID, SoccerPlayer] = {}
        if self._field is None:
            return players

        for team in (LEFT_TEAM, RIGHT_TEAM):
            x_pos = -self._field.width / 4.0 if team == LEFT_TEAM else self._field.width / 4.0
            y_positions = self._evenly_spaced_positions(self._config.team_size)
            for idx, y_pos in enumerate(y_positions, start=1):
                player_id = f"{team}_{idx}"
                genome = Genome.random(use_algorithm=False, rng=self._rng)
                energy_component = EnergyComponent(
                    max_energy=self._config.energy_max,
                    base_metabolism=self._config.base_metabolism,
                    initial_energy_ratio=1.0,
                )
                facing = 0.0 if team == LEFT_TEAM else math.pi
                players[player_id] = SoccerPlayer(
                    player_id=player_id,
                    team=team,
                    position=Vector2(x_pos, y_pos),
                    velocity=Vector2(0.0, 0.0),
                    facing_angle=facing,
                    energy_component=energy_component,
                    genome=genome,
                )
        return players

    def _evenly_spaced_positions(self, count: int) -> List[float]:
        if self._field is None or count <= 0:
            return []
        usable_height = self._field.height * 0.8
        start = -usable_height / 2.0
        spacing = usable_height / max(1, count)
        return [start + spacing * (i + 0.5) for i in range(count)]

    def _actions_from_policies(self) -> Dict[str, Any]:
        actions: Dict[str, Any] = {}
        for player_id, player in self._players.items():
            action = self._action_from_policy(player)
            actions[player_id] = action.to_dict()
        return actions

    def _action_from_policy(self, player: SoccerPlayer) -> SoccerAction:
        policy_kind = player.genome.behavioral.code_policy_kind
        component_id = player.genome.behavioral.code_policy_component_id
        kind_val = policy_kind.value if policy_kind else None
        comp_val = component_id.value if component_id else None

        if kind_val != SOCCER_POLICY_KIND or not comp_val or self.code_pool is None:
            return self._default_policy(player)

        func = self.code_pool.get_callable(comp_val)
        if func is None:
            return self._default_policy(player)

        observation = self._build_observation(player)
        try:
            output = func(observation, self._rng)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning("Soccer policy %s failed: %s", comp_val, exc)
            return self._default_policy(player)

        action = self._coerce_action(output, player)
        if action is None or not action.is_valid():
            return self._default_policy(player)
        return action

    def _default_policy(self, player: SoccerPlayer) -> SoccerAction:
        if self._ball is None:
            return SoccerAction()
        to_ball = self._ball.position - player.position
        target_angle = math.atan2(to_ball.y, to_ball.x)
        angle_delta = self._normalize_angle(target_angle - player.facing_angle)
        turn_command = self._clamp(angle_delta / self._config.player_turn_rate, -1.0, 1.0)
        dash = 1.0 if to_ball.length_squared() > 0.5 else 0.0
        kick = 1.0 if to_ball.length() <= self._config.kick_range else 0.0
        return SoccerAction(turn=turn_command, dash=dash, kick_power=kick, kick_angle=0.0)

    def _coerce_action(self, output: Any, player: SoccerPlayer) -> Optional[SoccerAction]:
        if isinstance(output, SoccerAction):
            return output
        if LegacySoccerAction is not None and isinstance(output, LegacySoccerAction):
            return self._legacy_action_to_action(output, player)
        if isinstance(output, dict):
            if "turn" in output or "dash" in output:
                return SoccerAction.from_dict(output)
            if "move_target" in output or "face_angle" in output:
                if LegacySoccerAction is not None:
                    return self._legacy_action_to_action(
                        LegacySoccerAction.from_dict(output), player
                    )
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

    def _legacy_action_to_action(self, legacy_action: Any, player: SoccerPlayer) -> SoccerAction:
        turn = 0.0
        dash = 0.0
        if legacy_action.face_angle is not None:
            angle_delta = self._normalize_angle(legacy_action.face_angle - player.facing_angle)
            turn = self._clamp(angle_delta / self._config.player_turn_rate, -1.0, 1.0)
        if legacy_action.move_target is not None:
            to_target = Vector2(
                legacy_action.move_target.x - player.position.x,
                legacy_action.move_target.y - player.position.y,
            )
            if to_target.length_squared() > 0.5:
                target_angle = math.atan2(to_target.y, to_target.x)
                angle_delta = self._normalize_angle(target_angle - player.facing_angle)
                turn = self._clamp(angle_delta / self._config.player_turn_rate, -1.0, 1.0)
                dash = 1.0
        return SoccerAction(
            turn=turn,
            dash=dash,
            kick_power=legacy_action.kick_power,
            kick_angle=legacy_action.kick_angle,
        )

    def _process_actions(self, actions_by_agent: Dict[str, Any]) -> None:
        if self._ball is None:
            return

        for player_id in sorted(self._players.keys()):
            player = self._players[player_id]
            if player_id == FAST_STEP_ACTION:
                continue
            action_data = actions_by_agent.get(player_id)
            action = self._coerce_action(action_data, player) if action_data else SoccerAction()
            if action is None or not action.is_valid():
                action = SoccerAction()

            action = self._clamp_action(action)
            if player.energy <= 0.0:
                action = SoccerAction(turn=action.turn, dash=0.0, kick_power=0.0, kick_angle=0.0)

            self._apply_turn(player, action.turn)
            self._apply_dash(player, action.dash)
            if action.kick_power > 0.0:
                self._apply_kick(player, action)

    def _apply_turn(self, player: SoccerPlayer, turn_command: float) -> None:
        delta = self._clamp(turn_command, -1.0, 1.0) * self._config.player_turn_rate
        player.facing_angle = self._normalize_angle(player.facing_angle + delta)

    def _apply_dash(self, player: SoccerPlayer, dash_command: float) -> None:
        dash = self._clamp(dash_command, -1.0, 1.0)
        if dash == 0.0:
            return

        energy_cost = abs(dash) * self._config.dash_energy_cost
        delta = player.modify_energy(-energy_cost)
        if delta < 0:
            player.stats.energy_spent += -delta

        direction = Vector2(math.cos(player.facing_angle), math.sin(player.facing_angle))
        accel = direction * (dash * self._config.player_acceleration)
        player.velocity.add_inplace(accel)
        player.velocity.limit_inplace(self._config.player_max_speed)

    def _apply_kick(self, player: SoccerPlayer, action: SoccerAction) -> None:
        if self._ball is None:
            return
        distance = player.distance_to(self._ball.position)
        if distance > self._config.kick_range:
            return

        kick_power = self._clamp(action.kick_power, 0.0, 1.0)
        direction = player.facing_angle + action.kick_angle
        velocity = Vector2(math.cos(direction), math.sin(direction))
        velocity = velocity * (kick_power * self._config.ball_kick_power_max)
        self._ball.velocity = velocity
        player.stats.kicks += 1
        self._prev_touch = self._last_touch
        self._last_touch = (player.player_id, player.team, self._frame)
        self._recent_events.append(
            {
                "type": "kick",
                "player_id": player.player_id,
                "team": player.team,
                "frame": self._frame,
            }
        )

    def _update_positions(self) -> None:
        if self._field is None:
            return

        for player in self._players.values():
            player.velocity.mul_inplace(self._config.player_friction)
            player.position.add_inplace(player.velocity)
            self._clamp_player(player)

    def _consume_energy(self) -> None:
        for player in self._players.values():
            before = player.energy
            breakdown = player.energy_component.consume_energy(
                player.velocity,
                self._config.player_max_speed,
                player.life_stage,
                time_modifier=1.0,
                size=1.0,
            )
            spent = before - player.energy
            if spent > 0:
                player.stats.energy_spent += spent
            if breakdown.get("total", 0.0) < 0:
                logger.warning("Negative energy consumption detected for %s", player.player_id)

    def _update_ball(self) -> None:
        if self._ball is None or self._field is None:
            return

        self._ball.position.add_inplace(self._ball.velocity)
        self._ball.velocity.mul_inplace(self._config.ball_friction)
        if self._ball.velocity.length() < 0.001:
            self._ball.velocity.update(0.0, 0.0)

        if self._ball.position.y < self._field.y_min:
            self._ball.position.y = self._field.y_min
            self._ball.velocity.y = abs(self._ball.velocity.y)
        elif self._ball.position.y > self._field.y_max:
            self._ball.position.y = self._field.y_max
            self._ball.velocity.y = -abs(self._ball.velocity.y)

        if self._ball.position.x < self._field.x_min:
            if abs(self._ball.position.y) > self._field.goal_width / 2.0:
                self._ball.position.x = self._field.x_min
                self._ball.velocity.x = abs(self._ball.velocity.x)
        elif self._ball.position.x > self._field.x_max:
            if abs(self._ball.position.y) > self._field.goal_width / 2.0:
                self._ball.position.x = self._field.x_max
                self._ball.velocity.x = -abs(self._ball.velocity.x)

    def _handle_goal(self, scoring_team: TeamID) -> None:
        self._score[scoring_team] += 1
        scorer_id = None
        assist_id = None

        if self._last_touch and self._last_touch[1] == scoring_team:
            scorer_id = self._last_touch[0]
        if (
            self._prev_touch
            and self._prev_touch[1] == scoring_team
            and self._prev_touch[0] != scorer_id
        ):
            assist_id = self._prev_touch[0]

        if scorer_id and scorer_id in self._players:
            scorer = self._players[scorer_id]
            scorer.stats.goals += 1
            delta = scorer.modify_energy(self._config.goal_reward)
            if delta > 0:
                scorer.stats.energy_gained += delta

        if assist_id and assist_id in self._players:
            assister = self._players[assist_id]
            assister.stats.assists += 1
            delta = assister.modify_energy(self._config.assist_reward)
            if delta > 0:
                assister.stats.energy_gained += delta

        self._recent_events.append(
            {
                "type": "goal",
                "team": scoring_team,
                "scorer": scorer_id,
                "assist": assist_id,
                "frame": self._frame,
                "score": dict(self._score),
            }
        )

        self._reset_after_goal()

    def _reset_after_goal(self) -> None:
        if self._ball is None:
            return
        self._ball.position.update(0.0, 0.0)
        self._ball.velocity.update(0.0, 0.0)
        if self._field is None:
            return
        for team in (LEFT_TEAM, RIGHT_TEAM):
            positions = self._kickoff_positions(team)
            team_players = sorted(
                (p for p in self._players.values() if p.team == team),
                key=lambda p: p.player_id,
            )
            for player, pos in zip(team_players, positions):
                player.position.update(pos.x, pos.y)
                player.velocity.update(0.0, 0.0)
                player.facing_angle = 0.0 if team == LEFT_TEAM else math.pi

    def _kickoff_positions(self, team: TeamID) -> List[Vector2]:
        if self._field is None:
            return []
        x_pos = -self._field.width / 4.0 if team == LEFT_TEAM else self._field.width / 4.0
        y_positions = self._evenly_spaced_positions(self._config.team_size)
        return [Vector2(x_pos, y_pos) for y_pos in y_positions]

    def _update_possession(self) -> None:
        if self._ball is None:
            return
        closest = None
        closest_dist_sq = float("inf")
        for player in self._players.values():
            dist_sq = Vector2.distance_squared_between(player.position, self._ball.position)
            if dist_sq < closest_dist_sq:
                closest_dist_sq = dist_sq
                closest = player
        if closest is None:
            return
        if math.sqrt(closest_dist_sq) <= self._config.possession_radius:
            closest.stats.possessions += 1
            delta = closest.modify_energy(self._config.possession_reward)
            if delta > 0:
                closest.stats.energy_gained += delta

    def _build_observations(self) -> Dict[PlayerID, Dict[str, Any]]:
        observations: Dict[PlayerID, Dict[str, Any]] = {}
        for player_id, player in self._players.items():
            observations[player_id] = self._build_observation(player)
        return observations

    def _build_observation(self, player: SoccerPlayer) -> Dict[str, Any]:
        ball = self._ball
        if ball is None:
            ball_rel_pos = Vector2(0.0, 0.0)
            ball_rel_vel = Vector2(0.0, 0.0)
        else:
            ball_rel_pos = ball.position - player.position
            ball_rel_vel = ball.velocity - player.velocity

        teammate_info = self._nearest_player(player, same_team=True)
        opponent_info = self._nearest_player(player, same_team=False)

        goal_x = self._field.x_max if player.team == LEFT_TEAM else self._field.x_min
        goal_vector = Vector2(goal_x - player.position.x, 0.0 - player.position.y)
        goal_dir = goal_vector.normalize()

        observation = {
            "ball_relative_pos": {"x": ball_rel_pos.x, "y": ball_rel_pos.y},
            "ball_relative_vel": {"x": ball_rel_vel.x, "y": ball_rel_vel.y},
            "nearest_teammate": teammate_info,
            "nearest_opponent": opponent_info,
            "goal_direction": {"x": goal_dir.x, "y": goal_dir.y},
            "stamina": player.energy_ratio(),
            "energy": player.energy,
        }
        return observation

    def _nearest_player(self, player: SoccerPlayer, *, same_team: bool) -> Optional[Dict[str, Any]]:
        closest = None
        closest_dist_sq = float("inf")
        for other in self._players.values():
            if other.player_id == player.player_id:
                continue
            if same_team and other.team != player.team:
                continue
            if not same_team and other.team == player.team:
                continue
            dist_sq = Vector2.distance_squared_between(player.position, other.position)
            if dist_sq < closest_dist_sq:
                closest_dist_sq = dist_sq
                closest = other
        if closest is None:
            return None
        rel_pos = closest.position - player.position
        rel_vel = closest.velocity - player.velocity
        return {
            "relative_pos": {"x": rel_pos.x, "y": rel_pos.y},
            "relative_vel": {"x": rel_vel.x, "y": rel_vel.y},
            "distance": math.sqrt(closest_dist_sq),
        }

    def _clamp_player(self, player: SoccerPlayer) -> None:
        if self._field is None:
            return
        radius = self._config.player_radius
        min_x = self._field.x_min + radius
        max_x = self._field.x_max - radius
        min_y = self._field.y_min + radius
        max_y = self._field.y_max - radius

        if player.position.x < min_x:
            player.position.x = min_x
            player.velocity.x = abs(player.velocity.x)
        elif player.position.x > max_x:
            player.position.x = max_x
            player.velocity.x = -abs(player.velocity.x)
        if player.position.y < min_y:
            player.position.y = min_y
            player.velocity.y = abs(player.velocity.y)
        elif player.position.y > max_y:
            player.position.y = max_y
            player.velocity.y = -abs(player.velocity.y)

    def _build_snapshot(self) -> Dict[str, Any]:
        if self._ball is None or self._field is None:
            return {}
        return {
            "frame": self._frame,
            "world_type": "soccer_training",
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
                    "energy": player.energy,
                }
                for player in self._players.values()
            ],
            "field": {
                "width": self._field.width,
                "height": self._field.height,
                "goal_width": self._field.goal_width,
            },
            "score": dict(self._score),
        }

    @staticmethod
    def _clamp(value: float, min_val: float, max_val: float) -> float:
        return max(min_val, min(max_val, value))

    def _clamp_action(self, action: SoccerAction) -> SoccerAction:
        turn = self._clamp(action.turn, -1.0, 1.0)
        dash = self._clamp(action.dash, -1.0, 1.0)
        kick_power = self._clamp(action.kick_power, 0.0, 1.0)
        kick_angle = self._clamp(action.kick_angle, -math.pi, math.pi)
        return SoccerAction(
            turn=turn,
            dash=dash,
            kick_power=kick_power,
            kick_angle=kick_angle,
        )

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        while angle > math.pi:
            angle -= 2.0 * math.pi
        while angle < -math.pi:
            angle += 2.0 * math.pi
        return angle
