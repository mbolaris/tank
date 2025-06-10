"""Minimal Petting Zoo-style environment wrapper for the tank simulation."""

from __future__ import annotations

from typing import Dict, Tuple, Optional

try:
    from pettingzoo.utils.env import ParallelEnv  # type: ignore
except Exception:  # pragma: no cover - allow running without pettingzoo
    class ParallelEnv:
        """Fallback base when pettingzoo is unavailable."""
        pass

# Use the lightweight Environment from this package
from environment import Environment


class Vec:
    """Simple 2D vector used when Pygame's Vector2 isn't available."""

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def __add__(self, other: "Vec") -> "Vec":
        return Vec(self.x + other.x, self.y + other.y)

    def __iter__(self):
        yield self.x
        yield self.y


class TankEnv(ParallelEnv):
    """Very small PettingZoo-style environment exposing a single agent."""

    metadata = {"render_modes": ["none"], "name": "tank"}

    def __init__(self, render_mode: Optional[str] = None):
        self.render_mode = render_mode
        self.environment = Environment([])
        self.agents = ["fish_0"]
        self.pos: Dict[str, Vec] = {"fish_0": Vec(0.0, 0.0)}
        self._steps = 0

    def reset(self, seed: Optional[int] = None, options: Optional[dict] = None):
        self._steps = 0
        self.pos["fish_0"] = Vec(0.0, 0.0)
        return {"fish_0": tuple(self.pos["fish_0"])}

    def step(self, actions: Dict[str, Tuple[float, float]]):
        action = actions.get("fish_0", (0.0, 0.0))
        dx, dy = action
        self.pos["fish_0"] = self.pos["fish_0"] + Vec(dx, dy)
        self._steps += 1
        observations = {"fish_0": tuple(self.pos["fish_0"])}
        rewards = {"fish_0": 0.0}
        terminations = {"fish_0": False}
        truncations = {"fish_0": self._steps >= 10}
        infos = {"fish_0": {}}
        return observations, rewards, terminations, truncations, infos

    def render(self):  # pragma: no cover - simple text render
        if self.render_mode == "none":
            return
        print(f"Agent at {self.pos['fish_0']}")
