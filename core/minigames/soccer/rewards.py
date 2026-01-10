"""Energy and reproduction rewards for soccer outcomes."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from core.minigames.soccer.selection import get_entity_id


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
        if not hasattr(entity, "modify_energy"):
            continue
        applied = entity.modify_energy(-entry_fee_energy, source=fee_source)
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
) -> dict[str, float]:
    """Apply energy rewards to the winning team via modify_energy()."""
    if not winner_team or winner_team == "draw":
        return {}

    mode = reward_mode.lower().strip()
    entry_fees = entry_fees or {}

    rewards: dict[str, float] = {}
    winner_ids = [pid for pid in player_map if pid.startswith(winner_team)]
    if not winner_ids:
        return rewards

    if mode == "pot_payout":
        pot = sum(entry_fees.values()) * reward_multiplier
        if pot <= 0:
            return rewards
        share = pot / len(winner_ids)
        for participant_id in winner_ids:
            entity = player_map[participant_id]
            if not hasattr(entity, "modify_energy"):
                continue
            applied = entity.modify_energy(share, source=reward_source)
            if applied != 0:
                rewards[participant_id] = applied
    elif mode == "refill_to_max":
        if sum(entry_fees.values()) <= 0:
            return rewards
        for participant_id in winner_ids:
            entity = player_map[participant_id]
            if not hasattr(entity, "modify_energy"):
                continue
            max_energy = getattr(entity, "max_energy", 1000.0)
            current_energy = getattr(entity, "energy", 0.0)
            delta = max_energy - current_energy
            if delta <= 0:
                continue
            applied = entity.modify_energy(delta, source=reward_source)
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
