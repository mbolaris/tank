"""Energy and reproduction rewards for soccer outcomes.

Reward modes:
- pot_payout: Winners split the entry fee pot (default)
- refill_to_max: Winners get energy refilled to max
- shaped_pot: Winners split pot + shaped bonuses from telemetry (for evolution)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping, Sequence

from core.minigames.soccer.selection import get_entity_id

if TYPE_CHECKING:
    from core.minigames.soccer.types import SoccerTelemetry


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
    # Note: shaped_pot mode is handled by apply_shaped_soccer_rewards()

    return rewards


def calculate_shaped_bonuses(
    telemetry: "SoccerTelemetry",
    *,
    progress_weight: float = 0.5,
    touch_weight: float = 0.2,
    shot_weight: float = 1.0,
    max_bonus_per_player: float = 10.0,
) -> dict[str, float]:
    """Calculate shaped bonuses from telemetry for evolution fitness.

    This provides incremental learning signals beyond sparse goal rewards.
    Bonuses are given to ALL players based on their contributions, not just winners.

    Args:
        telemetry: Match telemetry with per-player and per-team stats
        progress_weight: Energy per meter of ball progress toward goal
        touch_weight: Energy per ball touch
        shot_weight: Energy per shot on target
        max_bonus_per_player: Maximum bonus any single player can receive

    Returns:
        Dict mapping participant_id to bonus amount (always positive or zero)
    """
    bonuses: dict[str, float] = {}

    for player_id, player_tel in telemetry.players.items():
        team = player_tel.team
        team_tel = telemetry.teams.get(team)
        if not team_tel:
            continue

        bonus = 0.0

        # Touch bonus: reward ball control
        bonus += player_tel.touches * touch_weight

        # Ball progress bonus: share team's progress among team players
        team_players = [
            pid for pid, pt in telemetry.players.items() if pt.team == team
        ]
        if team_players and team_tel.ball_progress > 0:
            progress_share = team_tel.ball_progress / len(team_players)
            bonus += progress_share * progress_weight

        # Shot bonus: reward shots on target (team-level, shared)
        if team_players and team_tel.shots_on_target > 0:
            shot_share = team_tel.shots_on_target / len(team_players)
            bonus += shot_share * shot_weight

        # Clamp to max
        bonus = min(bonus, max_bonus_per_player)

        if bonus > 0:
            bonuses[player_id] = bonus

    return bonuses


def apply_shaped_soccer_rewards(
    player_map: Mapping[str, Any],
    winner_team: str | None,
    telemetry: "SoccerTelemetry",
    *,
    entry_fees: Mapping[int, float] | None = None,
    reward_multiplier: float = 1.0,
    shaped_bonus_cap: float = 20.0,
    progress_weight: float = 0.5,
    touch_weight: float = 0.2,
    shot_weight: float = 1.0,
    reward_source: str = "soccer_shaped",
    draw_refund_source: str = "soccer_draw_refund",
) -> dict[str, float]:
    """Apply shaped rewards: pot payout to winners + shaped bonuses to all.

    This reward mode combines:
    1. Standard pot payout to winning team (like pot_payout mode)
    2. Shaped bonuses to ALL players based on telemetry (for learning signal)

    The shaped bonuses are bounded to prevent energy economy explosion.

    Args:
        player_map: Mapping of participant_id to entity
        winner_team: "left", "right", "draw", or None
        telemetry: Match telemetry for shaped bonus calculation
        entry_fees: Entry fees paid by participants
        reward_multiplier: Multiplier for pot payout
        shaped_bonus_cap: Maximum total shaped bonus per team
        progress_weight: Weight for ball progress bonus
        touch_weight: Weight for touch bonus
        shot_weight: Weight for shot on target bonus
        reward_source: Source tag for energy ledger
        draw_refund_source: Source tag for draw refunds

    Returns:
        Dict mapping participant_id to total reward (pot share + shaped bonus)
    """
    entry_fees = entry_fees or {}
    rewards: dict[str, float] = {}

    # Step 1: Handle draw refunds (no pot payout, but still give shaped bonuses)
    if winner_team == "draw":
        for participant_id, entity in player_map.items():
            fee = entry_fees.get(get_entity_id(entity), 0.0)
            if fee > 0:
                applied = _apply_energy_delta(entity, fee, draw_refund_source)
                if applied != 0:
                    rewards[participant_id] = applied

    # Step 2: Pot payout to winners (if not draw)
    elif winner_team:
        winner_ids = [pid for pid in player_map if pid.startswith(winner_team)]
        if winner_ids:
            pot = sum(fee for fee in entry_fees.values() if fee > 0)
            pot *= reward_multiplier
            if pot > 0:
                share = pot / len(winner_ids)
                for participant_id in winner_ids:
                    entity = player_map[participant_id]
                    applied = _apply_energy_delta(entity, share, reward_source)
                    if applied != 0:
                        rewards[participant_id] = rewards.get(participant_id, 0.0) + applied

    # Step 3: Shaped bonuses to ALL players
    shaped = calculate_shaped_bonuses(
        telemetry,
        progress_weight=progress_weight,
        touch_weight=touch_weight,
        shot_weight=shot_weight,
        max_bonus_per_player=shaped_bonus_cap / max(1, len(player_map) // 2),
    )

    for participant_id, bonus in shaped.items():
        if participant_id not in player_map:
            continue
        entity = player_map[participant_id]
        applied = _apply_energy_delta(entity, bonus, f"{reward_source}_shaped")
        if applied != 0:
            rewards[participant_id] = rewards.get(participant_id, 0.0) + applied

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
