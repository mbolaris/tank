"""Entity factory for creating initial population.

This module provides a single source of truth for initial population creation,
used by the web UI backend and headless simulation mode.
"""

import random
from typing import List
from core import entities, environment
from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, FILES, INIT_POS
from core.ecosystem import EcosystemManager
from core.genetics import Genome
from core import movement_strategy


def create_initial_population(
    env: environment.Environment,
    ecosystem: EcosystemManager,
    screen_width: int = SCREEN_WIDTH,
    screen_height: int = SCREEN_HEIGHT,
) -> List[entities.Agent]:
    """Create initial population for simulation.

    Creates a starting population with algorithmic fish that evolve their behavior:
    - 10 algorithmic fish with parametrizable behavior algorithms
    - 3 plants
    - 1 crab
    - 1 castle

    Args:
        env: Environment instance for spatial queries
        ecosystem: EcosystemManager for population tracking
        screen_width: Screen width for boundary constraints
        screen_height: Screen height for boundary constraints

    Returns:
        List of Entity objects representing the initial population
    """
    population = []

    # Create algorithmic fish with parametrizable behavior algorithms
    # These fish use the algorithmic evolution system with diverse genomes
    for i in range(10):  # Start with 10 algorithmic fish for better evolution and sustainability
        x = INIT_POS["school"][0] + random.randint(-100, 100)
        y = INIT_POS["school"][1] + random.randint(-60, 60)
        # Create genome with behavior algorithm
        genome = Genome.random(use_algorithm=True)
        fish = entities.Fish(
            env,
            movement_strategy.AlgorithmicMovement(),
            FILES["schooling_fish"][0],
            x,
            y,
            4,
            genome=genome,
            generation=0,
            ecosystem=ecosystem,
            screen_width=screen_width,
            screen_height=screen_height,
        )
        population.append(fish)

    # Create plants at predefined positions
    plant1 = entities.Plant(env, 1, *INIT_POS["plant1"], screen_width, screen_height)
    plant2 = entities.Plant(env, 2, *INIT_POS["plant2"], screen_width, screen_height)
    plant3 = entities.Plant(env, 1, *INIT_POS["plant3"], screen_width, screen_height)

    # Create initial food items to prevent startup pause
    # Spawn 8 food items at various locations so fish have immediate targets
    initial_food = []
    food_positions = [
        (screen_width * 0.25, screen_height * 0.3),  # Upper left area
        (screen_width * 0.5, screen_height * 0.25),  # Upper middle
        (screen_width * 0.75, screen_height * 0.35),  # Upper right area
        (screen_width * 0.2, screen_height * 0.5),  # Middle left
        (screen_width * 0.6, screen_height * 0.45),  # Middle right
        (screen_width * 0.3, screen_height * 0.65),  # Lower left
        (screen_width * 0.7, screen_height * 0.6),  # Lower right
        (screen_width * 0.5, screen_height * 0.55),  # Lower middle
    ]
    for x, y in food_positions:
        food = entities.Food(
            env,
            x,
            y,
            source_plant=None,
            food_type=None,  # Random type
            allow_stationary_types=False,  # No stationary food at startup
            screen_width=screen_width,
            screen_height=screen_height,
        )
        initial_food.append(food)

    # Create crab and castle
    crab = entities.Crab(env, None, *INIT_POS["crab"], screen_width, screen_height)
    castle = entities.Castle(env, *INIT_POS["castle"], screen_width, screen_height)

    # Add all non-fish entities
    population.extend([plant1, plant2, plant3] + initial_food + [crab, castle])

    return population
