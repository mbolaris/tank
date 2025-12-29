from core.environment import Environment
from core.math_utils import Vector2
import random


def make_agent(x, y):
    return type("Dummy", (), {"pos": Vector2(x, y)})()


def test_nearby_agents():
    rng = random.Random(42)  # Deterministic seed
    a1 = make_agent(0, 0)
    a2 = make_agent(1, 0)
    a3 = make_agent(5, 0)
    env = Environment([a1, a2, a3], rng=rng)
    res = env.nearby_agents(a1, radius=2)
    assert a2 in res
    assert a3 not in res
