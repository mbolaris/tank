import math
import random
from types import SimpleNamespace

from core.algorithms.composable.behavior import ComposableBehavior
from core.algorithms.composable.definitions import (
    FoodApproach,
    PokerEngagement,
    SocialMode,
    ThreatResponse,
)
from core.entities.resources import Food
from core.genetics import Genome
from core.genetics.trait import GeneticTrait
from core.math_utils import Vector2


class _FoodEnv:
    def __init__(self, food):
        self.rng = random.Random(42)
        self.food = food

    def get_detection_modifier(self):
        return 1.0

    def nearby_agents_by_type(self, fish, radius, agent_type):
        return [self.food] if agent_type is Food else []

    def nearby_resources(self, fish, radius):
        return [self.food]


class _FishStub:
    def __init__(self):
        self.pos = Vector2(0, 0)
        self.vel = Vector2(0, 0)
        self.speed = 1.0
        self.energy = 75
        self.max_energy = 150
        self.genome = Genome.random(use_algorithm=True, rng=random.Random(7))
        self.genome.behavioral.pursuit_aggression = GeneticTrait(0.5)
        self.genome.behavioral.prediction_skill = GeneticTrait(0.5)
        self.genome.behavioral.hunting_stamina = GeneticTrait(1.0)

    def can_eat(self):
        return True


def test_zigzag_search_preserves_pattern_without_exceeding_pursuit_speed_budget():
    food = SimpleNamespace(
        pos=Vector2(100, 0),
        vel=Vector2(0, 0),
        get_energy_value=lambda: 10.0,
    )
    fish = _FishStub()
    fish.environment = _FoodEnv(food)
    behavior = ComposableBehavior(
        ThreatResponse.FREEZE,
        FoodApproach.ZIGZAG_SEARCH,
        SocialMode.SOLO,
        PokerEngagement.PASSIVE,
        {
            "pursuit_speed": 0.9,
            "zigzag_amplitude": 0.6,
            "zigzag_frequency": 0.05,
        },
    )

    direct_speed_budget = 0.9 * (1.0 + 0.5 * 0.4) * (1.0 + (1.0 - 0.5) * 0.3)
    magnitudes = []
    lateral_components = []

    for _ in range(160):
        vx, vy = behavior._execute_food_approach(fish)
        magnitudes.append(math.hypot(vx, vy))
        lateral_components.append(abs(vy))

    assert max(magnitudes) <= direct_speed_budget + 1e-9
    assert max(lateral_components) > 0.01
