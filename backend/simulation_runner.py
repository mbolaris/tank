"""Background simulation runner thread."""

import asyncio
import logging
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Union

import orjson

from backend.state_payloads import (
    AutoEvaluateStatsPayload,
    DeltaStatePayload,
    EntitySnapshot,
    FullStatePayload,
    PokerEventPayload,
    PokerLeaderboardEntryPayload,
    PokerStatsPayload,
    StatsPayload,
)
from core import entities, movement_strategy
from core.auto_evaluate_poker import AutoEvaluatePokerGame
from core.constants import FILES, FRAME_RATE, SCREEN_HEIGHT, SCREEN_WIDTH, SPAWN_MARGIN_PIXELS
from core.entities import Fish
from core.entities.fractal_plant import FractalPlant
from core.genetics import Genome
from core.human_poker_game import HumanPokerGame
from core.plant_poker_strategy import PlantPokerStrategyAdapter

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
        self.fast_forward = False
        
        # FPS Tracking
        self.last_fps_time = time.time()
        self.fps_frame_count = 0
        self.current_actual_fps = 0.0

        # Performance: Throttle WebSocket updates to reduce serialization overhead
        # Cache state and only rebuild every N frames (reduces from 30 FPS to 15 FPS)
        self.websocket_update_interval = 2  # Send every 2 frames
        self.frames_since_websocket_update = 0
        self._cached_state: Optional[Union[FullStatePayload, DeltaStatePayload]] = None
        self._cached_state_frame: Optional[int] = None
        self.delta_sync_interval = 30
        self._last_full_frame: Optional[int] = None
        self._last_entities: Dict[int, EntitySnapshot] = {}

        # Human poker game management
        self.human_poker_game: Optional[HumanPokerGame] = None

        # Static benchmark poker series management
        self.standard_poker_series: Optional[AutoEvaluatePokerGame] = None

        # Ongoing auto-evaluation against static baseline
        self.auto_eval_history: List[Dict[str, Any]] = []
        self.auto_eval_stats: Optional[Dict[str, Any]] = None
        self.auto_eval_running: bool = False
        self.auto_eval_interval_seconds = 60.0
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
        self._last_full_frame = None
        self._last_entities.clear()

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
        genome_data = self._get_fish_genome_data(fish)
        player_data = {
            "fish_id": fish.fish_id,
            "name": f"{algo_name[:15]} (Gen {fish.generation})",
            "generation": fish.generation,
            "energy": fish.energy,
            "algorithm": algo_name,
            "genome_data": genome_data,
        }

        if include_aggression:
            player_data["aggression"] = getattr(fish.genome, "aggression", 0.5)

        return player_data

    def _create_plant_player_data(self, plant: FractalPlant) -> Dict[str, Any]:
        """Create benchmark player metadata for a plant."""

        return {
            "plant_id": plant.plant_id,
            "name": f"Plant #{plant.plant_id}",
            "generation": getattr(plant, "age", 0),
            "energy": plant.energy,
            "species": "plant",
            "poker_strategy": PlantPokerStrategyAdapter.from_genome(plant.genome),
        }

    def _get_fish_genome_data(self, fish: Fish) -> Optional[Dict[str, Any]]:
        """Extract visual genome data for a fish to mirror tank rendering."""

        if not hasattr(fish, "genome"):
            return None

        return {
            "speed": fish.genome.speed_modifier,
            "size": getattr(fish, "size", getattr(fish.genome, "size_modifier", 1.0)),
            "color_hue": fish.genome.color_hue,
            "template_id": fish.genome.template_id,
            "fin_size": fish.genome.fin_size,
            "tail_size": fish.genome.tail_size,
            "body_aspect": fish.genome.body_aspect,
            "eye_size": fish.genome.eye_size,
            "pattern_intensity": fish.genome.pattern_intensity,
            "pattern_type": fish.genome.pattern_type,
        }

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
                            try:
                                self.world.update()
                            except Exception as e:
                                logger.error(
                                    f"Simulation loop: Error updating world at frame {frame_count}: {e}",
                                    exc_info=True,
                                )
                                # Continue running even if update fails

                    self._start_auto_evaluation_if_needed()

                    # FPS Calculation
                    self.fps_frame_count += 1
                    current_time = time.time()
                    if current_time - self.last_fps_time >= 5.0:
                        self.current_actual_fps = self.fps_frame_count / (current_time - self.last_fps_time)
                        self.fps_frame_count = 0
                        self.last_fps_time = current_time
                        # Log stats periodically
                        stats = self.world.get_stats()
                        logger.info(
                            f"Simulation Status: FPS={self.current_actual_fps:.1f}, "
                            f"Fish={stats.get('fish_count', 0)}, "
                            f"Plants={stats.get('plant_count', 0)}, "
                            f"Energy={stats.get('total_energy', 0.0):.1f}"
                        )

                    # Maintain frame rate
                    if not self.fast_forward:
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
            plant_list = [e for e in self.world.entities_list if isinstance(e, FractalPlant)]

        if not leaderboard:
            leaderboard = []

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
            # Still allow benchmarking if we have strong plants even when fish leaderboard is empty
            pass

        plant_players: List[Dict[str, Any]] = []
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
                plant_players.append(self._create_plant_player_data(plant))

        benchmark_players = fish_players + plant_players
        if not benchmark_players:
            return

        self.auto_eval_running = True
        threading.Thread(
            target=self._run_auto_evaluation,
            args=(benchmark_players,),
            name="auto_eval_thread",
            daemon=True,
        ).start()

    def _run_auto_evaluation(self, benchmark_players: List[Dict[str, Any]]):
        """Execute a background auto-evaluation series."""

        try:
            game_id = str(uuid.uuid4())
            standard_energy = 500.0
            max_hands = 1000

            auto_eval = AutoEvaluatePokerGame(
                game_id=game_id,
                player_pool=benchmark_players,
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

    def get_state(self, force_full: bool = False, allow_delta: bool = True):
        """Get current simulation state for WebSocket broadcast.

        This method now supports delta compression to avoid sending the entire
        world on every frame. A full state is sent every ``delta_sync_interval``
        frames (or when ``force_full`` is True); intermediate frames only carry
        position/velocity updates plus any added/removed entities.
        """

        current_frame = self.world.frame_count
        elapsed_time = (
            self.world.engine.elapsed_time
            if hasattr(self.world.engine, "elapsed_time")
            else self.world.frame_count * 33
        )

        # Fast path: identical frame reuse
        if self._cached_state is not None and current_frame == self._cached_state_frame:
            return self._cached_state

        self.frames_since_websocket_update += 1
        should_rebuild = self.frames_since_websocket_update >= self.websocket_update_interval

        if not should_rebuild and self._cached_state is not None:
            return self._cached_state

        self.frames_since_websocket_update = 0

        with self.lock:
            send_full = (
                force_full
                or not allow_delta
                or self._last_full_frame is None
                or (current_frame - self._last_full_frame) >= self.delta_sync_interval
            )

            if send_full:
                state = self._build_full_state(current_frame, elapsed_time)
                self._last_full_frame = current_frame
                self._last_entities = {entity.id: entity for entity in state.entities}
            else:
                entities = self._collect_entities()
                current_entities = {entity.id: entity for entity in entities}

                added = [entity.to_full_dict() for eid, entity in current_entities.items() if eid not in self._last_entities]
                removed = [eid for eid in self._last_entities if eid not in current_entities]
                updates = [entity.to_delta_dict() for entity in entities]

                poker_events = self._collect_poker_events()
                state = DeltaStatePayload(
                    frame=current_frame,
                    elapsed_time=elapsed_time,
                    updates=updates,
                    added=added,
                    removed=removed,
                    poker_events=poker_events,
                    stats=None,
                )

                self._last_entities = current_entities

            self._cached_state = state
            self._cached_state_frame = current_frame
            return state

    async def get_state_async(self, force_full: bool = False, allow_delta: bool = True):
        """Async wrapper to fetch simulation state without blocking the event loop."""

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self.get_state, force_full, allow_delta
        )

    def serialize_state(self, state: Union[FullStatePayload, DeltaStatePayload]) -> bytes:
        """Serialize a state payload with fast JSON and log slow frames."""

        start = time.perf_counter()
        payload = state.to_dict() if hasattr(state, "to_dict") else state
        serialized = orjson.dumps(payload)
        duration_ms = (time.perf_counter() - start) * 1000

        if duration_ms > 10:
            logger.warning(
                "serialize_state: Slow serialization %.2f ms for frame %s",
                duration_ms,
                getattr(state, "frame", "unknown"),
            )

        return serialized

    def _build_full_state(self, frame: int, elapsed_time: int) -> FullStatePayload:
        entities = self._collect_entities()
        stats = self._collect_stats(frame)
        poker_events = self._collect_poker_events()
        poker_leaderboard = self._collect_poker_leaderboard()
        auto_eval = self._collect_auto_eval()

        return FullStatePayload(
            frame=frame,
            elapsed_time=elapsed_time,
            entities=entities,
            stats=stats,
            poker_events=poker_events,
            poker_leaderboard=poker_leaderboard,
            auto_evaluation=auto_eval,
        )

    def _collect_entities(self) -> List[EntitySnapshot]:
        entities_data: List[EntitySnapshot] = []
        for entity in self.world.entities_list:
            entity_data = self._entity_to_data(entity)
            if entity_data:
                entities_data.append(entity_data)

        z_order = {
            "castle": 0,
            "plant": 1,
            "fractal_plant": 1,  # Same layer as regular plants
            "plant_nectar": 2,   # Same layer as food
            "food": 2,
            "fish": 4,
            "jellyfish": 5,
            "crab": 10,  # Render crab in front of everything
        }
        entities_data.sort(key=lambda e: z_order.get(e.type, 999))
        return entities_data

    def _collect_stats(self, frame: int) -> StatsPayload:
        stats = self.world.get_stats()
        poker_stats_dict = stats.get("poker_stats", {})
        poker_stats_payload = PokerStatsPayload(
            total_games=poker_stats_dict.get("total_games", 0),
            total_fish_games=poker_stats_dict.get("total_fish_games", 0),
            total_plant_games=poker_stats_dict.get("total_plant_games", 0),
            total_plant_energy_transferred=poker_stats_dict.get("total_plant_energy_transferred", 0.0),
            total_wins=poker_stats_dict.get("total_wins", 0),
            total_losses=poker_stats_dict.get("total_losses", 0),
            total_ties=poker_stats_dict.get("total_ties", 0),
            total_energy_won=poker_stats_dict.get("total_energy_won", 0.0),
            total_energy_lost=poker_stats_dict.get("total_energy_lost", 0.0),
            net_energy=poker_stats_dict.get("net_energy", 0.0),
            best_hand_rank=poker_stats_dict.get("best_hand_rank", 0),
            best_hand_name=poker_stats_dict.get("best_hand_name", "None"),
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

        return StatsPayload(
            frame=frame,
            population=stats.get("total_population", 0),
            generation=stats.get("current_generation", 0),
            max_generation=stats.get("max_generation", stats.get("current_generation", 0)),
            births=stats.get("total_births", 0),
            deaths=stats.get("total_deaths", 0),
            capacity=stats.get("capacity_usage", "0%"),
            time=stats.get("time_string", "Day"),
            death_causes=stats.get("death_causes", {}),
            fish_count=stats.get("fish_count", 0),
            food_count=stats.get("food_count", 0),
            plant_count=stats.get("plant_count", 0),
            total_energy=stats.get("total_energy", 0.0),
            fish_energy=stats.get("fish_energy", 0.0),
            plant_energy=stats.get("plant_energy", 0.0),
            poker_stats=poker_stats_payload,
            fps=round(self.current_actual_fps, 1),
        )

    def _collect_poker_events(self) -> List[PokerEventPayload]:
        poker_events: List[PokerEventPayload] = []
        recent_events = self.world.engine.poker_events
        for event in recent_events:
            if "Standard Algorithm" in event["message"] or "Auto-eval" in event["message"]:
                continue

            poker_events.append(
                PokerEventPayload(
                    frame=event["frame"],
                    winner_id=event["winner_id"],
                    loser_id=event["loser_id"],
                    winner_hand=event["winner_hand"],
                    loser_hand=event["loser_hand"],
                    energy_transferred=event["energy_transferred"],
                    message=event["message"],
                    is_jellyfish=event.get("is_jellyfish", False),
                    is_plant=event.get("is_plant", False),
                    plant_id=event.get("plant_id", None),
                )
            )

        return poker_events

    def _collect_poker_leaderboard(self) -> List[PokerLeaderboardEntryPayload]:
        if not hasattr(self.world.ecosystem, "get_poker_leaderboard"):
            return []

        fish_list = [e for e in self.world.entities_list if isinstance(e, Fish)]
        leaderboard_data = self.world.ecosystem.get_poker_leaderboard(
            fish_list=fish_list, limit=10, sort_by="net_energy"
        )
        return [PokerLeaderboardEntryPayload(**entry) for entry in leaderboard_data]

    def _collect_auto_eval(self) -> Optional[AutoEvaluateStatsPayload]:
        with self.auto_eval_lock:
            if not self.auto_eval_stats:
                return None

            try:
                stats_copy = self.auto_eval_stats.copy()
                if "performance_history" in stats_copy:
                    history = stats_copy["performance_history"]
                    if len(history) > 50:
                        stats_copy["performance_history"] = history[-50:]
                allowed_keys = {
                    "hands_played",
                    "hands_remaining",
                    "players",
                    "game_over",
                    "winner",
                    "reason",
                    "performance_history",
                }
                filtered = {k: v for k, v in stats_copy.items() if k in allowed_keys}
                return AutoEvaluateStatsPayload(**filtered)
            except Exception:
                logger.error("Failed to serialize auto evaluation stats", exc_info=True)
                return None

    def _entity_to_data(self, entity: entities.Agent) -> Optional[EntitySnapshot]:
        """Convert an entity to a lightweight snapshot for serialization."""
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

                return EntitySnapshot(
                    type="fish",
                    energy=entity.energy,
                    generation=entity.generation if hasattr(entity, "generation") else 0,
                    age=entity.age if hasattr(entity, "age") else 0,
                    species=species_label,
                    genome_data=genome_data,
                    poker_effect_state=entity.poker_effect_state if hasattr(entity, "poker_effect_state") else None,
                    **base_data,
                )

            elif isinstance(entity, entities.PlantNectar):
                # PlantNectar check must come BEFORE Food check since PlantNectar extends Food
                # Include source plant position for sway synchronization in frontend
                # Use id(source_plant) to match the plant's entity id in the frontend
                source_plant_id = None
                source_plant_x = None
                source_plant_y = None
                floral_type = None
                floral_petals = None
                floral_layers = None
                floral_spin = None
                floral_hue = None
                floral_saturation = None
                if entity.source_plant:
                    source_plant_id = id(entity.source_plant)  # Must match plant's entity id
                    source_plant_x = entity.source_plant.pos.x + entity.source_plant.width / 2
                    source_plant_y = entity.source_plant.pos.y + entity.source_plant.height
                    # Get floral genome from parent plant
                    genome = entity.source_plant.genome
                    floral_type = genome.floral_type
                    floral_petals = genome.floral_petals
                    floral_layers = genome.floral_layers
                    floral_spin = genome.floral_spin
                    floral_hue = genome.floral_hue
                    floral_saturation = genome.floral_saturation
                return EntitySnapshot(
                    type="plant_nectar",
                    energy=entity.energy if hasattr(entity, "energy") else 50,
                    source_plant_id=source_plant_id,
                    source_plant_x=source_plant_x,
                    source_plant_y=source_plant_y,
                    floral_type=floral_type,
                    floral_petals=floral_petals,
                    floral_layers=floral_layers,
                    floral_spin=floral_spin,
                    floral_hue=floral_hue,
                    floral_saturation=floral_saturation,
                    **base_data,
                )

            elif isinstance(entity, entities.Food):
                return EntitySnapshot(
                    type="food",
                    food_type=entity.food_type if hasattr(entity, "food_type") else 0,
                    **base_data,
                )

            elif isinstance(entity, entities.Plant):
                return EntitySnapshot(
                    type="plant",
                    plant_type=entity.plant_type if hasattr(entity, "plant_type") else 1,
                    **base_data,
                )

            elif isinstance(entity, entities.Crab):
                return EntitySnapshot(
                    type="crab",
                    energy=entity.energy if hasattr(entity, "energy") else 100,
                    **base_data,
                )

            elif isinstance(entity, entities.Castle):
                return EntitySnapshot(type="castle", **base_data)

            elif isinstance(entity, entities.Jellyfish):
                return EntitySnapshot(
                    type="jellyfish",
                    energy=entity.energy if hasattr(entity, "energy") else 1000,
                    plant_type=getattr(entity, "jellyfish_id", 0),
                    **base_data,
                )

            elif isinstance(entity, entities.FractalPlant):
                # Serialize fractal plant with its genome for L-system rendering
                genome_dict = entity.genome.to_dict() if hasattr(entity, "genome") else None
                return EntitySnapshot(
                    type="fractal_plant",
                    energy=entity.energy if hasattr(entity, "energy") else 0,
                    max_energy=entity.max_energy if hasattr(entity, "max_energy") else 100,
                    genome=genome_dict,
                    size_multiplier=entity.get_size_multiplier() if hasattr(entity, "get_size_multiplier") else 1.0,
                    iterations=entity.get_fractal_iterations() if hasattr(entity, "get_fractal_iterations") else 3,
                    nectar_ready=entity.nectar_cooldown == 0 and (
                        entity.energy / entity.max_energy >= entity.genome.nectar_threshold_ratio
                    ) if hasattr(entity, "nectar_cooldown") else False,
                    age=entity.age if hasattr(entity, "age") else 0,
                    **base_data,
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
                    self._invalidate_state_cache()

                except Exception as e:
                    logger.error(f"Error spawning fish: {e}")

            elif command == "pause":
                self.world.paused = True
                logger.info("Simulation paused")

            elif command == "resume":
                self.world.paused = False
                logger.info("Simulation resumed")

            elif command == "reset":
                self.world.setup()
                self._invalidate_state_cache()
                logger.info("Simulation reset")

            elif command == "fast_forward":
                enabled = data.get("enabled", False) if data else False
                self.fast_forward = enabled
                logger.info(f"Fast forward {'enabled' if enabled else 'disabled'}")

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

            elif command == "poker_new_round":
                # Start a new hand in the current poker session
                if not self.human_poker_game:
                    logger.warning("New round requested but no game active")
                    return self._create_error_response("No poker game active")

                logger.info("Starting new poker hand...")
                result = self.human_poker_game.start_new_hand()
                return result

            elif command == "poker_autopilot_action":
                # Get AI-recommended action for human player (autopilot mode)
                if not self.human_poker_game:
                    logger.warning("Autopilot action requested but no game active")
                    return self._create_error_response("No poker game active")

                game = self.human_poker_game

                # If game is over, return new_round action
                if game.game_over:
                    if game.session_over:
                        return {"success": True, "action": "exit", "amount": 0}
                    return {"success": True, "action": "new_round", "amount": 0}

                # If not human's turn, wait
                human_player = game.players[0]  # Human is always index 0
                if game.current_player_index != 0:
                    return {"success": True, "action": "wait", "amount": 0}

                # Use the same AI logic as fish opponents
                from core.poker.core import PokerEngine

                hand = PokerEngine.evaluate_hand(human_player.hole_cards, game.community_cards)
                call_amount = game._get_call_amount(0)
                active_bets = [p.current_bet for p in game.players if not p.folded]
                opponent_bet = max(active_bets) if active_bets else 0.0

                action, bet_amount = PokerEngine.decide_action(
                    hand=hand,
                    current_bet=human_player.current_bet,
                    opponent_bet=opponent_bet,
                    pot=game.pot,
                    player_energy=human_player.energy,
                    aggression=0.5,  # Medium aggression for autopilot
                    hole_cards=human_player.hole_cards,
                    community_cards=game.community_cards,
                    position_on_button=(game.current_player_index == game.button_index),
                )

                # Convert BettingAction enum to string
                action_str = action.name.lower()

                # Handle check vs call
                if action_str == "check" and call_amount > 0:
                    action_str = "call"
                    bet_amount = call_amount
                elif action_str == "call":
                    bet_amount = call_amount
                elif action_str == "raise":
                    # bet_amount is the raise amount on top of call
                    pass

                logger.info(f"Autopilot recommends: {action_str}, amount: {bet_amount}")
                return {"success": True, "action": action_str, "amount": bet_amount}

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
                    return self._create_error_response(f"Failed to run benchmark series: {str(e)}")

    async def handle_command_async(
        self, command: str, data: Optional[Dict[str, Any]] = None
    ):
        """Async wrapper to route commands off the event loop thread."""

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.handle_command, command, data)
