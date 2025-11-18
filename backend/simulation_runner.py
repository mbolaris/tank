"""Background simulation runner thread."""

import logging
import random
import threading
import time
from typing import List, Optional, Dict, Any

# Use absolute imports assuming tank/ is in PYTHONPATH
from simulation_engine import SimulationEngine
from core import entities
from core.algorithms import get_algorithm_index
from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT
from backend.models import EntityData, StatsData, SimulationUpdate, PokerStatsData, PokerEventData

logger = logging.getLogger(__name__)


class SimulationRunner:
    """Runs the simulation in a background thread and provides state updates."""

    def __init__(self):
        """Initialize the simulation runner."""
        self.engine = SimulationEngine(headless=True)
        self.engine.setup()

        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

        # Target frame rate
        self.fps = 30
        self.frame_time = 1.0 / self.fps

    def start(self):
        """Start the simulation in a background thread."""
        if not self.running:
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
        while self.running:
            loop_start = time.time()

            with self.lock:
                if not self.engine.paused:
                    self.engine.update()

            # Maintain frame rate
            elapsed = time.time() - loop_start
            sleep_time = max(0, self.frame_time - elapsed)
            time.sleep(sleep_time)

    def get_state(self) -> SimulationUpdate:
        """Get current simulation state for WebSocket broadcast.

        Returns:
            SimulationUpdate with current entities and stats
        """
        with self.lock:
            entities_data = []

            # Convert entities to serializable format
            for entity in self.engine.entities_list:
                entity_data = self._entity_to_data(entity)
                if entity_data:
                    entities_data.append(entity_data)

            # Get ecosystem stats
            stats = self.engine.get_stats()

            # Create poker stats data
            poker_stats_dict = stats.get('poker_stats', {})
            poker_stats_data = PokerStatsData(
                total_games=poker_stats_dict.get('total_games', 0),
                total_wins=poker_stats_dict.get('total_wins', 0),
                total_losses=poker_stats_dict.get('total_losses', 0),
                total_ties=poker_stats_dict.get('total_ties', 0),
                total_energy_won=poker_stats_dict.get('total_energy_won', 0.0),
                total_energy_lost=poker_stats_dict.get('total_energy_lost', 0.0),
                net_energy=poker_stats_dict.get('net_energy', 0.0),
                best_hand_rank=poker_stats_dict.get('best_hand_rank', 0),
                best_hand_name=poker_stats_dict.get('best_hand_name', 'None'),
                # Advanced metrics
                win_rate=poker_stats_dict.get('win_rate', 0.0),
                win_rate_pct=poker_stats_dict.get('win_rate_pct', '0.0%'),
                roi=poker_stats_dict.get('roi', 0.0),
                vpip=poker_stats_dict.get('vpip', 0.0),
                vpip_pct=poker_stats_dict.get('vpip_pct', '0.0%'),
                bluff_success_rate=poker_stats_dict.get('bluff_success_rate', 0.0),
                bluff_success_pct=poker_stats_dict.get('bluff_success_pct', '0.0%'),
                button_win_rate=poker_stats_dict.get('button_win_rate', 0.0),
                button_win_rate_pct=poker_stats_dict.get('button_win_rate_pct', '0.0%'),
                off_button_win_rate=poker_stats_dict.get('off_button_win_rate', 0.0),
                off_button_win_rate_pct=poker_stats_dict.get('off_button_win_rate_pct', '0.0%'),
                positional_advantage=poker_stats_dict.get('positional_advantage', 0.0),
                positional_advantage_pct=poker_stats_dict.get('positional_advantage_pct', '0.0%'),
                aggression_factor=poker_stats_dict.get('aggression_factor', 0.0),
                avg_hand_rank=poker_stats_dict.get('avg_hand_rank', 0.0),
                total_folds=poker_stats_dict.get('total_folds', 0),
                preflop_folds=poker_stats_dict.get('preflop_folds', 0),
                postflop_folds=poker_stats_dict.get('postflop_folds', 0),
                showdown_win_rate=poker_stats_dict.get('showdown_win_rate', '0.0%'),
                avg_fold_rate=poker_stats_dict.get('avg_fold_rate', '0.0%'),
            )

            stats_data = StatsData(
                frame=self.engine.frame_count,
                population=stats.get('total_population', 0),
                generation=stats.get('current_generation', 0),
                births=stats.get('total_births', 0),
                deaths=stats.get('total_deaths', 0),
                capacity=stats.get('capacity_usage', '0%'),
                time=stats.get('time_string', 'Day'),
                death_causes=stats.get('death_causes', {}),
                fish_count=stats.get('fish_count', 0),
                food_count=stats.get('food_count', 0),
                plant_count=stats.get('plant_count', 0),
                total_energy=stats.get('total_energy', 0.0),
                poker_stats=poker_stats_data
            )

            # Get recent poker events
            poker_events = []
            recent_events = self.engine.get_recent_poker_events(max_age_frames=180)
            for event in recent_events:
                poker_events.append(PokerEventData(
                    frame=event['frame'],
                    winner_id=event['winner_id'],
                    loser_id=event['loser_id'],
                    winner_hand=event['winner_hand'],
                    loser_hand=event['loser_hand'],
                    energy_transferred=event['energy_transferred'],
                    message=event['message']
                ))

            return SimulationUpdate(
                frame=self.engine.frame_count,
                elapsed_time=self.engine.elapsed_time if hasattr(self.engine, 'elapsed_time') else self.engine.frame_count * 33,
                entities=entities_data,
                stats=stats_data,
                poker_events=poker_events
            )

    def _entity_to_data(self, entity: entities.Agent) -> Optional[EntityData]:
        """Convert an entity to EntityData.

        Args:
            entity: The entity to convert

        Returns:
            EntityData or None if conversion failed
        """
        try:
            base_data = {
                'id': id(entity),  # Use object id as unique identifier
                'x': entity.pos.x,
                'y': entity.pos.y,
                'width': entity.width,
                'height': entity.height,
                'vel_x': entity.vel.x if hasattr(entity, 'vel') else 0,
                'vel_y': entity.vel.y if hasattr(entity, 'vel') else 0
            }

            if isinstance(entity, entities.Fish):
                genome_data = None
                if hasattr(entity, 'genome'):
                    genome_data = {
                        'speed': entity.genome.speed_modifier,
                        'size': entity.genome.size_modifier,
                        'color_hue': entity.genome.color_hue,
                        # Visual traits for parametric fish templates
                        'template_id': entity.genome.template_id,
                        'fin_size': entity.genome.fin_size,
                        'tail_size': entity.genome.tail_size,
                        'body_aspect': entity.genome.body_aspect,
                        'eye_size': entity.genome.eye_size,
                        'pattern_intensity': entity.genome.pattern_intensity,
                        'pattern_type': entity.genome.pattern_type,
                    }

                return EntityData(
                    type='fish',
                    energy=entity.energy,
                    generation=entity.generation if hasattr(entity, 'generation') else 0,
                    age=entity.age if hasattr(entity, 'age') else 0,
                    genome_data=genome_data,
                    **base_data
                )

            elif isinstance(entity, entities.Food):
                return EntityData(
                    type='food',
                    food_type=entity.food_type if hasattr(entity, 'food_type') else 0,
                    **base_data
                )

            elif isinstance(entity, entities.Plant):
                return EntityData(
                    type='plant',
                    plant_type=entity.plant_type if hasattr(entity, 'plant_type') else 1,
                    **base_data
                )

            elif isinstance(entity, entities.Crab):
                return EntityData(
                    type='crab',
                    energy=entity.energy if hasattr(entity, 'energy') else 100,
                    **base_data
                )

            elif isinstance(entity, entities.Castle):
                return EntityData(
                    type='castle',
                    **base_data
                )

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
            command: Command type ('add_food', 'pause', 'resume', 'reset')
            data: Optional command data
        """
        with self.lock:
            if command == 'add_food':
                # Add food at random position
                x = random.randint(0, SCREEN_WIDTH)
                food = entities.Food(
                    self.engine.environment,
                    x,
                    0,
                    source_plant=None,
                    allow_stationary_types=False,
                    screen_width=SCREEN_WIDTH,
                    screen_height=SCREEN_HEIGHT
                )
                food.pos.y = 0
                self.engine.entities_list.append(food)

            elif command == 'pause':
                self.engine.paused = True

            elif command == 'resume':
                self.engine.paused = False

            elif command == 'spawn_jellyfish':
                # Spawn jellyfish at center of tank
                x = SCREEN_WIDTH // 2
                y = SCREEN_HEIGHT // 2
                jellyfish = entities.Jellyfish(
                    self.engine.environment,
                    x=x,
                    y=y,
                    jellyfish_id=0,  # Could track count if needed
                    screen_width=SCREEN_WIDTH,
                    screen_height=SCREEN_HEIGHT
                )
                self.engine.entities_list.append(jellyfish)
                logger.info(f"Spawned jellyfish at ({x}, {y})")

            elif command == 'reset':
                # Reset simulation
                self.engine.entities_list.clear()
                self.engine.frame_count = 0
                self.engine.setup()
                self.engine.paused = False
                self.engine.start_time = time.time()
