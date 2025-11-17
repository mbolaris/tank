from pygame.math import Vector2

from core.environment import Environment


def make_agent(x, y):
    return type('Dummy', (), {'pos': Vector2(x, y)})()


def test_nearby_agents():
    a1 = make_agent(0, 0)
    a2 = make_agent(1, 0)
    a3 = make_agent(5, 0)
    env = Environment([a1, a2, a3])
    res = env.nearby_agents(a1, radius=2)
    assert a2 in res
    assert a3 not in res
