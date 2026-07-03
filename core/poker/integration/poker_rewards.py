"""Per-fish reward accounting for poker games.

These helpers turn a completed poker interaction into the reward-log detail
surfaced under the poker table in the UI: net energy per fish, reproduction
credits banked by the winner, and any reproduction the win earned. They are
kept out of PokerSystem so the system stays focused on orchestration.
"""

from __future__ import annotations

from typing import Any


def fish_energy_deltas(poker: Any) -> dict[str, float]:
    """Net per-fish energy change over the hand (winnings minus bets).

    Keys are stringified fish ids to match the JSON shape used by soccer
    reward events. Plants are excluded: the reward log is about fish.
    Duck-types on fish_id (like MixedPokerInteraction._is_fish_player) so
    reloaded modules and test doubles are handled.
    """
    initial = getattr(poker, "_initial_player_energies", None)
    players = getattr(poker, "players", [])
    if initial is None or len(initial) != len(players):
        return {}

    deltas: dict[str, float] = {}
    for idx, player in enumerate(players):
        if hasattr(player, "fish_id"):
            delta = float(getattr(player, "energy", 0.0)) - float(initial[idx])
            deltas[str(player.fish_id)] = delta
    return deltas


def award_winner_repro_credits(poker: Any) -> dict[str, float]:
    """Award reproduction credits to a winning fish (mirrors soccer rewards).

    Returns:
        Mapping of stringified fish id to credits awarded (empty on tie,
        plant win, or when the award is disabled).
    """
    from core.config.poker import POKER_REPRO_CREDIT_AWARD

    if POKER_REPRO_CREDIT_AWARD <= 0:
        return {}

    result = getattr(poker, "result", None)
    if result is None or getattr(result, "is_tie", False):
        return {}
    if getattr(result, "winner_type", "") != "fish":
        return {}

    for player in getattr(poker, "fish_players", []):
        if not hasattr(player, "fish_id"):
            continue
        if poker._get_player_id(player) != result.winner_id:
            continue
        component = getattr(player, "_reproduction_component", None)
        if component is None or not hasattr(component, "add_repro_credits"):
            return {}
        applied = component.add_repro_credits(POKER_REPRO_CREDIT_AWARD)
        if applied:
            return {str(player.fish_id): float(applied)}
        return {}
    return {}


def annotate_reproduction_reward(
    event: dict[str, Any] | None, parent_id: int | None, baby: Any
) -> None:
    """Mark a recorded poker event with the reproduction it earned."""
    if event is None:
        return
    baby_id = getattr(baby, "fish_id", None)
    event["reproduction"] = {"parent_id": parent_id, "baby_id": baby_id}
    if baby_id is not None:
        event["message"] += f" Won the chance to reproduce - baby #{baby_id} born!"
