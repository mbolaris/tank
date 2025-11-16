"""Background simulation runner thread."""

import sys
import os
import random
import threading
import time
from typing import List, Optional, Dict, Any

# Add parent directory to path to import simulation engine
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from simulation_engine import SimulationEngine
from core import entities
from core.behavior_algorithms import get_algorithm_index
from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT
from models import EntityData, StatsData, SimulationUpdate


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
                plant_count=stats.get('plant_count', 0)
            )

            return SimulationUpdate(
                frame=self.engine.frame_count,
                entities=entities_data,
                stats=stats_data
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
                'height': entity.height
            }

            if isinstance(entity, entities.Fish):
                # Get species name from movement strategy
                species = 'unknown'
                if hasattr(entity, 'movement_strategy'):
                    strategy_name = entity.movement_strategy.__class__.__name__
                    if 'Solo' in strategy_name:
                        species = 'solo'
                    elif 'Algorithmic' in strategy_name:
                        species = 'algorithmic'
                    elif 'Neural' in strategy_name:
                        species = 'neural'
                    elif 'Schooling' in strategy_name:
                        species = 'schooling'

                genome_data = None
                if hasattr(entity, 'genome'):
                    genome_data = {
                        'speed': entity.genome.speed_modifier,
                        'size': entity.genome.size_modifier,
                        'color_hue': entity.genome.color_hue
                    }

                return EntityData(
                    type='fish',
                    energy=entity.energy,
                    species=species,
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

            return None

        except Exception as e:
            print(f"Error converting entity: {e}")
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

            elif command == 'reset':
                # Reset simulation
                self.engine.entities_list.clear()
                self.engine.frame_count = 0
                self.engine.setup()
                self.engine.paused = False
                self.engine.start_time = time.time()
