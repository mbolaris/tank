import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

from core.entities import Fish
from core.minigames.soccer import SelectionStrategy, create_soccer_match, finalize_soccer_match

if TYPE_CHECKING:
    from backend.simulation_runner import SimulationRunner

logger = logging.getLogger(__name__)


class SoccerCommands:
    def _cmd_set_soccer_league_enabled(
        self: "SimulationRunner", data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
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

    def _cmd_set_soccer_league_config(
        self: "SimulationRunner", data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
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

    def _cmd_start_soccer(
        self: "SimulationRunner", data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Handle 'start_soccer' command.

        Starts a soccer match with selected fish.
        """
        try:
            num_players = data.get("num_players", 22)  # Default 22 (11 vs 11)
            seed_value = data.get("seed")
            match_id = data.get("match_id")

            seed: int | None
            if seed_value is None:
                seed = None
            else:
                seed = int(seed_value)

            # Get Fish
            entities_list = self.world.get_entities_for_snapshot()
            fish_list = [e for e in entities_list if isinstance(e, Fish)]

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

    def _cmd_soccer_step(
        self: "SimulationRunner", data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
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

    def _cmd_end_soccer(self: "SimulationRunner", data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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
