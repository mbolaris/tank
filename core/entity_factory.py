"""Entity factory for creating initial population.

This module provides a single source of truth for initial population creation,
used by both the pygame GUI mode (fishtank.py) and headless mode (simulation_engine.py).
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
    screen_height: int = SCREEN_HEIGHT
) -> List[entities.Agent]:
    """Create initial population for simulation.

    Creates a diverse starting population with multiple species:
    - 1 solo fish (traditional rule-based AI)
    - 2 algorithmic fish (parametrizable behavior algorithms)
    - 2 neural fish (neural network brains)
    - 2 traditional schooling fish (rule-based schooling)
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

    # Species 1: Solo fish with traditional AI (rule-based)
    solo_fish = entities.Fish(
        env,
        movement_strategy.SoloFishMovement(),
        FILES['solo_fish'][0],
        *INIT_POS['fish'],
        3,
        generation=0,
        ecosystem=ecosystem,
        screen_width=screen_width,
        screen_height=screen_height
    )
    population.append(solo_fish)

    # Species 2: Algorithmic fish with parametrizable behavior algorithms
    # These fish use the new algorithmic evolution system
    for i in range(2):  # Start with 2 algorithmic fish for sustainable population
        x = INIT_POS['school'][0] + random.randint(-80, 80)
        y = INIT_POS['school'][1] + random.randint(-50, 50)
        # Create genome WITH behavior algorithm but WITHOUT neural brain
        genome = Genome.random(use_brain=False, use_algorithm=True)
        fish = entities.Fish(
            env,
            movement_strategy.AlgorithmicMovement(),
            FILES['schooling_fish'][0],
            x, y,
            4,
            genome=genome,
            generation=0,
            ecosystem=ecosystem,
            screen_width=screen_width,
            screen_height=screen_height
        )
        population.append(fish)

    # Species 3: Schooling fish with neural network brains (learning AI)
    for i in range(2):  # Fewer neural fish to start
        x = INIT_POS['school'][0] + random.randint(-50, 50)
        y = INIT_POS['school'][1] + random.randint(-30, 30)
        # Neural fish should NOT have algorithmic behavior (use brain instead)
        genome = Genome.random(use_brain=True, use_algorithm=False)
        fish = entities.Fish(
            env,
            movement_strategy.NeuralMovement(),
            FILES['schooling_fish'][0],
            x, y,
            4,
            genome=genome,
            generation=0,
            ecosystem=ecosystem,
            screen_width=screen_width,
            screen_height=screen_height
        )
        population.append(fish)

    # Species 4: Traditional schooling fish (rule-based AI)
    for i in range(2):  # Also 2 traditional schooling fish
        x = INIT_POS['school'][0] + random.randint(-50, 50)
        y = INIT_POS['school'][1] + random.randint(-30, 30)
        # Create genome without neural brain or algorithm (uses movement strategy only)
        genome = Genome.random(use_brain=False, use_algorithm=False)
        fish = entities.Fish(
            env,
            movement_strategy.SchoolingFishMovement(),
            FILES['schooling_fish'][0],
            x, y,
            4,
            genome=genome,
            generation=0,
            ecosystem=ecosystem,
            screen_width=screen_width,
            screen_height=screen_height
        )
        population.append(fish)

    # Create plants at predefined positions
    plant1 = entities.Plant(env, 1, *INIT_POS['plant1'], screen_width, screen_height)
    plant2 = entities.Plant(env, 2, *INIT_POS['plant2'], screen_width, screen_height)
    plant3 = entities.Plant(env, 1, *INIT_POS['plant3'], screen_width, screen_height)

    # Create crab and castle
    crab = entities.Crab(env, None, *INIT_POS['crab'], screen_width, screen_height)
    castle = entities.Castle(env, *INIT_POS['castle'], screen_width, screen_height)

    # Add all non-fish entities
    population.extend([plant1, plant2, plant3, crab, castle])

    return population
