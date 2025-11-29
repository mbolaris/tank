"""Entity factory for creating initial population.

This module provides a single source of truth for initial population creation,
used by the web UI backend and headless simulation mode.
"""

import random
from typing import List, Optional

from core import entities, environment, movement_strategy
from core.constants import FILES, INIT_POS, NUM_SCHOOLING_FISH, SCREEN_HEIGHT, SCREEN_WIDTH
from core.ecosystem import EcosystemManager
from core.genetics import Genome


def create_initial_population(
    env: environment.Environment,
    ecosystem: EcosystemManager,
    screen_width: int = SCREEN_WIDTH,
    screen_height: int = SCREEN_HEIGHT,
    rng: Optional[random.Random] = None,
) -> List[entities.Agent]:
    """Create initial population for simulation.

    Creates a starting population with algorithmic fish that evolve their behavior:
    - 10 algorithmic fish with parametrizable behavior algorithms
    - 1 crab
    - 1 castle

    Note: PNG plants have been disabled. Only fractal plants are used.

    Args:
        env: Environment instance for spatial queries
        ecosystem: EcosystemManager for population tracking
        screen_width: Screen width for boundary constraints
        screen_height: Screen height for boundary constraints

    Returns:
        List of Entity objects representing the initial population
    """
    population = []
    rng = rng or random

    # Create algorithmic fish with parametrizable behavior algorithms
    # These fish use the algorithmic evolution system with diverse genomes
    for _i in range(
        NUM_SCHOOLING_FISH
    ):  # Start with NUM_SCHOOLING_FISH algorithmic fish for better evolution and sustainability
        x = INIT_POS["school"][0] + rng.randint(-100, 100)
        y = INIT_POS["school"][1] + rng.randint(-60, 60)
        # Create genome with behavior algorithm
        genome = Genome.random(use_algorithm=True, rng=rng)
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

    # PNG plants disabled - only fractal plants are used now

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
    population.extend(initial_food + [crab, castle])

    return population
