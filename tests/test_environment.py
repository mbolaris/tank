import random

from core.environment import Environment
from core.math_utils import Vector2


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


def test_agents_contract_preserves_list_reference():
    rng = random.Random(42)
    a1 = make_agent(0, 0)
    a2 = make_agent(1, 0)
    agents = [a1, a2]

    env = Environment(agents=agents, rng=rng)

    assert env.agents is agents


def test_agents_contract_converts_generator_to_list():
    rng = random.Random(42)
    a1 = make_agent(0, 0)
    a2 = make_agent(1, 0)
    a3 = make_agent(5, 0)

    env = Environment(agents=(a for a in (a1, a2, a3)), rng=rng)

    assert isinstance(env.agents, list)
    assert env.agents == [a1, a2, a3]

    # Spatial grid should be usable after conversion and rebuilds should not crash.
    env.rebuild_spatial_grid()
    res = env.nearby_agents(a1, radius=2)
    assert a2 in res
    assert a3 not in res
