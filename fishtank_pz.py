"""PettingZoo-style environment wrapper for the fish tank simulation."""

from typing import Dict, Tuple

# Avoid importing pygame during unit tests
try:  # pragma: no cover - optional dependency
    import pygame
except Exception:  # pragma: no cover - fallback when pygame is unavailable
    pygame = None

try:  # pragma: no cover - optional dependency
    import fishtank
except Exception:  # pragma: no cover - fallback when pygame is unavailable
    fishtank = None


class FishTankPZEnv:
    """Simplified PettingZoo-like interface for the fish tank simulator."""

    metadata = {"render_mode": ["human"]}

    def __init__(self):
        if fishtank is None:
            raise ImportError("fishtank and pygame are required to use FishTankPZEnv")
        self.simulator = fishtank.FishTankSimulator()
        self.agents = []

    def reset(self) -> Dict[str, Tuple[int, int]]:
        """Reset the environment and return initial observations."""
        if pygame:
            pygame.init()
        self.simulator.setup_game()
        self.agents = [f"agent_{i}" for i, _ in enumerate(self.simulator.agents)]
        return self._get_observations()

    def step(self, actions: Dict[str, int]):
        """Advance the simulation one step."""
        # Actions are ignored for now; this is a structural placeholder
        self.simulator.update()
        observations = self._get_observations()
        rewards = {agent: 0.0 for agent in self.agents}
        dones = {agent: False for agent in self.agents}
        infos = {agent: {} for agent in self.agents}
        return observations, rewards, dones, infos

    def render(self):
        if pygame:
            self.simulator.render()

    def close(self):
        if pygame:
            pygame.quit()

    def _get_observations(self) -> Dict[str, Tuple[int, int]]:
        """Return positions of all sprites as observations."""
        return {
            f"agent_{i}": (sprite.rect.x, sprite.rect.y)
            for i, sprite in enumerate(self.simulator.agents)
        }

