"""Agent factory for creating initial population with pygame sprites.

This module provides initial population creation for the pygame GUI mode,
wrapping entities in pygame.sprite.Sprite classes from agents.py.
"""

import random
from typing import List
import pygame
from core import environment
from core.constants import FILES, INIT_POS
from core.ecosystem import EcosystemManager
from core.genetics import Genome
import agents
import movement_strategy


def create_initial_agents(
    env: environment.Environment,
    ecosystem: EcosystemManager
) -> List[agents.Agent]:
    """Create initial population as pygame sprites for GUI mode.

    Creates a diverse starting population with multiple species as agents.Agent sprites:
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

    Returns:
        List of Agent sprites (pygame.sprite.Sprite) representing the initial population
    """
    population = []

    # Species 1: Solo fish with traditional AI (rule-based)
    solo_fish = agents.Fish(
        env,
        movement_strategy.SoloFishMovement(),
        FILES['solo_fish'],
        *INIT_POS['fish'],
        3,
        generation=0,
        ecosystem=ecosystem
    )
    population.append(solo_fish)

    # Species 2: Algorithmic fish with parametrizable behavior algorithms
    # These fish use the new algorithmic evolution system
    for i in range(2):  # Start with 2 algorithmic fish for sustainable population
        x = INIT_POS['school'][0] + random.randint(-80, 80)
        y = INIT_POS['school'][1] + random.randint(-50, 50)
        # Create genome WITH behavior algorithm but WITHOUT neural brain
        genome = Genome.random(use_brain=False, use_algorithm=True)
        fish = agents.Fish(
            env,
            movement_strategy.AlgorithmicMovement(),
            FILES['schooling_fish'],
            x, y,
            4,
            genome=genome,
            generation=0,
            ecosystem=ecosystem
        )
        population.append(fish)

    # Species 3: Schooling fish with neural network brains (learning AI)
    for i in range(2):  # Fewer neural fish to start
        x = INIT_POS['school'][0] + random.randint(-50, 50)
        y = INIT_POS['school'][1] + random.randint(-30, 30)
        # Neural fish should NOT have algorithmic behavior (use brain instead)
        genome = Genome.random(use_brain=True, use_algorithm=False)
        fish = agents.Fish(
            env,
            movement_strategy.NeuralMovement(),
            FILES['schooling_fish'],
            x, y,
            4,
            genome=genome,
            generation=0,
            ecosystem=ecosystem
        )
        population.append(fish)

    # Species 4: Traditional schooling fish (rule-based AI)
    for i in range(2):  # Also 2 traditional schooling fish
        x = INIT_POS['school'][0] + random.randint(-50, 50)
        y = INIT_POS['school'][1] + random.randint(-30, 30)
        # Create genome without neural brain or algorithm (uses movement strategy only)
        genome = Genome.random(use_brain=False, use_algorithm=False)
        fish = agents.Fish(
            env,
            movement_strategy.SchoolingFishMovement(),
            FILES['schooling_fish'],
            x, y,
            4,
            genome=genome,
            generation=0,
            ecosystem=ecosystem
        )
        population.append(fish)

    # Create plants at predefined positions
    plant1 = agents.Plant(env, 1)
    plant2 = agents.Plant(env, 2)
    # Third plant manually positioned
    plant3 = agents.Plant(env, 1)
    plant3.pos.x = INIT_POS['plant3'][0]
    plant3.pos.y = INIT_POS['plant3'][1]
    plant3.rect.topleft = (plant3.pos.x, plant3.pos.y)

    # Create crab and castle
    crab = agents.Crab(env)
    castle = agents.Castle(env)

    # Add all non-fish entities
    population.extend([plant1, plant2, plant3, crab, castle])

    return population
