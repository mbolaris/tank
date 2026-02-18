import logging
import uuid
from typing import TYPE_CHECKING, Any, Optional

from core.auto_evaluate_poker import AutoEvaluatePokerGame

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class BenchmarkCommands:
    if TYPE_CHECKING:
        world: Any
        standard_poker_series: Any

        def _create_error_response(self, error_msg: str) -> dict[str, Any]: ...

        def _invalidate_state_cache(self) -> None: ...

    def _cmd_standard_poker_series(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """Handle 'standard_poker_series' command."""
        logger.info("Starting standard poker benchmark series...")
        try:
            # Get top fish from leaderboard
            # Intentional: poker benchmark only applies to fish agents in TankWorld v1
            entities_list = self.world.get_entities_for_snapshot()
            fish_list = [e for e in entities_list if getattr(e, "snapshot_type", None) == "fish"]

            if len(fish_list) < 1:
                logger.warning("No fish available for benchmark series")
                return self._create_error_response("Need at least 1 fish to run benchmark series")

            # Get top 3 fish from leaderboard
            num_fish = min(3, len(fish_list))
            ecosystem = getattr(self.world, "ecosystem", None)
            if not ecosystem:
                return self._create_error_response("Ecosystem not available for benchmark")

            leaderboard = ecosystem.get_poker_leaderboard(
                fish_list=fish_list, limit=num_fish, sort_by="net_energy"
            )

            # Build list of fish player data
            fish_players = []
            for i in range(num_fish):
                if i < len(leaderboard):
                    # Use leaderboard entry
                    entry = leaderboard[i]
                    fish = next(
                        (f for f in fish_list if f.fish_id == entry["fish_id"]), fish_list[i]
                    )
                    fish_name = (
                        f"{entry['algorithm'][:15]} (Gen {entry['generation']}) #{entry['fish_id']}"
                    )
                else:
                    # Fallback to fish from list
                    fish = fish_list[i]
                    algo_name = "Unknown"
                    if hasattr(fish, "genome") and hasattr(fish.genome, "behavioral"):
                        behavior_algorithm = fish.genome.behavioral.behavior_algorithm.value
                        if behavior_algorithm:
                            algo_name = behavior_algorithm.algorithm_id
                    fish_name = f"{algo_name[:15]} (Gen {fish.generation}) #{fish.fish_id}"

                fish_players.append(
                    {
                        "name": fish_name,
                        "fish_id": fish.fish_id,
                        "generation": fish.generation,
                        "poker_strategy": (
                            fish.genome.behavioral.poker_strategy.value
                            if fish.genome.behavioral.poker_strategy
                            else None
                        ),
                    }
                )

            # Create benchmark series with multiple fish
            game_id = str(uuid.uuid4())
            standard_energy = data.get("standard_energy", 500.0) if data else 500.0
            max_hands = data.get("max_hands", 1000) if data else 1000

            self.standard_poker_series = AutoEvaluatePokerGame(
                game_id=game_id,
                player_pool=fish_players,
                standard_energy=standard_energy,
                max_hands=max_hands,
                small_blind=5.0,
                big_blind=10.0,
            )

            logger.info(
                f"Created standard series {game_id} with {len(fish_players)} fish vs Standard"
            )

            # Run the series (this will complete all hands)
            final_stats = self.standard_poker_series.run_evaluation()

            # Convert stats to dict for JSON serialization
            stats_dict = {
                "hands_played": final_stats.hands_played,
                "hands_remaining": final_stats.hands_remaining,
                "game_over": final_stats.game_over,
                "winner": final_stats.winner,
                "reason": final_stats.reason,
                "players": final_stats.players,  # List of all player stats
                "performance_history": final_stats.performance_history,
            }

            logger.info(
                f"Standard series complete: {final_stats.winner} after {final_stats.hands_played} hands!"
            )

            # Return the final stats to the frontend
            return {
                "success": True,
                "stats": stats_dict,
            }

        except Exception as e:
            logger.error(f"Error running benchmark series: {e}", exc_info=True)
            return self._create_error_response(f"Failed to run benchmark series: {e!s}")

    def _cmd_set_plant_energy_input(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """Handle 'set_plant_energy_input' command.

        Adjusts the runtime plant energy input rate (minimum energy gain per frame).

        Args:
            data: Dictionary with 'rate' key (float, 0.0-1.0 suggested range)
        """
        if not data or "rate" not in data:
            return self._create_error_response("Missing 'rate' parameter")

        rate = float(data["rate"])

        # Clamp to reasonable range (0.0 to 2.0)
        rate = max(0.0, min(2.0, rate))

        # Access the simulation config through the world's engine
        if hasattr(self.world, "engine") and hasattr(self.world.engine, "config"):
            config = self.world.engine.config
            if hasattr(config, "plant"):
                config.plant.plant_energy_input_rate = rate
                logger.info(f"Plant energy input rate set to {rate:.3f}")
                return {"success": True, "rate": rate}
        elif hasattr(self.world, "simulation_config"):
            config = self.world.simulation_config
            if hasattr(config, "plant"):
                config.plant.plant_energy_input_rate = rate
                logger.info(f"Plant energy input rate set to {rate:.3f}")
                return {"success": True, "rate": rate}

        return self._create_error_response("Could not access plant configuration")
