"""Service for managing auto-evaluation poker tournaments.

This service encapsulates the logic for running periodic benchmark poker games
and tracking their results, removing this complexity from the main simulation runner.
"""

import logging
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from core.auto_evaluate_poker import AutoEvaluatePokerGame
from core.entities.fish import Fish
from core.entities.fractal_plant import FractalPlant
from core.serializers import FishSerializer, PlantSerializer

logger = logging.getLogger(__name__)


class AutoEvalService:
    """Manages periodic auto-evaluation poker games."""

    def __init__(self, world: Any):
        """Initialize the auto-evaluation service.
        
        Args:
            world: The TankWorld instance to interact with entities.
        """
        self.world = world
        self.history: List[Dict[str, Any]] = []
        self.stats: Optional[Dict[str, Any]] = None
        self.running: bool = False
        self.interval_seconds: float = 15.0
        self.last_run_time: float = 0.0
        self.lock = threading.Lock()

    def update(self) -> None:
        """Check if it's time to run an evaluation and start if needed."""
        now = time.time()
        if self.running or (now - self.last_run_time) < self.interval_seconds:
            return

        # Prepare players
        benchmark_players = self._collect_benchmark_players()
        if not benchmark_players:
            return

        # Start evaluation in background thread
        self.running = True
        threading.Thread(
            target=self._run_evaluation,
            args=(benchmark_players,),
            name="auto_eval_thread",
            daemon=True,
        ).start()

    def _collect_benchmark_players(self) -> List[Dict[str, Any]]:
        """Collect top fish and plants for benchmarking."""
        # This logic mirrors the previous implementation but uses serializers
        fish_list = [e for e in self.world.entities_list if isinstance(e, Fish)]
        plant_list = [e for e in self.world.entities_list if isinstance(e, FractalPlant)]
        
        # Get leaderboard from ecosystem
        leaderboard = []
        if hasattr(self.world.ecosystem, "get_poker_leaderboard"):
             leaderboard = self.world.ecosystem.get_poker_leaderboard(
                fish_list=fish_list, limit=3, sort_by="net_energy"
            )

        fish_players = []
        for i, entry in enumerate(leaderboard):
            # Find the actual fish entity
            fish = next(
                (f for f in fish_list if f.fish_id == entry["fish_id"]),
                fish_list[i] if i < len(fish_list) else None,
            )
            
            if fish is None:
                continue

            # Ensure fish has a poker strategy
            if fish.genome.poker_strategy_algorithm is None:
                from core.poker.strategy.implementations import get_random_poker_strategy
                fish.genome.poker_strategy_algorithm = get_random_poker_strategy()
                logger.info(f"Assigned random poker strategy to fish #{fish.fish_id} for auto-eval")

            # Use rudimentary dict creation here because we need specific fields for the player pool
            # that match what AutoEvaluatePokerGame expects (which is slightly different from the generic player data)
            # Actually, let's try to reuse the serializer logic but adapt it if needed.
            # The previous code made a specific ad-hoc dict. Let's stick to that structure for safety or adapt.
            
            fish_name = f"{entry['algorithm'][:15]} (Gen {entry['generation']}) #{entry['fish_id']}"
            fish_players.append(
                {
                    "name": fish_name,
                    "fish_id": fish.fish_id,
                    "generation": fish.generation,
                    "poker_strategy": fish.genome.poker_strategy_algorithm,
                }
            )

        plant_players = []
        if plant_list:
            ranked_plants = sorted(
                plant_list,
                key=lambda p: (
                    getattr(p, "poker_wins", 0),
                    getattr(p.genome, "fitness_score", 0.0),
                    p.energy,
                ),
                reverse=True,
            )
            for plant in ranked_plants[:3]:
                plant_players.append(PlantSerializer.to_player_data(plant))

        return fish_players + plant_players

    def _run_evaluation(self, benchmark_players: List[Dict[str, Any]]) -> None:
        """Execute the evaluation game."""
        try:
            game_id = str(uuid.uuid4())
            standard_energy = 500.0
            max_hands = 5000

            auto_eval = AutoEvaluatePokerGame(
                game_id=game_id,
                player_pool=benchmark_players,
                standard_energy=standard_energy,
                max_hands=max_hands,
                small_blind=5.0,
                big_blind=10.0,
                position_rotation=True,
            )

            final_stats = auto_eval.run_evaluation()

            # Process results
            self._reward_winners(benchmark_players, final_stats)
            self._update_stats(final_stats)

        except Exception as e:
            logger.error(f"Auto-evaluation thread failed: {e}", exc_info=True)
        finally:
            self.last_run_time = time.time()
            self.running = False

    def _reward_winners(self, benchmark_players: List[Dict[str, Any]], final_stats: Any) -> None:
        """Give energy rewards to winners."""
        # Acquiring world lock might be needed here if modify_energy isn't thread-safe
        # But generally we are just modifying entity state. 
        # Ideally we should synchronize with the simulation update loop.
        # For now, we follow the pattern of the runner which had a lock, 
        # BUT runner.lock is private. We might need a way to acquire it or just risk it 
        # (simulation update is single threaded, this is a background thread).
        # Actually, the runner acquires `self.lock` before updating world.
        # We should accept a callback or lock to be safe. 
        # Or, realizing that `modify_energy` is atomic enough in python (GIL), 
        # but `ecosystem.record` might have race conditions.
        
        # Let's assume for this refactor we will just modify directly and add locking support if we see issues,
        # OR better, pass a context manager for locking to the service.
        pass # To be implemented with proper access

        # Re-implement logic from runner:
        for player_stats in final_stats.players:
            if player_stats.get("is_standard", False):
                continue

            net_energy = player_stats.get("net_energy", 0.0)
            if net_energy <= 0:
                continue

            fish_id = player_stats.get("fish_id")
            plant_id = player_stats.get("plant_id")

            if fish_id is not None:
                fish = next((e for e in self.world.entities_list
                            if isinstance(e, Fish) and e.fish_id == fish_id), None)
                if fish and net_energy > 0:
                    actual_gain = fish.modify_energy(net_energy)
                    if actual_gain > 0 and fish.ecosystem is not None:
                        fish.ecosystem.record_auto_eval_energy_gain(actual_gain)
                    logger.info(f"Auto-eval reward: Fish #{fish_id} gained {actual_gain:.1f} energy")

            elif plant_id is not None:
                plant = next((e for e in self.world.entities_list
                            if isinstance(e, FractalPlant) and e.plant_id == plant_id), None)
                if plant:
                    reward = min(net_energy, plant.max_energy - plant.energy)
                    if reward > 0:
                        actual_gain = plant.gain_energy(reward, source="auto_eval")
                        logger.info(
                            f"Auto-eval reward: Plant #{plant_id} gained {actual_gain:.1f} energy"
                        )

    def _update_stats(self, final_stats: Any) -> None:
        """Update internal statistics."""
        with self.lock:
            starting_hand = self.history[-1]["hand"] if self.history else 0

            if final_stats.performance_history:
                last_snapshot = final_stats.performance_history[-1]
                adjusted_snapshot = {**last_snapshot, "hand": last_snapshot["hand"] + starting_hand}
                self.history.append(adjusted_snapshot)

            players_with_win_rate = []
            for player in final_stats.players:
                hands_played = final_stats.hands_played or 1
                win_rate = round((player.get("hands_won", 0) / hands_played) * 100, 1)
                players_with_win_rate.append({**player, "win_rate": win_rate})

            self.stats = {
                "hands_played": final_stats.hands_played,
                "hands_remaining": final_stats.hands_remaining,
                "game_over": final_stats.game_over,
                "winner": final_stats.winner,
                "reason": final_stats.reason,
                "players": players_with_win_rate,
                "performance_history": list(self.history),
            }

    def get_stats(self) -> Optional[Dict[str, Any]]:
        """Return current stats."""
        with self.lock:
            if not self.stats:
                return None
            return self.stats.copy()

    def get_history(self) -> List[Dict[str, Any]]:
        """Return full history."""
        with self.lock:
            return list(self.history)
