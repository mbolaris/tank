"""Tests for engine phase ordering correctness."""


def test_poker_runs_every_frame_regardless_of_energy_events(simulation_engine):
    """Poker system must run every frame, even with zero energy events."""
    engine = simulation_engine

    # Clear any pending events
    engine.pending_sim_events.clear()

    # Track poker calls
    original_update = engine.poker_system.update
    call_count = 0

    def tracked_update(frame_count):
        nonlocal call_count
        call_count += 1
        return original_update(frame_count)

    engine.poker_system.update = tracked_update

    # Run 5 frames with no energy events
    for _ in range(5):
        engine.pending_sim_events.clear()
        engine.update()

    assert call_count == 5, f"Poker should run every frame, got {call_count} calls in 5 frames"
