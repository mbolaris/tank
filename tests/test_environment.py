import math

from core.environment import Environment

class Vec:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def __sub__(self, other):
        return Vec(self.x - other.x, self.y - other.y)
    def length(self):
        return math.hypot(self.x, self.y)

def make_agent(x, y):
    return type('Dummy', (), {'pos': Vec(x, y)})()

def test_nearby_agents():
    a1 = make_agent(0, 0)
    a2 = make_agent(1, 0)
    a3 = make_agent(5, 0)
    env = Environment([a1, a2, a3])
    res = env.nearby_agents(a1, radius=2)
    assert a2 in res
    assert a3 not in res
