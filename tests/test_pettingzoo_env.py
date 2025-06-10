import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import pytest

try:
    import pygame  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    pygame = None

if pygame is not None:
    from fishtank_pz import FishTankPZEnv


@pytest.mark.skipif(pygame is None, reason="pygame not installed")
def test_reset_returns_observations():
    env = FishTankPZEnv()
    obs = env.reset()
    assert isinstance(obs, dict)
    assert len(obs) > 0
    env.close()

