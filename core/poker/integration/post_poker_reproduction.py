"""Post-poker reproduction orchestration helpers."""

from __future__ import annotations

from typing import Any

from core.poker.integration.poker_rewards import annotate_reproduction_reward


def handle_fish_post_poker_reproduction(
    engine: Any,
    poker: Any,
    event: dict[str, Any] | None,
) -> None:
    """Try sexual post-poker reproduction for fish winners with fish opponents."""
    result = getattr(poker, "result", None)
    if result is None or getattr(result, "is_tie", False):
        return
    if getattr(result, "winner_type", "") != "fish":
        return
    if getattr(result, "fish_count", 0) < 2:
        return

    reproduction_service = getattr(engine, "reproduction_service", None)
    if reproduction_service is None:
        return

    baby = reproduction_service.handle_post_poker_reproduction(poker)
    if baby is not None:
        annotate_reproduction_reward(event, getattr(result, "winner_id", None), baby)
