import logging
from dataclasses import asdict
from typing import TYPE_CHECKING, Any, Dict, Optional

from core.minigames.soccer import SelectionStrategy, create_soccer_match, finalize_soccer_match

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SoccerCommands:
    if TYPE_CHECKING:
        soccer_match: Any
        world: Any

        def _create_error_response(self, error_msg: str) -> Dict[str, Any]: ...

        def _invalidate_state_cache(self) -> None: ...

    def _cmd_set_soccer_league_enabled(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle 'set_soccer_league_enabled' command."""
        if not data or "enabled" not in data:
            return self._create_error_response("Missing 'enabled' parameter")

        enabled = bool(data["enabled"])

        engine = getattr(self.world, "engine", None)
        config = getattr(engine, "config", None) if engine is not None else None
        if config is None:
            config = getattr(self.world, "simulation_config", None)

        soccer_cfg = getattr(config, "soccer", None) if config is not None else None
        if soccer_cfg is None:
            return self._create_error_response("Could not access soccer configuration")

        soccer_cfg.enabled = enabled
        logger.info("Soccer league enabled set to %s", enabled)
        self._invalidate_state_cache()
        return {"success": True, "enabled": enabled}

    def _cmd_set_soccer_league_config(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle 'set_soccer_league_config' command."""
        if not data:
            return self._create_error_response("Missing config payload")

        engine = getattr(self.world, "engine", None)
        config = getattr(engine, "config", None) if engine is not None else None
        if config is None:
            config = getattr(self.world, "simulation_config", None)

        soccer_cfg = getattr(config, "soccer", None) if config is not None else None
        if soccer_cfg is None:
            return self._create_error_response("Could not access soccer configuration")

        errors = []

        def clamp_int(value: Any, min_value: int, max_value: int) -> int:
            try:
                ivalue = int(value)
            except (TypeError, ValueError):
                raise ValueError("must be an integer")
            return max(min_value, min(max_value, ivalue))

        def clamp_float(value: Any, min_value: float, max_value: float) -> float:
            try:
                fvalue = float(value)
            except (TypeError, ValueError):
                raise ValueError("must be a number")
            return max(min_value, min(max_value, fvalue))

        field_map = {
            "match_every_frames": ("match_every_frames", lambda v: clamp_int(v, 1, 600)),
            "duration_frames": ("duration_frames", lambda v: clamp_int(v, 10, 2000)),
            "duration_cycles": ("duration_frames", lambda v: clamp_int(v, 10, 2000)),
            "matches_per_tick": ("matches_per_tick", lambda v: clamp_int(v, 0, 5)),
            "cycles_per_frame": ("cycles_per_frame", lambda v: clamp_int(v, 1, 20)),
            "min_players": ("min_players", lambda v: clamp_int(v, 2, 200)),
            "num_players": ("num_players", lambda v: clamp_int(v, 2, 200)),
            "team_size": ("team_size", lambda v: clamp_int(v, 0, 100)),
            "entry_fee_energy": ("entry_fee_energy", lambda v: clamp_float(v, 0.0, 500.0)),
            "reward_multiplier": ("reward_multiplier", lambda v: clamp_float(v, 0.1, 5.0)),
            "repro_credit_award": ("repro_credit_award", lambda v: clamp_float(v, 0.0, 10.0)),
            "repro_credit_required": ("repro_credit_required", lambda v: clamp_float(v, 0.0, 10.0)),
        }

        for key, (attr, caster) in field_map.items():
            if key not in data:
                continue
            try:
                setattr(soccer_cfg, attr, caster(data[key]))
            except ValueError as exc:
                errors.append(f"{key} {exc}")

        if "reward_mode" in data:
            mode = str(data["reward_mode"]).strip().lower()
            if mode not in {"pot_payout", "refill_to_max"}:
                errors.append("reward_mode must be 'pot_payout' or 'refill_to_max'")
            else:
                soccer_cfg.reward_mode = mode

        if "repro_reward_mode" in data:
            mode = str(data["repro_reward_mode"]).strip().lower()
            if mode not in {"credits"}:
                errors.append("repro_reward_mode must be 'credits'")
            else:
                soccer_cfg.repro_reward_mode = mode

        if "selection_strategy" in data:
            soccer_cfg.selection_strategy = str(data["selection_strategy"]).strip().lower()

        if "allow_repeat_within_match" in data:
            soccer_cfg.allow_repeat_within_match = bool(data["allow_repeat_within_match"])

        if "cooldown_matches" in data:
            try:
                soccer_cfg.cooldown_matches = clamp_int(data["cooldown_matches"], 0, 10)
            except ValueError as exc:
                errors.append(f"cooldown_matches {exc}")

        if errors:
            return self._create_error_response("; ".join(errors))

        logger.info("Soccer league config updated")
        self._invalidate_state_cache()
        return {"success": True}

    def _cmd_start_soccer(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle 'start_soccer' command.

        Starts a soccer match with selected fish.
        """
        try:
            num_players = data.get("num_players", 22)  # Default 22 (11 vs 11)
            seed_value = data.get("seed")
            match_id = data.get("match_id")

            seed: Optional[int]
            if seed_value is None:
                seed = None
            else:
                seed = int(seed_value)

            # Get fish-type entities for soccer match
            # Intentional: soccer currently designed for fish agents in TankWorld v1
            entities_list = self.world.get_entities_for_snapshot()
            fish_list = [e for e in entities_list if getattr(e, "snapshot_type", None) == "fish"]

            if len(fish_list) < 2:
                return self._create_error_response("Not enough fish for soccer!")

            counter = getattr(self, "_soccer_match_counter", 0)
            seed_base = getattr(self, "_seed", None)
            if seed_base is None:
                seed_base = 0

            code_source = getattr(self.world, "genome_code_pool", None)
            # Pass the view_mode so soccer can render correct avatar type
            view_mode = getattr(self, "view_mode", "side")  # "side" = tank, "top" = petri
            soccer_cfg = None
            engine = getattr(self.world, "engine", None)
            if engine is not None:
                soccer_cfg = getattr(engine.config, "soccer", None)

            strategy = SelectionStrategy.STRATIFIED
            if soccer_cfg is not None:
                try:
                    strategy = SelectionStrategy(
                        getattr(soccer_cfg, "selection_strategy", "stratified")
                    )
                except ValueError:
                    strategy = SelectionStrategy.STRATIFIED

            setup = create_soccer_match(
                fish_list,
                num_players=num_players,
                code_source=code_source,
                view_mode=view_mode,
                seed=seed,
                seed_base=seed_base,
                match_counter=counter,
                match_id=match_id,
                strategy=strategy,
                allow_repeat_within_match=bool(
                    getattr(soccer_cfg, "allow_repeat_within_match", False)
                ),
                entry_fee_energy=(
                    float(getattr(soccer_cfg, "entry_fee_energy", 0.0))
                    if soccer_cfg is not None
                    else 0.0
                ),
            )
            self.soccer_match = setup.match
            self._soccer_match_seed = setup.seed
            self._soccer_match_counter = counter + 1
            self._soccer_match_entry_fees = setup.entry_fees
            self._soccer_match_selection_seed = setup.selection_seed
            self._soccer_match_counter_current = setup.match_counter
            logger.info(
                "Started soccer match %s with %d players (view_mode=%s, seed=%s)",
                setup.match_id,
                setup.selected_count,
                view_mode,
                setup.seed,
            )

            return {
                "success": True,
                "match_id": setup.match_id,
                "seed": setup.seed,
                "state": self.soccer_match.get_state(),
            }
        except ValueError as e:
            return self._create_error_response(str(e))
        except Exception as e:
            logger.error(f"Error starting soccer match: {e}", exc_info=True)
            return self._create_error_response(f"Failed to start soccer match: {str(e)}")

    def _cmd_soccer_step(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle 'soccer_step' command.

        Steps the ongoing soccer match.
        """
        try:
            match = getattr(self, "soccer_match", None)
            if not match:
                return self._create_error_response("No active soccer match")

            # Batch multiple steps for faster gameplay (default 2 steps per request)
            num_steps = data.get("num_steps", 2)
            state = match.step(num_steps=num_steps)
            return {"success": True, "state": state}
        except Exception as e:
            logger.error(f"Error stepping soccer match: {e}", exc_info=True)
            return self._create_error_response(f"Failed to step soccer match: {str(e)}")

    def _cmd_end_soccer(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle 'end_soccer' command.

        Ends the current match and distributes rewards.
        """
        try:
            match = getattr(self, "soccer_match", None)
            if not match:
                return self._create_error_response("No active soccer match")

            outcome = None
            if match.game_over:
                soccer_cfg = None
                engine = getattr(self.world, "engine", None)
                if engine is not None:
                    soccer_cfg = getattr(engine.config, "soccer", None)

                outcome = finalize_soccer_match(
                    match,
                    seed=getattr(self, "_soccer_match_seed", None),
                    match_counter=getattr(self, "_soccer_match_counter_current", 0),
                    selection_seed=getattr(self, "_soccer_match_selection_seed", None),
                    entry_fees=getattr(self, "_soccer_match_entry_fees", None),
                    reward_mode=(
                        getattr(soccer_cfg, "reward_mode", "pot_payout")
                        if soccer_cfg is not None
                        else "pot_payout"
                    ),
                    reward_multiplier=(
                        float(getattr(soccer_cfg, "reward_multiplier", 1.0))
                        if soccer_cfg is not None
                        else 1.0
                    ),
                    repro_credit_award=(
                        float(getattr(soccer_cfg, "repro_credit_award", 0.0))
                        if soccer_cfg is not None
                        else 0.0
                    ),
                    repro_reward_mode=(
                        getattr(soccer_cfg, "repro_reward_mode", "credits")
                        if soccer_cfg is not None
                        else "credits"
                    ),
                )
                if engine:
                    engine.add_soccer_event(outcome)
                    # Update live league state in the runner too
                    state = {
                        "match_id": outcome.match_id,
                        "teams": outcome.teams,
                        "score_left": outcome.score_left,
                        "score_right": outcome.score_right,
                        "frames": outcome.frames,
                        "winner_team": outcome.winner_team,
                    }
                    # Also update engine copy for consistency
                    engine.set_soccer_league_live_state(state)

            self.soccer_match = None
            # Do NOT reset counters here
            return {
                "success": True,
                "outcome": asdict(outcome) if outcome else None,
            }
        except Exception as e:
            logger.error(f"Error ending soccer match: {e}", exc_info=True)
            return self._create_error_response(f"Failed to end soccer match: {str(e)}")

    def _cmd_set_tank_soccer_enabled(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle 'set_tank_soccer_enabled' command.

        Dynamically adds/removes physical soccer ball and goals from the tank world.
        """
        if not data or "enabled" not in data:
            return self._create_error_response("Missing 'enabled' parameter")

        enabled = bool(data["enabled"])
        engine = getattr(self.world, "engine", None)

        if engine is None:
            return self._create_error_response("World engine not available")

        # Try to update tank practice config if it exists (for persistence)
        if hasattr(engine, "config") and hasattr(engine.config, "soccer"):
            engine.config.soccer.tank_practice_enabled = enabled

        try:
            if enabled:
                self._spawn_tank_soccer(engine)
                logger.info("Tank soccer elements ENABLED")
            else:
                self._remove_tank_soccer(engine)
                logger.info("Tank soccer elements DISABLED")
        except Exception as e:
            logger.error(f"Failed to toggle tank soccer: {e}", exc_info=True)
            return self._create_error_response(f"Failed to toggle tank soccer: {str(e)}")

        self._invalidate_state_cache()
        return {"success": True, "enabled": enabled}

    def _spawn_tank_soccer(self, engine: Any) -> None:
        """Spawn soccer elements into the engine."""
        from core.entities.ball import Ball
        from core.entities.goal_zone import GoalZone, GoalZoneManager

        if not engine.environment:
            return

        # Cleanup existing first to avoid duplicates
        self._remove_tank_soccer(engine)

        width = engine.environment.width
        height = engine.environment.height
        mid_y = height / 2

        # Create ball at center
        ball = Ball(
            environment=engine.environment,
            x=width / 2,
            y=mid_y,
            decay_rate=0.94,
            max_speed=3.0,
            size=0.085,
            kickable_margin=0.7,
            kick_power_rate=0.027,
        )
        engine.request_spawn(ball)

        # Create goal manager
        goal_manager = GoalZoneManager()

        # Create goals
        goal_left = GoalZone(
            environment=engine.environment,
            x=50,
            y=mid_y,
            team="A",
            goal_id="goal_left",
            radius=40.0,
            base_energy_reward=100.0,
        )
        engine.request_spawn(goal_left)
        goal_manager.register_zone(goal_left)

        goal_right = GoalZone(
            environment=engine.environment,
            x=width - 50,
            y=mid_y,
            team="B",
            goal_id="goal_right",
            radius=40.0,
            base_energy_reward=100.0,
        )
        engine.request_spawn(goal_right)
        goal_manager.register_zone(goal_right)

        # Update environment refs
        engine.environment.ball = ball
        engine.environment.goal_manager = goal_manager

        # Update system
        if hasattr(engine, "soccer_system") and engine.soccer_system:
            engine.soccer_system.set_ball(ball)
            engine.soccer_system.set_goal_manager(goal_manager)
            engine.soccer_system.enabled = True

    def _remove_tank_soccer(self, engine: Any) -> None:
        """Remove soccer elements from the engine."""
        # Gather entities to remove using snapshot_type for generic classification
        to_remove = []
        for entity in engine.entities_list:
            entity_type = getattr(entity, "snapshot_type", None)
            if entity_type in ("ball", "goal_zone"):
                to_remove.append(entity)

        for entity in to_remove:
            engine.request_remove(entity)

        # Clear environment refs
        if engine.environment:
            if hasattr(engine.environment, "ball"):
                engine.environment.ball = None
            if hasattr(engine.environment, "goal_manager"):
                engine.environment.goal_manager = None

        # Disable system
        if hasattr(engine, "soccer_system") and engine.soccer_system:
            engine.soccer_system.set_ball(None)
            engine.soccer_system.set_goal_manager(None)
            engine.soccer_system.enabled = False
