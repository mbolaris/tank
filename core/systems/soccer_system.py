"""Soccer system for ball physics and goal checking."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional

from core.math_utils import Vector2
from core.systems.base import BaseSystem

if TYPE_CHECKING:
    from core.entities.ball import Ball
    from core.entities.goal_zone import GoalZone
    from core.simulation.engine import SimulationEngine

logger = logging.getLogger(__name__)


class SoccerSystem(BaseSystem):
    """Manages soccer gameplay physics and rules."""

    def __init__(self, engine: SimulationEngine, name: str = "soccer"):
        super().__init__(engine, name)
        self.ball: Optional[Ball] = None
        self.goals: List[GoalZone] = []
        self.enabled = True

    def register_ball(self, ball: Ball) -> None:
        """Register the ball entity."""
        self.ball = ball

    def add_goal(self, goal: GoalZone) -> None:
        """Add a goal zone."""
        self.goals.append(goal)

    def _do_update(self, frame: int) -> Optional[SystemResult]:
        """Update system state (physics, rules)."""
        from core.systems.base import SystemResult

        # Debug logging every second (30 frames)
        if frame % 30 == 0:
            logger.debug(
                f"SOCCER: _do_update called frame={frame}, ball={self.ball is not None}, goals={len(self.goals)}"
            )

        if not self.ball or not self.goals:
            self._ensure_initialized()

        if not self.ball:
            if frame % 30 == 0:
                logger.warning("SOCCER: No ball available, skipping update")
            return SystemResult.empty()

        # 1. Update Ball Physics
        self.ball.update()

        # 1.5 Handle Agent Collisions - Goal-Directed Kicking
        if self.engine.environment and self.goals:
            import math

            ball_radius = self.ball.radius
            ball_pos = self.ball.pos

            # Track ball position for potential-based shaping
            ball_pos_before = Vector2(ball_pos.x, ball_pos.y)

            # Sort goals by x-position: goal_A is left, goal_B is right
            sorted_goals = sorted(self.goals, key=lambda g: g.pos.x)
            goal_A = sorted_goals[0]  # Left goal
            goal_B = sorted_goals[-1]  # Right goal

            agent_count = 0

            for entity in self.engine.entities_list:
                if entity is self.ball or not hasattr(entity, "pos") or not hasattr(entity, "vel"):
                    continue

                # Only Fish can kick the ball (not Food or LiveFood)
                from core.entities import Fish

                if not isinstance(entity, Fish):
                    continue

                agent_count += 1
                agent_radius = getattr(entity, "radius", 16.0)

                dist_sq = Vector2.distance_squared_between(ball_pos, entity.pos)
                min_dist = ball_radius + agent_radius

                if dist_sq < min_dist * min_dist:
                    # Assign team based on fish_id: even = Team A, odd = Team B
                    fish_id = getattr(entity, "fish_id", 0)
                    is_team_a = (fish_id % 2) == 0

                    # Team A aims at right goal (B), Team B aims at left goal (A)
                    target_goal = goal_B if is_team_a else goal_A
                    goal_center = Vector2(target_goal.pos.x, target_goal.pos.y)

                    # COLLISION - Kick ball TOWARD the team's target goal!
                    # (Debug logging removed for production)

                    # Calculate direction TO THE GOAL (smart kick)
                    kick_dir = goal_center - ball_pos
                    if kick_dir.length_squared() > 0.01:
                        kick_dir = kick_dir.normalize()
                    else:
                        # Ball already at goal, kick away from entity
                        kick_dir = (ball_pos - entity.pos).normalize()

                    # Power based on agent speed
                    agent_speed = entity.vel.length()
                    kick_power = 30.0 + agent_speed * 15.0

                    angle = math.atan2(kick_dir.y, kick_dir.x)
                    self.ball.kick(kick_power, angle, id(entity))

                    # SHAPING REWARD: Small bonus just for kicking toward goal
                    if hasattr(entity, "gain_energy"):
                        entity.gain_energy(2.0)  # Small reward for engagement
                        # Set visual effect for HUD display
                        entity.soccer_effect_state = {
                            "type": "kick",
                            "amount": 2.0,
                            "timer": 10,  # ~1 second at broadcast rate
                        }

            # POTENTIAL-BASED SHAPING: Reward entity if ball moved closer to their team's goal
            if self.ball.last_kicker_id:
                ball_pos_after = self.ball.pos
                # Find the kicker and their target goal
                for entity in self.engine.entities_list:
                    if id(entity) == self.ball.last_kicker_id:
                        from core.entities import Fish

                        if isinstance(entity, Fish) and hasattr(entity, "gain_energy"):
                            # Determine kicker's team and target goal
                            fish_id = getattr(entity, "fish_id", 0)
                            is_team_a = (fish_id % 2) == 0
                            target_goal = goal_B if is_team_a else goal_A
                            goal_center = Vector2(target_goal.pos.x, target_goal.pos.y)

                            import math

                            dist_before = math.sqrt(
                                Vector2.distance_squared_between(ball_pos_before, goal_center)
                            )
                            dist_after = math.sqrt(
                                Vector2.distance_squared_between(ball_pos_after, goal_center)
                            )

                            if dist_after < dist_before - 5.0:  # Ball moved significantly closer
                                bonus = min((dist_before - dist_after) * 0.1, 5.0)  # Up to 5 energy
                                entity.gain_energy(bonus)
                                # Set visual effect for HUD display
                                entity.soccer_effect_state = {
                                    "type": "progress",
                                    "amount": round(bonus, 1),
                                    "timer": 10,  # ~1 second at broadcast rate
                                }
                        break

            if frame % 300 == 0:  # Log less frequently
                logger.debug(f"SOCCER: {agent_count} agents. Ball at {ball_pos}")

        # 2. Check Goals
        goals_events = 0
        detail_msg = {}

        for goal in self.goals:
            if goal.check_goal(self.ball):
                self._handle_goal_scored(goal)
                goals_events += 1
                detail_msg = {"goal_scored": goal.team_id}
                break  # Only one goal per frame

        return SystemResult(
            entities_affected=1, events_emitted=goals_events, details=detail_msg  # ball
        )

    def _handle_goal_scored(self, goal: GoalZone) -> None:
        """Handle goal event and award energy to scorer."""
        logger.info(f"GOAL SCORED in Goal {goal.team_id}!")

        # Find and reward the last kicker
        scorer_found = False
        if self.ball and self.ball.last_kicker_id:
            for entity in self.engine.entities_list:
                if id(entity) == self.ball.last_kicker_id:
                    # Award energy to the scoring entity
                    if hasattr(entity, "gain_energy"):
                        entity.gain_energy(50.0)
                        # Set visual effect for HUD display (GOAL - big reward!)
                        entity.soccer_effect_state = {
                            "type": "goal",
                            "amount": 50.0,
                            "timer": 30,  # ~3 seconds at broadcast rate
                        }
                        entity_name = getattr(entity, "fish_id", type(entity).__name__)
                        logger.info(f"SOCCER: {entity_name} scored a goal - awarded 50 energy!")
                        scorer_found = True
                    break

        if not scorer_found:
            logger.debug("SOCCER: No scorer found to reward (ball may not have been kicked)")

        # Increment score
        goal.score_count += 1

        # Reset Ball to Center
        if self.engine.environment:
            cx = self.engine.environment.width / 2
            cy = self.engine.environment.height / 2
            self.ball.pos = Vector2(cx, cy)
            self.ball.vel = Vector2(0.0, 0.0)
            self.ball.last_kicker_id = None

    def _ensure_initialized(self) -> None:
        """Self-heal: Find or spawn soccer entities if missing (respects config)."""
        if not self.engine.environment:
            logger.debug("SOCCER: _ensure_initialized skipped - no environment")
            return

        # Check config settings
        config = getattr(self.engine, "config", None)
        soccer_cfg = getattr(config, "soccer", None) if config else None

        logger.info(
            f"SOCCER: _ensure_initialized called. config={config is not None}, soccer_cfg={soccer_cfg is not None}"
        )

        # If tank practice is disabled, don't spawn anything
        if soccer_cfg and not soccer_cfg.tank_practice_enabled:
            logger.info("SOCCER: Tank practice disabled, skipping soccer init")
            return

        from core.entities.ball import Ball
        from core.entities.goal_zone import GoalZone

        # 1. Recover references from existing entities (e.g. after snapshot restore)
        found_ball = False
        found_goals = 0
        for entity in self.engine.entities_list:
            if isinstance(entity, Ball):
                self.ball = entity
                found_ball = True
            elif isinstance(entity, GoalZone):
                if entity not in self.goals:
                    self.goals.append(entity)
                found_goals += 1

        # 2. Spawn if missing (and config allows)
        env = self.engine.environment
        width = env.width
        height = env.height

        # Only spawn ball if ball is visible in config (or config unavailable for legacy)
        ball_visible = soccer_cfg.tank_ball_visible if soccer_cfg else True
        if not found_ball and ball_visible:
            logger.info("SoccerSystem: Spawning missing Ball")
            ball = Ball(env, width / 2, height / 2)
            self.engine.add_entity(ball)
            self.ball = ball

        # Only spawn goals if goals are visible in config
        goals_visible = soccer_cfg.tank_goals_visible if soccer_cfg else True
        if found_goals < 2 and goals_visible:
            logger.info("SoccerSystem: Spawning missing Goals")

            # Goal A
            goal_a = GoalZone(env, 50.0, height / 2, "A")
            self.engine.add_entity(goal_a)
            self.goals.append(goal_a)

            # Goal B
            goal_b = GoalZone(env, width - 50.0, height / 2, "B")
            self.engine.add_entity(goal_b)
            self.goals.append(goal_b)
