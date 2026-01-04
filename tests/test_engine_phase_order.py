"""Tests for engine phase ordering correctness."""


def test_poker_runs_every_frame_regardless_of_energy_events(simulation_engine):
    """Poker system must run every frame, even with zero energy events.

    The poker system is called via handle_mixed_poker_games() during the
    interaction phase. This test verifies it runs consistently.
    """
    engine = simulation_engine

    # Track poker calls by patching handle_mixed_poker_games
    original_handle = engine.poker_system.handle_mixed_poker_games
    call_count = 0

    def tracked_handle():
        nonlocal call_count
        call_count += 1
        return original_handle()

    engine.poker_system.handle_mixed_poker_games = tracked_handle

    # Run 5 frames
    for _ in range(5):
        engine.update()

    assert call_count == 5, f"Poker should run every frame, got {call_count} calls in 5 frames"
