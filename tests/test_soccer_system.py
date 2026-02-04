"""Unit tests for SoccerSystem.

Tests the soccer system's energy accounting, team selection,
deterministic kicker selection, and kick timing.
"""

from typing import Optional
from unittest.mock import MagicMock, Mock

import pytest

from core.entities.ball import Ball
from core.math_utils import Vector2
from core.systems.soccer_system import SoccerSystem


class MockFish:
    """Minimal fish mock for soccer system testing."""

    def __init__(
        self,
        fish_id: int,
        x: float,
        y: float,
        team: Optional[str] = None,
        vel: Optional[Vector2] = None,
    ):
        self.fish_id = fish_id
        self.pos = Vector2(x, y)
        self.vel = vel or Vector2(0.0, 0.0)
        self.team = team
        self.snapshot_type = "fish"
        self.energy = 50.0
        self.max_energy = 100.0
        self.soccer_effect_state = None
        self._modify_energy_calls: list[tuple[float, str]] = []

    def is_dead(self) -> bool:
        return False

    def modify_energy(self, amount: float, *, source: str = "unknown") -> float:
        """Track modify_energy calls for testing."""
        self._modify_energy_calls.append((amount, source))
        old = self.energy
        self.energy = min(self.energy + amount, self.max_energy)
        return self.energy - old


class TestSoccerSystemEnergyAccounting:
    """Test that energy changes use modify_energy properly."""

    def test_kick_uses_modify_energy(self):
        """Kicking the ball should use modify_energy with source='soccer_kick'."""
        mock_engine = MagicMock()
        mock_env = MagicMock()
        mock_env.width = 800
        mock_env.height = 600
        mock_engine.environment = mock_env

        ball = Ball(mock_env, 400, 300)
        fish = MockFish(fish_id=1, x=400, y=310, team="A")  # Within 30px of ball

        mock_engine.entities_list = [fish]

        system = SoccerSystem(mock_engine)
        system.ball = ball
        system.enabled = True

        system._process_auto_kicks(frame=0)

        # Verify modify_energy was called with correct source
        assert len(fish._modify_energy_calls) == 1
        amount, source = fish._modify_energy_calls[0]
        assert amount == 2.0
        assert source == "soccer_kick"

    def test_goal_uses_modify_energy(self):
        """Scoring a goal should use modify_energy with source='soccer_goal'."""
        mock_engine = MagicMock()
        mock_env = MagicMock()
        mock_env.width = 800
        mock_env.height = 600
        mock_engine.environment = mock_env

        ball = Ball(mock_env, 400, 300)
        fish = MockFish(fish_id=42, x=100, y=100, team="A")

        mock_engine.entities_list = [fish]

        def get_fish_list():
            return [fish]

        mock_engine.get_fish_list = get_fish_list

        system = SoccerSystem(mock_engine)
        system.ball = ball
        system.enabled = True

        # Create a mock goal event
        mock_goal_event = MagicMock()
        mock_goal_event.scorer_id = 42
        mock_goal_event.team = "A"
        mock_goal_event.goal_id = "goal_left"
        mock_goal_event.timestamp = 100

        system._handle_goal_scored(mock_goal_event)

        # Verify modify_energy was called with correct source
        assert len(fish._modify_energy_calls) == 1
        amount, source = fish._modify_energy_calls[0]
        assert amount == 50.0
        assert source == "soccer_goal"


class TestSoccerSystemTeamSelection:
    """Test that team selection uses fish.team when available."""

    def test_uses_fish_team_when_set(self):
        """Should use fish.team attribute when it's set."""
        mock_engine = MagicMock()
        mock_env = MagicMock()
        mock_env.width = 800
        mock_env.height = 600
        mock_engine.environment = mock_env

        ball = Ball(mock_env, 400, 300)

        # Fish with explicit team="B" but odd fish_id (would be team B anyway)
        fish = MockFish(fish_id=3, x=400, y=310, team="B")

        mock_engine.entities_list = [fish]

        system = SoccerSystem(mock_engine)
        system.ball = ball
        system.enabled = True

        # Track kick direction to verify team logic
        original_vel = ball.vel.x

        system._process_auto_kicks(frame=0)

        # Team B kicks toward left goal (negative x direction when stationary)
        # The kick should have been applied
        assert ball.acceleration.x != 0 or ball.vel.x != original_vel

    def test_uses_fish_team_a_for_direction(self):
        """Fish with team='A' should kick toward the right goal."""
        mock_engine = MagicMock()
        mock_env = MagicMock()
        mock_env.width = 800
        mock_env.height = 600
        mock_engine.environment = mock_env

        # Ball at center
        ball = Ball(mock_env, 400, 300)

        # Fish with team A, stationary (will kick toward opponent goal)
        fish = MockFish(fish_id=1, x=400, y=310, team="A", vel=Vector2(0, 0))

        mock_engine.entities_list = [fish]

        system = SoccerSystem(mock_engine)
        system.ball = ball
        system.enabled = True

        system._process_auto_kicks(frame=0)

        # Team A kicks toward right (positive x) - check acceleration
        assert ball.acceleration.x > 0

    def test_uses_fish_team_b_for_direction(self):
        """Fish with team='B' should kick toward the left goal."""
        mock_engine = MagicMock()
        mock_env = MagicMock()
        mock_env.width = 800
        mock_env.height = 600
        mock_engine.environment = mock_env

        # Ball at center
        ball = Ball(mock_env, 400, 300)

        # Fish with team B, stationary (will kick toward opponent goal)
        fish = MockFish(fish_id=2, x=400, y=310, team="B", vel=Vector2(0, 0))

        mock_engine.entities_list = [fish]

        system = SoccerSystem(mock_engine)
        system.ball = ball
        system.enabled = True

        system._process_auto_kicks(frame=0)

        # Team B kicks toward left (negative x) - check acceleration
        assert ball.acceleration.x < 0

    def test_fallback_to_fish_id_parity_when_team_none(self):
        """Should fall back to fish_id parity when team is None."""
        mock_engine = MagicMock()
        mock_env = MagicMock()
        mock_env.width = 800
        mock_env.height = 600
        mock_engine.environment = mock_env

        ball = Ball(mock_env, 400, 300)

        # Fish with team=None and even fish_id (should be team A)
        fish = MockFish(fish_id=4, x=400, y=310, team=None, vel=Vector2(0, 0))

        mock_engine.entities_list = [fish]

        system = SoccerSystem(mock_engine)
        system.ball = ball
        system.enabled = True

        system._process_auto_kicks(frame=0)

        # Even fish_id -> team A -> kicks right (positive x)
        assert ball.acceleration.x > 0


class TestSoccerSystemDeterministicKickerSelection:
    """Test that kicker selection is deterministic."""

    def test_closest_fish_kicks(self):
        """The closest fish to the ball should kick."""
        mock_engine = MagicMock()
        mock_env = MagicMock()
        mock_env.width = 800
        mock_env.height = 600
        mock_engine.environment = mock_env

        ball = Ball(mock_env, 400, 300)

        # Two fish: one closer, one farther
        fish_far = MockFish(fish_id=1, x=400, y=325, team="A")  # 25px away
        fish_close = MockFish(fish_id=2, x=400, y=310, team="B")  # 10px away

        # Order in list shouldn't matter
        mock_engine.entities_list = [fish_far, fish_close]

        system = SoccerSystem(mock_engine)
        system.ball = ball
        system.enabled = True

        system._process_auto_kicks(frame=0)

        # Only the closer fish should have kicked
        assert len(fish_close._modify_energy_calls) == 1
        assert len(fish_far._modify_energy_calls) == 0

    def test_fish_id_breaks_ties(self):
        """When distances are equal, smaller fish_id should kick."""
        mock_engine = MagicMock()
        mock_env = MagicMock()
        mock_env.width = 800
        mock_env.height = 600
        mock_engine.environment = mock_env

        ball = Ball(mock_env, 400, 300)

        # Two fish at exactly the same distance (15px each)
        fish_high_id = MockFish(fish_id=99, x=400, y=315, team="A")
        fish_low_id = MockFish(fish_id=1, x=400, y=285, team="B")

        # Order in list shouldn't matter - put higher ID first
        mock_engine.entities_list = [fish_high_id, fish_low_id]

        system = SoccerSystem(mock_engine)
        system.ball = ball
        system.enabled = True

        system._process_auto_kicks(frame=0)

        # Lower fish_id should have kicked (tie-breaker)
        assert len(fish_low_id._modify_energy_calls) == 1
        assert len(fish_high_id._modify_energy_calls) == 0

    def test_kicker_selection_is_repeatable(self):
        """Same setup should always produce same kicker."""
        mock_engine = MagicMock()
        mock_env = MagicMock()
        mock_env.width = 800
        mock_env.height = 600
        mock_engine.environment = mock_env

        # Run the same setup multiple times
        kickers = []

        for _ in range(5):
            ball = Ball(mock_env, 400, 300)

            fish1 = MockFish(fish_id=10, x=395, y=300, team="A")
            fish2 = MockFish(fish_id=20, x=405, y=300, team="B")
            fish3 = MockFish(fish_id=5, x=400, y=305, team="A")

            mock_engine.entities_list = [fish1, fish2, fish3]

            system = SoccerSystem(mock_engine)
            system.ball = ball
            system.enabled = True

            system._process_auto_kicks(frame=0)

            # Find which fish kicked
            for fish in [fish1, fish2, fish3]:
                if fish._modify_energy_calls:
                    kickers.append(fish.fish_id)
                    break

        # All iterations should select the same kicker
        assert len(set(kickers)) == 1


class TestSoccerSystemKickTiming:
    """Test that kicks are applied before ball physics update."""

    def test_kick_affects_same_frame_physics(self):
        """Kicks should affect ball state in the same _do_update call."""
        mock_engine = MagicMock()
        mock_env = MagicMock()
        mock_env.width = 800
        mock_env.height = 600
        mock_env.get_bounds = Mock(return_value=((0, 0), (800, 600)))
        mock_engine.environment = mock_env

        ball = Ball(mock_env, 400, 300)
        fish = MockFish(fish_id=1, x=400, y=310, team="A")

        mock_engine.entities_list = [fish]

        system = SoccerSystem(mock_engine)
        system.ball = ball
        system.goal_manager = None
        system.enabled = True

        # Verify fish gets the energy reward (proves kick happened in same frame)
        assert len(fish._modify_energy_calls) == 0

        # Track ball.kick calls to verify it was called
        kick_calls = []
        original_kick = ball.kick

        def tracked_kick(power, direction, kicker=None):
            kick_calls.append((power, direction, kicker))
            return original_kick(power, direction, kicker=kicker)

        ball.kick = tracked_kick

        # Run full update (kicks then physics)
        system._do_update(frame=0)

        # Kick should have happened and energy awarded in the same _do_update call
        assert len(fish._modify_energy_calls) == 1
        assert fish._modify_energy_calls[0] == (2.0, "soccer_kick")

        # Ball.kick should have been called with appropriate power
        assert len(kick_calls) == 1
        power, direction, kicker = kick_calls[0]
        assert power >= 40.0  # Base power
        assert kicker is fish

    def test_kick_order_is_kick_then_physics(self):
        """Verify the order: kicks processed, then ball.update called."""
        mock_engine = MagicMock()
        mock_env = MagicMock()
        mock_env.width = 800
        mock_env.height = 600
        mock_env.get_bounds = Mock(return_value=((0, 0), (800, 600)))
        mock_engine.environment = mock_env

        ball = Ball(mock_env, 400, 300)

        # Track call order
        call_order = []

        original_kick = ball.kick

        def tracked_kick(*args, **kwargs):
            call_order.append("kick")
            return original_kick(*args, **kwargs)

        original_update = ball.update

        def tracked_update(*args, **kwargs):
            call_order.append("update")
            return original_update(*args, **kwargs)

        ball.kick = tracked_kick
        ball.update = tracked_update

        fish = MockFish(fish_id=1, x=400, y=310, team="A")
        mock_engine.entities_list = [fish]

        system = SoccerSystem(mock_engine)
        system.ball = ball
        system.goal_manager = None
        system.enabled = True

        system._do_update(frame=0)

        # Kick should come before update
        assert call_order == ["kick", "update"]


class TestSoccerSystemEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_no_fish_in_range(self):
        """No kick should occur when no fish is within range."""
        mock_engine = MagicMock()
        mock_env = MagicMock()
        mock_env.width = 800
        mock_env.height = 600
        mock_engine.environment = mock_env

        ball = Ball(mock_env, 400, 300)

        # Fish too far from ball (>30px)
        fish = MockFish(fish_id=1, x=400, y=350, team="A")  # 50px away

        mock_engine.entities_list = [fish]

        system = SoccerSystem(mock_engine)
        system.ball = ball
        system.enabled = True

        initial_accel = ball.acceleration.x

        system._process_auto_kicks(frame=0)

        # No kick should have occurred
        assert len(fish._modify_energy_calls) == 0
        assert ball.acceleration.x == initial_accel

    def test_dead_fish_cannot_kick(self):
        """Dead fish should not be able to kick."""
        mock_engine = MagicMock()
        mock_env = MagicMock()
        mock_env.width = 800
        mock_env.height = 600
        mock_engine.environment = mock_env

        ball = Ball(mock_env, 400, 300)

        # Create a dead fish
        fish = MockFish(fish_id=1, x=400, y=310, team="A")
        fish.is_dead = lambda: True  # Override to return True

        mock_engine.entities_list = [fish]

        system = SoccerSystem(mock_engine)
        system.ball = ball
        system.enabled = True

        system._process_auto_kicks(frame=0)

        # Dead fish should not kick
        assert len(fish._modify_energy_calls) == 0

    def test_only_one_fish_kicks_per_frame(self):
        """Only one fish should kick per frame, even with multiple in range."""
        mock_engine = MagicMock()
        mock_env = MagicMock()
        mock_env.width = 800
        mock_env.height = 600
        mock_engine.environment = mock_env

        ball = Ball(mock_env, 400, 300)

        # Multiple fish all in range
        fish1 = MockFish(fish_id=1, x=400, y=310, team="A")
        fish2 = MockFish(fish_id=2, x=410, y=300, team="B")
        fish3 = MockFish(fish_id=3, x=390, y=300, team="A")

        mock_engine.entities_list = [fish1, fish2, fish3]

        system = SoccerSystem(mock_engine)
        system.ball = ball
        system.enabled = True

        system._process_auto_kicks(frame=0)

        # Count total kicks
        total_kicks = sum(len(f._modify_energy_calls) for f in [fish1, fish2, fish3])
        assert total_kicks == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
