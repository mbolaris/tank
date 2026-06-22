import random
from unittest.mock import MagicMock

from core.config.fish import LIFE_STAGE_MATURE_MAX
from core.entities.fish import Fish
from core.genetics import Genome
from core.movement_strategy import AlgorithmicMovement


def _mock_environment():
    env = MagicMock()
    env.rng = random.Random(42)
    env.width = 800
    env.height = 600
    env.tank_bounds = MagicMock()
    env.tank_bounds.left = 0
    env.tank_bounds.right = 800
    env.tank_bounds.top = 0
    env.tank_bounds.bottom = 600
    env.tank_bounds.water_top = 50
    env.add_entity = MagicMock()
    env.food_list = []
    env.simulation_config = None
    return env


def _fish_with_traits(size_modifier: float, lifespan_modifier: float) -> Fish:
    env = _mock_environment()
    genome = Genome.random(rng=env.rng)
    genome.physical.size_modifier.value = size_modifier
    genome.physical.lifespan_modifier.value = lifespan_modifier
    genome.invalidate_caches()

    return Fish(
        environment=env,
        movement_strategy=AlgorithmicMovement(),
        species="test",
        x=100,
        y=100,
        speed=5,
        genome=genome,
    )


def test_lifespan_modifier_controls_max_age_independent_of_body_size():
    small = _fish_with_traits(size_modifier=0.5, lifespan_modifier=1.2)
    large = _fish_with_traits(size_modifier=2.0, lifespan_modifier=1.2)

    assert small.max_age == int(LIFE_STAGE_MATURE_MAX * 1.2)
    assert large.max_age == small.max_age
    assert large.size > small.size
    assert large.max_energy > small.max_energy


def test_lifespan_trait_still_changes_max_age():
    normal = _fish_with_traits(size_modifier=1.0, lifespan_modifier=1.0)
    long_lived = _fish_with_traits(size_modifier=1.0, lifespan_modifier=1.4)

    assert normal.max_age == LIFE_STAGE_MATURE_MAX
    assert long_lived.max_age == int(LIFE_STAGE_MATURE_MAX * 1.4)
    assert long_lived.max_age > normal.max_age
