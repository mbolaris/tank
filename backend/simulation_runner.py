"""Background simulation runner thread."""

import logging
import threading
import time
import uuid
from typing import Any, Dict, Optional

from backend.models import (
    EntityData,
    AutoEvaluateStats,
    PokerEventData,
    PokerLeaderboardEntry,
    PokerStatsData,
    SimulationUpdate,
    StatsData,
)
from core import entities, movement_strategy
from core.auto_evaluate_poker import AutoEvaluatePokerGame
from core.constants import FILES, FRAME_RATE, SCREEN_HEIGHT, SCREEN_WIDTH, SPAWN_MARGIN_PIXELS
from core.entities import Fish
from core.genetics import Genome
from core.human_poker_game import HumanPokerGame

# Use absolute imports assuming tank/ is in PYTHONPATH
from core.tank_world import TankWorld, TankWorldConfig

logger = logging.getLogger(__name__)


class SimulationRunner:
    """Runs the simulation in a background thread and provides state updates."""

    def __init__(self, seed: Optional[int] = None):
        """Initialize the simulation runner.

        Args:
            seed: Optional random seed for deterministic behavior
        """
        # Create TankWorld configuration
        config = TankWorldConfig(headless=True)

        # Create TankWorld instance
        self.world = TankWorld(config=config, seed=seed)
        self.world.setup()

        # Start paused to prevent initial fish from aging before frontend sees them
        # This ensures all fish (initial and spawned) appear at baby size when first created
        self.world.paused = True

        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

        # Target frame rate
        self.fps = FRAME_RATE
        self.frame_time = 1.0 / self.fps

        # Performance: Throttle WebSocket updates to reduce serialization overhead
        # Cache state and only rebuild every N frames (reduces from 30 FPS to 15 FPS)
        self.websocket_update_interval = 2  # Send every 2 frames
        self.frames_since_websocket_update = 0
        self._cached_state: Optional[SimulationUpdate] = None
        self._cached_state_frame: Optional[int] = None

        # Human poker game management
        self.human_poker_game: Optional[HumanPokerGame] = None

        # Static benchmark poker series management
        self.standard_poker_series: Optional[AutoEvaluatePokerGame] = None

        # Ongoing auto-evaluation against static baseline
        self.auto_eval_history: list[dict[str, Any]] = []
        self.auto_eval_stats: Optional[dict[str, Any]] = None
        self.auto_eval_running: bool = False
        self.auto_eval_interval_seconds = 120.0
        self.last_auto_eval_time = 0.0
        self.auto_eval_lock = threading.Lock()

    def _create_error_response(self, error_msg: str) -> Dict[str, Any]:
        """Create a standardized error response.

        Args:
            error_msg: The error message to return

        Returns:
            Dictionary with success=False and error message
        """
        return {"success": False, "error": error_msg}

    def _invalidate_state_cache(self) -> None:
        """Clear cached state so the next request rebuilds fresh data."""

        self._cached_state = None
        self._cached_state_frame = None
        self.frames_since_websocket_update = 0

    @property
    def engine(self):
        """Expose the underlying simulation engine for compatibility/testing."""

        return self.world.engine

    def _create_fish_player_data(self, fish: Fish, include_aggression: bool = False) -> Dict[str, Any]:
        """Create fish player data dictionary.

        Args:
            fish: The fish entity
            include_aggression: If True, include aggression field for human poker games

        Returns:
            Dictionary with fish player data
        """
        algo_name = fish.genome.behavior_algorithm.algorithm_id
        player_data = {
            "fish_id": fish.fish_id,
            "name": f"{algo_name[:15]} (Gen {fish.generation})",
            "energy": fish.energy,
            "algorithm": algo_name,
        }

        if include_aggression:
            player_data["aggression"] = getattr(fish.genome, "aggression", 0.5)

        return player_data

    def start(self, start_paused: bool = False):
        """Start the simulation in a background thread.

        Args:
            start_paused: Whether to keep the simulation paused after starting.
                Defaults to False to allow immediate frame progression in tests
                and headless runs. The backend can override to start paused
                until WebSocket broadcasting is ready.
        """

        if not self.running:
            # Override the initial paused state based on caller preference
            self.world.paused = start_paused

            self.running = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()

    def stop(self):
        """Stop the simulation."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)

    def _run_loop(self):
        """Main simulation loop."""
        logger.info("Simulation loop: Starting")
        frame_count = 0
        try:
            while self.running:
                try:
                    loop_start = time.time()
                    frame_count += 1

                    with self.lock:
                        if not self.world.paused:
                            try:
                                self.world.update()
                            except Exception as e:
                                logger.error(
                                    f"Simulation loop: Error updating world at frame {frame_count}: {e}",
                                    exc_info=True,
                                )
                                # Continue running even if update fails

                    self._start_auto_evaluation_if_needed()

                    # Maintain frame rate
                    elapsed = time.time() - loop_start
                    sleep_time = max(0, self.frame_time - elapsed)
                    time.sleep(sleep_time)

                except Exception as e:
                    logger.error(f"Simulation loop: Unexpected error at frame {frame_count}: {e}", exc_info=True)
                    # Continue running even if there's an error
                    time.sleep(self.frame_time)

        except Exception as e:
            logger.error(f"Simulation loop: Fatal error, loop exiting: {e}", exc_info=True)
        finally:
            logger.info(f"Simulation loop: Ended after {frame_count} frames")

    def _start_auto_evaluation_if_needed(self) -> None:
        """Periodically benchmark top fish against the static evaluator."""

        now = time.time()
        if self.auto_eval_running or (now - self.last_auto_eval_time) < self.auto_eval_interval_seconds:
            return

        with self.lock:
            fish_list = [e for e in self.world.entities_list if isinstance(e, Fish)]
            leaderboard = self.world.ecosystem.get_poker_leaderboard(
                fish_list=fish_list, limit=3, sort_by="net_energy"
            )

        if not leaderboard:
            return

        fish_players = []
        for i, entry in enumerate(leaderboard):
            fish = next(
                (f for f in fish_list if f.fish_id == entry["fish_id"]),
                fish_list[i] if i < len(fish_list) else None,
            )
            if fish is None:
                continue

            fish_name = f"{entry['algorithm'][:15]} (Gen {entry['generation']}) #{entry['fish_id']}"
            fish_players.append(
                {
                    "name": fish_name,
                    "fish_id": fish.fish_id,
                    "generation": fish.generation,
                    "poker_strategy": fish.genome.poker_strategy_algorithm,
                }
            )

        if not fish_players:
            return

        self.auto_eval_running = True
        threading.Thread(
            target=self._run_auto_evaluation,
            args=(fish_players,),
            name="auto_eval_thread",
            daemon=True,
        ).start()

    def _run_auto_evaluation(self, fish_players: list[dict[str, Any]]):
        """Execute a background auto-evaluation series."""

        try:
            game_id = str(uuid.uuid4())
            standard_energy = 500.0
            max_hands = 300

            auto_eval = AutoEvaluatePokerGame(
                game_id=game_id,
                fish_players=fish_players,
                standard_energy=standard_energy,
                max_hands=max_hands,
                small_blind=5.0,
                big_blind=10.0,
            )

            final_stats = auto_eval.run_evaluation()

            with self.auto_eval_lock:
                starting_hand = self.auto_eval_history[-1]["hand"] if self.auto_eval_history else 0
                extended_history = [
                    {**snapshot, "hand": snapshot["hand"] + starting_hand}
                    for snapshot in final_stats.performance_history
                ]
                self.auto_eval_history.extend(extended_history)

                players_with_win_rate = []
                for player in final_stats.players:
                    hands_played = final_stats.hands_played or 1
                    win_rate = round((player.get("hands_won", 0) / hands_played) * 100, 1)
                    players_with_win_rate.append({**player, "win_rate": win_rate})

                self.auto_eval_stats = {
                    "hands_played": final_stats.hands_played,
                    "hands_remaining": final_stats.hands_remaining,
                    "game_over": final_stats.game_over,
                    "winner": final_stats.winner,
                    "reason": final_stats.reason,
                    "players": players_with_win_rate,
                    "performance_history": list(self.auto_eval_history),
                }

            self._invalidate_state_cache()
        except Exception as e:
            logger.error(f"Auto-evaluation thread failed: {e}", exc_info=True)
        finally:
            self.last_auto_eval_time = time.time()
            self.auto_eval_running = False

    def get_state(self) -> SimulationUpdate:
        """Get current simulation state for WebSocket broadcast.

        Uses caching to reduce serialization overhead - only rebuilds state
        every N frames instead of every single frame.

        Returns:
            SimulationUpdate with current entities and stats
        """
        current_frame = self.world.frame_count

        # Fast path: if the simulation hasn't advanced, reuse the cached state
        if self._cached_state is not None and current_frame == self._cached_state_frame:
            return self._cached_state

        # Check if we should rebuild state this frame
        self.frames_since_websocket_update += 1
        should_rebuild = self.frames_since_websocket_update >= self.websocket_update_interval

        # Return cached state if available and not time to rebuild
        if not should_rebuild and self._cached_state is not None:
            return self._cached_state

        # Reset counter and rebuild state
        self.frames_since_websocket_update = 0

        with self.lock:
            entities_data = []

            # Convert entities to serializable format
            for entity in self.world.entities_list:
                entity_data = self._entity_to_data(entity)
                if entity_data:
                    entities_data.append(entity_data)

            # Sort entities by z-order (background to foreground)
            # This ensures castles and plants are rendered first (background)
            z_order = {
                'castle': 0,
                'plant': 1,
                'food': 2,
                'crab': 3,
                'fish': 4,
                'jellyfish': 5,
            }
            entities_data.sort(key=lambda e: z_order.get(e.type, 999))

            # Get ecosystem stats
            stats = self.world.get_stats()

            # Create poker stats data
            poker_stats_dict = stats.get("poker_stats", {})
            poker_stats_data = PokerStatsData(
                total_games=poker_stats_dict.get("total_games", 0),
                total_wins=poker_stats_dict.get("total_wins", 0),
                total_losses=poker_stats_dict.get("total_losses", 0),
                total_ties=poker_stats_dict.get("total_ties", 0),
                total_energy_won=poker_stats_dict.get("total_energy_won", 0.0),
                total_energy_lost=poker_stats_dict.get("total_energy_lost", 0.0),
                net_energy=poker_stats_dict.get("net_energy", 0.0),
                best_hand_rank=poker_stats_dict.get("best_hand_rank", 0),
                best_hand_name=poker_stats_dict.get("best_hand_name", "None"),
                # Advanced metrics
                win_rate=poker_stats_dict.get("win_rate", 0.0),
                win_rate_pct=poker_stats_dict.get("win_rate_pct", "0.0%"),
                roi=poker_stats_dict.get("roi", 0.0),
                vpip=poker_stats_dict.get("vpip", 0.0),
                vpip_pct=poker_stats_dict.get("vpip_pct", "0.0%"),
                bluff_success_rate=poker_stats_dict.get("bluff_success_rate", 0.0),
                bluff_success_pct=poker_stats_dict.get("bluff_success_pct", "0.0%"),
                button_win_rate=poker_stats_dict.get("button_win_rate", 0.0),
                button_win_rate_pct=poker_stats_dict.get("button_win_rate_pct", "0.0%"),
                off_button_win_rate=poker_stats_dict.get("off_button_win_rate", 0.0),
                off_button_win_rate_pct=poker_stats_dict.get("off_button_win_rate_pct", "0.0%"),
                positional_advantage=poker_stats_dict.get("positional_advantage", 0.0),
                positional_advantage_pct=poker_stats_dict.get("positional_advantage_pct", "0.0%"),
                aggression_factor=poker_stats_dict.get("aggression_factor", 0.0),
                avg_hand_rank=poker_stats_dict.get("avg_hand_rank", 0.0),
                total_folds=poker_stats_dict.get("total_folds", 0),
                preflop_folds=poker_stats_dict.get("preflop_folds", 0),
                postflop_folds=poker_stats_dict.get("postflop_folds", 0),
                showdown_win_rate=poker_stats_dict.get("showdown_win_rate", "0.0%"),
                avg_fold_rate=poker_stats_dict.get("avg_fold_rate", "0.0%"),
            )

            stats_data = StatsData(
                frame=self.world.frame_count,
                population=stats.get("total_population", 0),
                generation=stats.get("current_generation", 0),
                max_generation=stats.get(
                    "max_generation", stats.get("current_generation", 0)
                ),
                births=stats.get("total_births", 0),
                deaths=stats.get("total_deaths", 0),
                capacity=stats.get("capacity_usage", "0%"),
                time=stats.get("time_string", "Day"),
                death_causes=stats.get("death_causes", {}),
                fish_count=stats.get("fish_count", 0),
                food_count=stats.get("food_count", 0),
                plant_count=stats.get("plant_count", 0),
                total_energy=stats.get("total_energy", 0.0),
                poker_stats=poker_stats_data,
            )

            # Get recent poker events
            poker_events = []
            recent_events = self.world.engine.poker_events
            for event in recent_events:
                # Filter out evaluation events if any slipped in
                if "Standard Algorithm" in event["message"] or "Auto-eval" in event["message"]:
                    continue
                    
                poker_events.append(
                    PokerEventData(
                        frame=event["frame"],
                        winner_id=event["winner_id"],
                        loser_id=event["loser_id"],
                        winner_hand=event["winner_hand"],
                        loser_hand=event["loser_hand"],
                        energy_transferred=event["energy_transferred"],
                        message=event["message"],
                        is_jellyfish=event["is_jellyfish"],
                    )
                )

            # Get poker leaderboard
            poker_leaderboard = []
            if hasattr(self.world.ecosystem, "get_poker_leaderboard"):
                # Get fish list from entities
                fish_list = [e for e in self.world.entities_list if isinstance(e, Fish)]
                leaderboard_data = self.world.ecosystem.get_poker_leaderboard(
                    fish_list=fish_list, limit=10, sort_by="net_energy"
                )
                poker_leaderboard = [PokerLeaderboardEntry(**entry) for entry in leaderboard_data]

            auto_eval_stats: Optional[AutoEvaluateStats] = None
            with self.auto_eval_lock:
                if self.auto_eval_stats:
                    try:
                        # Optimization: Truncate history to last 50 entries to prevent payload explosion
                        # The full history is preserved in self.auto_eval_history for the final report
                        stats_copy = self.auto_eval_stats.copy()
                        if "performance_history" in stats_copy:
                            history = stats_copy["performance_history"]
                            if len(history) > 50:
                                stats_copy["performance_history"] = history[-50:]

                        auto_eval_stats = AutoEvaluateStats(**stats_copy)
                    except Exception:
                        logger.error("Failed to serialize auto evaluation stats", exc_info=True)

            state = SimulationUpdate(
                frame=self.world.frame_count,
                elapsed_time=(
                    self.world.engine.elapsed_time
                    if hasattr(self.world.engine, "elapsed_time")
                    else self.world.frame_count * 33
                ),
                entities=entities_data,
                stats=stats_data,
                poker_events=poker_events,
                poker_leaderboard=poker_leaderboard,
                auto_evaluation=auto_eval_stats,
            )

            # Cache the state for reuse
            self._cached_state = state
            self._cached_state_frame = current_frame
            return state

    def _entity_to_data(self, entity: entities.Agent) -> Optional[EntityData]:
        """Convert an entity to EntityData.

        Args:
            entity: The entity to convert

        Returns:
            EntityData or None if conversion failed
        """
        try:
            base_data = {
                "id": id(entity),  # Use object id as unique identifier
                "x": entity.pos.x,
                "y": entity.pos.y,
                "width": entity.width,
                "height": entity.height,
                "vel_x": entity.vel.x if hasattr(entity, "vel") else 0,
                "vel_y": entity.vel.y if hasattr(entity, "vel") else 0,
            }

            if isinstance(entity, entities.Fish):
                genome_data = None
                if hasattr(entity, "genome"):
                    genome_data = {
                        "speed": entity.genome.speed_modifier,
                        "size": entity.size,  # Use actual size (includes baby stage growth)
                        "color_hue": entity.genome.color_hue,
                        # Visual traits for parametric fish templates
                        "template_id": entity.genome.template_id,
                        "fin_size": entity.genome.fin_size,
                        "tail_size": entity.genome.tail_size,
                        "body_aspect": entity.genome.body_aspect,
                        "eye_size": entity.genome.eye_size,
                        "pattern_intensity": entity.genome.pattern_intensity,
                        "pattern_type": entity.genome.pattern_type,
                    }

                # Map sprite/genome data to a friendly species label for the frontend
                species_label = None
                sprite_name = getattr(entity, "species", "")
                if "george" in sprite_name:
                    species_label = "solo"
                elif "school" in sprite_name:
                    species_label = "schooling"

                if species_label is None and hasattr(entity, "genome"):
                    algo_id = getattr(entity.genome.behavior_algorithm, "algorithm_id", "").lower()
                    if "neural" in algo_id:
                        species_label = "neural"
                    elif "school" in algo_id:
                        species_label = "schooling"
                    else:
                        species_label = "algorithmic"

                return EntityData(
                    type="fish",
                    energy=entity.energy,
                    generation=entity.generation if hasattr(entity, "generation") else 0,
                    age=entity.age if hasattr(entity, "age") else 0,
                    species=species_label,
                    genome_data=genome_data,
                    **base_data,
                )

            elif isinstance(entity, entities.Food):
                return EntityData(
                    type="food",
                    food_type=entity.food_type if hasattr(entity, "food_type") else 0,
                    **base_data,
                )

            elif isinstance(entity, entities.Plant):
                return EntityData(
                    type="plant",
                    plant_type=entity.plant_type if hasattr(entity, "plant_type") else 1,
                    **base_data,
                )

            elif isinstance(entity, entities.Crab):
                return EntityData(
                    type="crab",
                    energy=entity.energy if hasattr(entity, "energy") else 100,
                    **base_data,
                )

            elif isinstance(entity, entities.Castle):
                return EntityData(type="castle", **base_data)

            elif isinstance(entity, entities.Jellyfish):
                return EntityData(
                    type='jellyfish',
                    energy=entity.energy if hasattr(entity, 'energy') else 1000,
                    jellyfish_id=entity.jellyfish_id if hasattr(entity, 'jellyfish_id') else 0,
                    **base_data
                )

            return None

        except Exception as e:
            logger.error("Error converting entity: %s", e, exc_info=True)
            return None

    def handle_command(self, command: str, data: Optional[Dict[str, Any]] = None):
        """Handle a command from the client.

        Args:
            command: Command type ('add_food', 'spawn_fish', 'pause', 'resume', 'reset')
            data: Optional command data
        """
        with self.lock:
            if command == "add_food":
                # Add food at random position
                x = self.world.rng.randint(0, SCREEN_WIDTH)
                food = entities.Food(
                    self.world.environment,
                    x,
                    0,
                    source_plant=None,
                    allow_stationary_types=False,
                    screen_width=SCREEN_WIDTH,
                    screen_height=SCREEN_HEIGHT,
                )
                food.pos.y = 0
                self.world.add_entity(food)
                self._invalidate_state_cache()

            elif command == "spawn_fish":
                # Spawn a new fish at random position
                try:
                    logger.info("Spawn fish command received")

                    # Random spawn position (avoid edges)
                    x = self.world.rng.randint(
                        SPAWN_MARGIN_PIXELS, SCREEN_WIDTH - SPAWN_MARGIN_PIXELS
                    )
                    y = self.world.rng.randint(
                        SPAWN_MARGIN_PIXELS, SCREEN_HEIGHT - SPAWN_MARGIN_PIXELS
                    )

                    logger.info(f"Creating fish at position ({x}, {y})")

                    # Create new fish with random genome
                    genome = Genome.random(use_algorithm=True)
                    new_fish = entities.Fish(
                        self.world.environment,
                        movement_strategy.AlgorithmicMovement(),
                        FILES["schooling_fish"][0],
                        x,
                        y,
                        4,  # Base speed
                        genome=genome,
                        generation=0,
                        ecosystem=self.world.ecosystem,
                        screen_width=SCREEN_WIDTH,
                        screen_height=SCREEN_HEIGHT,
                    )
                    self.world.add_entity(new_fish)
                    fish_count = len([e for e in self.world.entities_list if isinstance(e, entities.Fish)])
                    logger.info(f"Successfully spawned new fish at ({x}, {y}). Total fish count: {fish_count}")
                    self._invalidate_state_cache()
                except Exception as e:
                    logger.error(f"Error spawning fish: {e}", exc_info=True)

            elif command == "pause":
                self.world.pause()
                self._invalidate_state_cache()

            elif command == "resume":
                self.world.resume()
                self._invalidate_state_cache()

            elif command == "reset":
                # Reset simulation
                self.world.reset()
                self._invalidate_state_cache()

            elif command == "start_poker":
                # Start a new poker game with top 3 fish
                logger.info("Starting human poker game...")
                try:
                    # Get top 3 fish from leaderboard
                    fish_list = [e for e in self.world.entities_list if isinstance(e, Fish)]

                    if len(fish_list) < 3:
                        logger.warning(f"Not enough fish to start poker game (need 3, have {len(fish_list)})")
                        return self._create_error_response(
                            f"Need at least 3 fish to play poker (currently {len(fish_list)})"
                        )

                    # Get leaderboard
                    leaderboard = self.world.ecosystem.get_poker_leaderboard(
                        fish_list=fish_list, limit=3, sort_by="net_energy"
                    )

                    # Create AI fish data from top 3
                    ai_fish = []
                    for entry in leaderboard[:3]:
                        # Find the actual fish object
                        fish = next((f for f in fish_list if f.fish_id == entry["fish_id"]), None)
                        if fish:
                            ai_fish.append(self._create_fish_player_data(fish, include_aggression=True))

                    # If we don't have 3 fish from leaderboard, fill with random fish
                    if len(ai_fish) < 3:
                        for fish in fish_list:
                            if len(ai_fish) >= 3:
                                break
                            if fish.fish_id not in [f["fish_id"] for f in ai_fish]:
                                ai_fish.append(self._create_fish_player_data(fish, include_aggression=True))

                    # Create poker game
                    game_id = str(uuid.uuid4())
                    human_energy = data.get("energy", 500.0) if data else 500.0

                    self.human_poker_game = HumanPokerGame(
                        game_id=game_id,
                        human_energy=human_energy,
                        ai_fish=ai_fish,
                        small_blind=5.0,
                        big_blind=10.0,
                    )

                    logger.info(f"Created human poker game {game_id} with {len(ai_fish)} AI opponents")

                    # Return the initial game state to the frontend
                    return {
                        "success": True,
                        "state": self.human_poker_game.get_state(),
                    }

                except Exception as e:
                    logger.error(f"Error starting poker game: {e}", exc_info=True)
                    return self._create_error_response(f"Failed to start poker game: {str(e)}")

            elif command == "poker_action":
                # Handle poker action (fold, check, call, raise)
                if not self.human_poker_game:
                    logger.warning("Poker action received but no game active")
                    return self._create_error_response("No poker game active")

                if not data:
                    return self._create_error_response("No action data provided")

                action = data.get("action")
                amount = data.get("amount", 0.0)

                logger.info(f"Processing poker action: {action}, amount: {amount}")

                result = self.human_poker_game.handle_action("human", action, amount)
                return result

            elif command == "standard_poker_series":
                # Run standard benchmark poker series with top 3 fish vs static player
                logger.info("Starting standard poker benchmark series...")
                try:
                    # Get top fish from leaderboard
                    fish_list = [e for e in self.world.entities_list if isinstance(e, Fish)]

                    if len(fish_list) < 1:
                        logger.warning("No fish available for benchmark series")
                        return self._create_error_response("Need at least 1 fish to run benchmark series")

                    # Get top 3 fish from leaderboard
                    num_fish = min(3, len(fish_list))
                    leaderboard = self.world.ecosystem.get_poker_leaderboard(
                        fish_list=fish_list, limit=num_fish, sort_by="net_energy"
                    )

                    # Build list of fish player data
                    fish_players = []
                    for i in range(num_fish):
                        if i < len(leaderboard):
                            # Use leaderboard entry
                            entry = leaderboard[i]
                            fish = next(
                                (f for f in fish_list if f.fish_id == entry["fish_id"]),
                                fish_list[i]
                            )
                            fish_name = f"{entry['algorithm'][:15]} (Gen {entry['generation']}) #{entry['fish_id']}"
                        else:
                            # Fallback to fish from list
                            fish = fish_list[i]
                            algo_name = fish.genome.behavior_algorithm.algorithm_id
                            fish_name = f"{algo_name[:15]} (Gen {fish.generation}) #{fish.fish_id}"

                        fish_players.append({
                            "name": fish_name,
                            "fish_id": fish.fish_id,
                            "generation": fish.generation,
                            "poker_strategy": fish.genome.poker_strategy_algorithm,
                        })

                    # Create benchmark series with multiple fish
                    game_id = str(uuid.uuid4())
                    standard_energy = data.get("standard_energy", 500.0) if data else 500.0
                    max_hands = data.get("max_hands", 1000) if data else 1000

                    self.standard_poker_series = AutoEvaluatePokerGame(
                        game_id=game_id,
                        fish_players=fish_players,
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
                    return self._create_error_response(f"Failed to run benchmark series: {str(e)}")
