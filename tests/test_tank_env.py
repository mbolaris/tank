import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from tank_env import TankEnv


def test_reset_step():
    env = TankEnv()
    obs = env.reset()
    assert "fish_0" in obs
    first_pos = obs["fish_0"]

    obs, reward, term, trunc, info = env.step({"fish_0": (1.0, 0.0)})
    assert obs["fish_0"][0] == first_pos[0] + 1.0
    assert not term["fish_0"]
    # after enough steps, truncation should occur
    for _ in range(9):
        obs, _, _, trunc, _ = env.step({"fish_0": (0.0, 0.0)})
    assert trunc["fish_0"]
