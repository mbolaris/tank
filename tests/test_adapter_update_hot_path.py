from contextlib import ExitStack
from typing import cast
from unittest.mock import patch

from core.worlds import WorldRegistry
from core.worlds.tank.backend import TankWorldBackendAdapter


def test_adapter_update_avoids_expensive_calls():
    """Verify that adapter.update() does not call get_stats() or other expensive methods."""

    # Setup via canonical WorldRegistry path
    adapter = cast(
        TankWorldBackendAdapter, WorldRegistry.create_world("tank", seed=42, headless=True)
    )
    adapter.reset(seed=42)

    # Mock the underlying engine's expensive methods
    # We want to ensure these are NOT called during update()
    with ExitStack() as stack:
        from core.simulation.engine import SimulationEngine

        mock_get_stats = stack.enter_context(
            patch.object(SimulationEngine, "get_stats", wraps=adapter.engine.get_stats)
        )
        mock_get_events = stack.enter_context(
            patch.object(
                SimulationEngine, "drain_frame_outputs", wraps=adapter.engine.drain_frame_outputs
            )
        )
        # Action: Run update loop
        for _ in range(10):
            adapter.update()

        # Assertions
        # get_stats should NOT be called
        assert mock_get_stats.call_count == 0, "get_stats() was called during update()!"

        # get_recent_poker_events should NOT be called
        assert (
            mock_get_events.call_count == 0
        ), "get_recent_poker_events() was called during update()!"

        # Verify frame count advanced
        assert adapter.frame_count == 10


def test_adapter_step_uses_lightweight_metrics_by_default():
    """Verify that adapter.step() calls get_stats(include_distributions=False) by default."""

    adapter = WorldRegistry.create_world("tank", seed=42, headless=True)
    adapter.reset(seed=42)

    from core.simulation.engine import SimulationEngine

    with patch.object(SimulationEngine, "get_stats", return_value={}) as mock_get_stats:
        # Action
        adapter.step()

        # Assertion
        # Should be called with include_distributions=False
        mock_get_stats.assert_called_once()
        call_args = mock_get_stats.call_args
        assert (
            call_args.kwargs.get("include_distributions") is False
        ), "step() should request lightweight metrics"
