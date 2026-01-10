"""Energy and reproduction rewards for soccer outcomes."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from core.minigames.soccer.selection import get_entity_id


def _apply_energy_delta(entity: Any, amount: float, source: str) -> float:
    if not hasattr(entity, "modify_energy"):
        return 0.0
    return float(entity.modify_energy(amount, source=source))


def apply_soccer_entry_fees(
    participants: Sequence[Any],
    entry_fee_energy: float,
    *,
    fee_source: str = "soccer_entry_fee",
) -> dict[int, float]:
    """Apply entry fees to participants via modify_energy()."""
    if entry_fee_energy <= 0:
        return {}

    fees: dict[int, float] = {}
    for entity in participants:
        applied = _apply_energy_delta(entity, -entry_fee_energy, fee_source)
        if applied == 0:
            continue
        fees[get_entity_id(entity)] = -applied
    return fees


def apply_soccer_rewards(
    player_map: Mapping[str, Any],
    winner_team: str | None,
    *,
    reward_mode: str = "pot_payout",
    entry_fees: Mapping[int, float] | None = None,
    reward_multiplier: float = 1.0,
    reward_source: str = "soccer_win",
    draw_refund_source: str = "soccer_draw_refund",
) -> dict[str, float]:
    """Apply energy rewards to the winning team via modify_energy()."""
    mode = reward_mode.lower().strip()
    entry_fees = entry_fees or {}

    rewards: dict[str, float] = {}
    if not winner_team:
        return rewards
    if winner_team == "draw":
        for participant_id, entity in player_map.items():
            fee = entry_fees.get(get_entity_id(entity), 0.0)
            if fee <= 0:
                continue
            applied = _apply_energy_delta(entity, fee, draw_refund_source)
            if applied != 0:
                rewards[participant_id] = applied
        return rewards
    winner_ids = [pid for pid in player_map if pid.startswith(winner_team)]
    if not winner_ids:
        return rewards

    if mode == "pot_payout":
        pot = sum(fee for fee in entry_fees.values() if fee > 0)
        pot *= reward_multiplier
        if pot <= 0:
            return rewards
        share = pot / len(winner_ids)
        for participant_id in winner_ids:
            entity = player_map[participant_id]
            applied = _apply_energy_delta(entity, share, reward_source)
            if applied != 0:
                rewards[participant_id] = applied
    elif mode == "refill_to_max":
        for participant_id in winner_ids:
            entity = player_map[participant_id]
            max_energy = getattr(entity, "max_energy", 1000.0)
            current_energy = getattr(entity, "energy", 0.0)
            delta = max_energy - current_energy
            if delta <= 0:
                continue
            applied = _apply_energy_delta(entity, delta, reward_source)
            if applied != 0:
                rewards[participant_id] = applied

    return rewards


def apply_soccer_repro_rewards(
    player_map: Mapping[str, Any],
    winner_team: str | None,
    *,
    reward_mode: str = "credits",
    credit_award: float = 0.0,
) -> dict[int, float]:
    """Apply reproduction credit rewards to the winning team."""
    if credit_award <= 0:
        return {}
    if not winner_team or winner_team == "draw":
        return {}
    if reward_mode.lower().strip() != "credits":
        return {}

    deltas: dict[int, float] = {}
    for participant_id, entity in player_map.items():
        if not participant_id.startswith(winner_team):
            continue
        component = getattr(entity, "_reproduction_component", None)
        if component is None or not hasattr(component, "add_repro_credits"):
            continue
        applied = component.add_repro_credits(credit_award)
        if applied == 0:
            continue
        fish_id = get_entity_id(entity)
        deltas[fish_id] = deltas.get(fish_id, 0.0) + applied
    return deltas
