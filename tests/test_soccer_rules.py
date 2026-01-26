import math
from unittest.mock import MagicMock

from core.minigames.soccer.engine import RCSSVector
from core.minigames.soccer.match import SoccerMatch


def create_mock_fish(count=4):
    fish_list = []
    for i in range(count):
        fish = MagicMock()
        fish.fish_id = i
        fish.genome = MagicMock()
        fish.genome.behavioral = MagicMock()
        # Mocking genetic traits to avoid attribute errors
        fish.genome.behavioral.soccer_policy_id = MagicMock(value=None)
        fish.genome.behavioral.soccer_policy_params = MagicMock(value={})
        fish.genome.physical = None  # Usually ignored by create_participants_from_fish
        fish_list.append(fish)
    return fish_list


class TestSoccerRules:
    def test_goal_reset(self):
        """Test that players reset to initial positions after a goal."""
        fish_players = create_mock_fish(2)  # 1 vs 1
        match = SoccerMatch(
            match_id="test_reset", entities=fish_players, duration_frames=1000, seed=42
        )

        # Get initial positions
        initial_pos = {}
        state = match.get_state()
        for entity in state["entities"]:
            if entity["type"] == "player":
                initial_pos[entity["id"]] = (entity["x"], entity["y"])

        # Move players away
        match._engine.get_player("left_1").position = RCSSVector(0, 0)
        match._engine.get_player("right_1").position = RCSSVector(0, 0)

        # Verify moved
        current_state = match.get_state()
        for entity in current_state["entities"]:
            if entity["type"] == "player":
                assert (entity["x"], entity["y"]) == (0, 0)

        # Force a goal event manually
        # We can't easily inject events into step_cycle return without mocking engine,
        # but we can simulate the effect by manually calling _reset_players
        # OR we can actually score a goal.

        # Let's score a goal.
        # Position ball deep in right goal (+x) (must be > half_length + goal_depth = 50 + 2 = 52)
        match._engine.set_ball_position(53, 0)
        # Verify it counts as goal
        info = match._engine._check_goal()
        assert info is not None

        # Step match to process goal
        match.step()

        # Verify players are back at initial positions
        reset_state = match.get_state()
        for entity in reset_state["entities"]:
            if entity["type"] == "player":
                pid = entity["id"]
                orig_x, orig_y = initial_pos[pid]
                assert math.isclose(entity["x"], orig_x, abs_tol=1e-5)
                assert math.isclose(entity["y"], orig_y, abs_tol=1e-5)

    def test_halftime_side_switch(self):
        """Test that teams switch sides at half-time."""
        fish_players = create_mock_fish(2)
        # Duration 10 frames, half time at 5
        match = SoccerMatch(
            match_id="test_swap", entities=fish_players, duration_frames=10, seed=42
        )

        # Capture initial positions
        # left_1 starts at negative x
        p_left = match._engine.get_player("left_1")
        initial_x = p_left.position.x
        assert initial_x < 0

        # Step to half time
        for _ in range(5):
            match.step()

        # Check if sides swapped
        # left_1 should now be at -initial_x (positive)
        p_left_after = match._engine.get_player("left_1")
        assert math.isclose(p_left_after.position.x, -initial_x, abs_tol=1e-5)
        # Angle should be flipped (0 -> pi)
        assert math.isclose(abs(p_left_after.body_angle), math.pi, abs_tol=1e-5)

        # Check engine flag
        assert match._engine._swapped_sides is True

    def test_halftime_reset_ball(self):
        """Test ball resets at half-time."""
        fish_players = create_mock_fish(2)
        match = SoccerMatch(
            match_id="test_ball", entities=fish_players, duration_frames=10, seed=42
        )

        # Move ball away
        match._engine.set_ball_position(20, 20)

        # Step to half time (5)
        for _ in range(5):
            match.step()

        # Ball should be at center
        ball = match._engine.get_ball()
        assert ball.position.x == 0
        assert ball.position.y == 0

    def test_second_half_scoring(self):
        """Test scoring attribution after side switch."""
        fish_players = create_mock_fish(2)
        match = SoccerMatch(
            match_id="test_score_swap", entities=fish_players, duration_frames=10, seed=42
        )

        # Reach half time
        for _ in range(5):
            match.step()

        assert match._engine._swapped_sides is True

        # Now Left Team is on Right Side (positive X).
        # Right Team is on Left Side (negative X).

        # Left Team attacks Left Goal (negative X) - wait.
        # Start: L (-x) attacks R (+x).
        # Swap: L (+x) attacks R (-x).
        # So Left Team attacks Negative X Goal.

        # Place ball in Negative X Goal (Deep check: < -52)
        match._engine.set_ball_position(-53, 0)

        # Check goal
        info = match._engine._check_goal()
        assert info is not None
        # Should be Left Team score
        assert info["team"] == "left"

        # Verify match score update
        match.step()  # Process goal
        state = match.get_state()
        assert state["score"]["left"] == 1
        assert state["score"]["right"] == 0
