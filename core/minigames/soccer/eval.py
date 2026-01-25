"""Deterministic soccer evaluation harness.

Runs a complete soccer episode and produces a stable result object.
Used for evolution, reward shaping, and CI determinism.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from core.entities.ball import Ball
from core.entities.goal_zone import GoalZone, GoalZoneManager
from core.math_utils import Vector2
from core.minigames.soccer.params import DEFAULT_RCSS_PARAMS, RCSSParams
from core.systems.soccer_system import SoccerSystem

if TYPE_CHECKING:
    pass


@dataclass
class SoccerEpisodeConfig:
    """Configuration for a deterministic soccer episode."""

    seed: int
    max_cycles: int
    params: RCSSParams = field(default_factory=lambda: DEFAULT_RCSS_PARAMS)
    initial_ball: tuple[float, float] | None = None
    # team -> list of (x, y) positions
    initial_players: dict[str, list[tuple[float, float]]] = field(default_factory=dict)
    reward_config: dict[str, Any] | None = None
    field_width: float = 800.0
    field_height: float = 600.0


@dataclass
class SoccerEpisodeResult:
    """Stable result object for a soccer episode."""

    seed: int
    cycles: int
    score: dict[str, int]  # team -> goals
    touches: dict[str, int]  # team -> count
    possession_cycles: dict[str, int]  # team -> cycles
    shots: dict[str, int]  # team -> count
    episode_hash: str  # stable hash of key events


class EvalEntity:
    """Minimal entity for evaluation that satisfies SoccerSystem requirements."""

    def __init__(self, fish_id: int, pos: Vector2, team: str):
        self.fish_id = fish_id
        self.pos = pos
        self.vel = Vector2(0.0, 0.0)
        self.team = team
        self.snapshot_type = "fish"
        self.energy = 100.0
        self.max_energy = 100.0
        self.soccer_effect_state = None

    def is_dead(self) -> bool:
        return False

    def modify_energy(self, amount: float, source: str = "unknown") -> float:
        self.energy = max(0.0, min(self.max_energy, self.energy + amount))
        return amount


class EvalEnvironment:
    """Minimal environment for evaluation that satisfies SoccerSystem/Ball requirements."""

    def __init__(self, width: float, height: float, seed: int):
        self.width = width
        self.height = height
        self.rng = random.Random(seed)
        self.entities_list: list[EvalEntity] = []
        self.ball: Ball | None = None
        self.goal_manager: GoalZoneManager | None = None

    def get_bounds(self) -> tuple[tuple[float, float], tuple[float, float]]:
        return ((0.0, 0.0), (self.width, self.height))

    def update_agent_position(self, agent: Any) -> None:
        """No-op for evaluation."""
        pass

    def get_fish_list(self) -> list[EvalEntity]:
        return self.entities_list


def run_soccer_episode(
    config: SoccerEpisodeConfig, policies: dict[int, Any] = None
) -> SoccerEpisodeResult:
    """Run a deterministic soccer episode.

    Args:
        config: Episode configuration
        policies: Optional mapping of fish_id -> policy objects (not fully utilized in this v1)

    Returns:
        SoccerEpisodeResult containing stats and stable hash
    """
    # 1. Setup minimal environment
    env = EvalEnvironment(config.field_width, config.field_height, config.seed)

    # 2. Setup Ball
    start_ball_pos = config.initial_ball or (config.field_width / 2, config.field_height / 2)
    env.ball = Ball(
        env,
        start_ball_pos[0],
        start_ball_pos[1],
        decay_rate=config.params.ball_decay,
        max_speed=config.params.ball_speed_max,
        size=config.params.ball_size,
        kickable_margin=config.params.kickable_margin,
        kick_power_rate=config.params.kick_power_rate,
    )

    # 3. Setup Goals
    env.goal_manager = GoalZoneManager()
    # Left goal (Team B defends, Team A scores)
    left_goal = GoalZone(env, 50, config.field_height / 2, team="B", goal_id="goal_left", radius=40)
    # Right goal (Team A defends, Team B scores)
    right_goal = GoalZone(
        env,
        config.field_width - 50,
        config.field_height / 2,
        team="A",
        goal_id="goal_right",
        radius=40,
    )
    env.goal_manager.register_zone(left_goal)
    env.goal_manager.register_zone(right_goal)

    # 4. Setup Players
    fish_id_counter = 0
    for team, positions in config.initial_players.items():
        for pos in positions:
            player = EvalEntity(fish_id_counter, Vector2(pos[0], pos[1]), team)
            env.entities_list.append(player)
            fish_id_counter += 1

    # Sort entities by fish_id for determinism
    env.entities_list.sort(key=lambda x: x.fish_id)

    # 5. Setup Engine/System
    class MockEngine:
        def __init__(self, environment):
            self.environment = environment
            self.entities_list = environment.entities_list
            self.event_bus = None
            self.rng = environment.rng

        def get_fish_list(self):
            return self.environment.get_fish_list()

    engine = MockEngine(env)
    soccer_system = SoccerSystem(engine)
    soccer_system.setup()

    # Force the soccer_system to use the engine's RNG if it has its own logic that needs it
    # Note: SoccerSystem doesn't actually have an 'rng' attribute in the provided code,
    # but some physics like kick_rand might use it if we were to support it in RCSSLiteEngine-style.
    # However, SoccerSystem currently doesn't use randomness in _process_auto_kicks.
    # To ensure seeds matter, let's add a small random nudge to initial positions.
    for entity in env.entities_list:
        entity.pos.x += env.rng.uniform(-1.0, 1.0)
        entity.pos.y += env.rng.uniform(-1.0, 1.0)

    # Statistics tracking
    score = {"A": 0, "B": 0}
    touches = {"A": 0, "B": 0}
    possession_cycles = {"A": 0, "B": 0}
    shots = {"A": 0, "B": 0}
    event_log = []

    last_kicker_id = None

    # 6. Simulation Loop
    for cycle in range(config.max_cycles):
        # 6.1 Process auto-kicks and ball physics
        # We call _do_update manually to avoid engine overhead but use its logic

        # Track if ball was kicked this cycle
        kicker_this_cycle = None

        # SoccerSystem._process_auto_kicks(cycle)
        soccer_system._process_auto_kicks(cycle)

        # Check if kicker was assigned
        if env.ball.last_kicker:
            kicker_this_cycle = env.ball.last_kicker
            kicker_id = getattr(kicker_this_cycle, "fish_id", None)
            kicker_team = getattr(kicker_this_cycle, "team", None)

            if kicker_id != last_kicker_id:
                if kicker_team:
                    touches[kicker_team] += 1
                event_log.append((cycle, "touch", kicker_team, kicker_id))
                last_kicker_id = kicker_id

            if kicker_team:
                possession_cycles[kicker_team] += 1

        # 6.2 Update ball physics
        env.ball.update(cycle)

        # 6.3 Check for goals
        if env.goal_manager:
            goal_event = env.goal_manager.check_all_goals(env.ball, cycle)
            if goal_event:
                # Determine scoring team
                scoring_team = "A" if goal_event.team == "B" else "B"
                score[scoring_team] += 1
                event_log.append((cycle, "goal", scoring_team, goal_event.scorer_id))

                # Reset ball to center
                env.ball.reset_position(config.field_width / 2, config.field_height / 2)

    # Calculate stable hash
    # Include final positions and event log
    final_state = {
        "event_log": event_log,
        "final_ball_pos": (env.ball.pos.x, env.ball.pos.y),
        "final_player_pos": [(p.fish_id, p.pos.x, p.pos.y) for p in env.entities_list],
    }
    log_str = json.dumps(final_state, sort_keys=True)
    episode_hash = hashlib.sha256(log_str.encode()).hexdigest()

    return SoccerEpisodeResult(
        seed=config.seed,
        cycles=config.max_cycles,
        score=score,
        touches=touches,
        possession_cycles=possession_cycles,
        shots=shots,  # In v1, shots are not distinct from touches toward goal
        episode_hash=episode_hash,
    )
