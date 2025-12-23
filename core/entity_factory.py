"""Entity factory for creating initial population.

This module provides a single source of truth for initial population creation,
used by the web UI backend and headless simulation mode.
"""

import random
from typing import List, Optional

from core import entities, environment, movement_strategy
from core.config.simulation_config import DisplayConfig, EcosystemConfig
from core.config.fish import FISH_BASE_SPEED
from core.ecosystem import EcosystemManager
from core.genetics import Genome


def create_initial_population(
    env: environment.Environment,
    ecosystem: EcosystemManager,
    display_config: Optional[DisplayConfig] = None,
    ecosystem_config: Optional[EcosystemConfig] = None,
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
        display_config: Display configuration for asset selection and bounds
        ecosystem_config: Ecosystem configuration controlling initial population size

    Returns:
        List of Entity objects representing the initial population
    """
    display_config = display_config or DisplayConfig()
    ecosystem_config = ecosystem_config or EcosystemConfig()
    population = []
    rng = rng if rng is not None else random.Random()
    # These fish use the algorithmic evolution system with diverse genomes
    for _i in range(
        ecosystem_config.num_schooling_fish
    ):  # Start with configured algorithmic fish for better evolution and sustainability
        x = display_config.init_pos["school"][0] + rng.randint(-100, 100)
        y = display_config.init_pos["school"][1] + rng.randint(-60, 60)
        # Create genome with behavior algorithm
        genome = Genome.random(use_algorithm=True, rng=rng)
        fish = entities.Fish(
            env,
            movement_strategy.AlgorithmicMovement(),
            display_config.files["schooling_fish"][0],
            x,
            y,
            FISH_BASE_SPEED,
            genome=genome,
            generation=0,
            ecosystem=ecosystem,
        )
        fish.register_birth()
        population.append(fish)

    # PNG plants disabled - only fractal plants are used now

    # Create initial food items to prevent startup pause
    # Spawn 8 food items at various locations so fish have immediate targets
    initial_food = []
    food_positions = [
        (display_config.screen_width * 0.25, display_config.screen_height * 0.3),  # Upper left area
        (display_config.screen_width * 0.5, display_config.screen_height * 0.25),  # Upper middle
        (display_config.screen_width * 0.75, display_config.screen_height * 0.35),  # Upper right area
        (display_config.screen_width * 0.2, display_config.screen_height * 0.5),  # Middle left
        (display_config.screen_width * 0.6, display_config.screen_height * 0.45),  # Middle right
        (display_config.screen_width * 0.3, display_config.screen_height * 0.65),  # Lower left
        (display_config.screen_width * 0.7, display_config.screen_height * 0.6),  # Lower right
        (display_config.screen_width * 0.5, display_config.screen_height * 0.55),  # Lower middle
    ]
    for x, y in food_positions:
        food = entities.Food(
            env,
            x,
            y,
            source_plant=None,
            food_type=None,  # Random type
            allow_stationary_types=False,  # No stationary food at startup
        )
        initial_food.append(food)

    # Create crab and castle
    crab = entities.Crab(env, None, *display_config.init_pos["crab"])
    castle = entities.Castle(env, *display_config.init_pos["castle"])

    # Add all non-fish entities
    population.extend(initial_food + [crab, castle])

    return population
