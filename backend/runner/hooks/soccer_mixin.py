"""Soccer functionality mixin for world hooks.

This module provides a mixin class that adds soccer event collection
functionality to world hooks that support soccer gameplay.
"""

from typing import Any, List, Optional

from backend.state_payloads import SoccerEventPayload


class SoccerMixin:
    """Mixin that provides soccer event collection functionality.

    Add this mixin to any hooks class that needs to support soccer
    game events and league state.
    """

    def collect_soccer_events(self, runner: Any) -> Optional[List[SoccerEventPayload]]:
        """Collect soccer events from the world engine.

        Args:
            runner: The SimulationRunner instance

        Returns:
            List of soccer event payloads, or None if not available
        """
        engine = getattr(runner.world, "engine", None)
        if engine is None or not hasattr(engine, "get_recent_soccer_events"):
            return None

        soccer_events: List[SoccerEventPayload] = []
        recent_events = engine.get_recent_soccer_events(max_age_frames=60)
        for event in recent_events:
            soccer_events.append(
                SoccerEventPayload(
                    frame=event["frame"],
                    match_id=event["match_id"],
                    match_counter=event.get("match_counter", 0),
                    winner_team=event.get("winner_team"),
                    score_left=event.get("score_left", 0),
                    score_right=event.get("score_right", 0),
                    frames=event.get("frames", 0),
                    seed=event.get("seed"),
                    selection_seed=event.get("selection_seed"),
                    message=event.get("message"),
                    rewarded=event.get("rewarded", {}),
                    entry_fees=event.get("entry_fees", {}),
                    energy_deltas=event.get("energy_deltas", {}),
                    repro_credit_deltas=event.get("repro_credit_deltas", {}),
                    teams=event.get("teams", {}),
                    last_goal=event.get("last_goal"),
                    skipped=event.get("skipped", False),
                    skip_reason=event.get("skip_reason"),
                )
            )

        return soccer_events

    def collect_soccer_league_live(self, runner: Any) -> Optional[dict]:
        """Collect soccer league live state.

        Args:
            runner: The SimulationRunner instance

        Returns:
            Soccer league live state dict, or None if not available
        """
        # Try direct method on world (e.g. TankWorldBackendAdapter)
        get_live = getattr(runner.world, "get_soccer_league_live_state", None)
        if callable(get_live):
            live = get_live()
            return live if isinstance(live, dict) else None

        # Try via engine
        engine = getattr(runner.world, "engine", None)
        if engine is None and hasattr(runner.world, "world"):
            # Handle adapter wrapper
            engine = getattr(runner.world.world, "engine", None)

        if engine is None or not hasattr(engine, "get_soccer_league_live_state"):
            return None

        live = engine.get_soccer_league_live_state()
        return live if isinstance(live, dict) else None
