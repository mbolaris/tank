"""Energy and reproduction rewards for soccer outcomes.

Reward modes:
- pot_payout: Winners split the entry fee pot (default)
- refill_to_max: Winners get energy refilled to max
- shaped_pot: Winners split pot + shaped bonuses to ALL players from telemetry (for evolution)

The shaped_pot mode is dispatched via finalize_soccer_match() to apply_shaped_soccer_rewards().
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

from core.config.soccer import (
    SOCCER_SHAPED_PER_PLAYER_CAP,
    SOCCER_SHAPED_PROGRESS_WEIGHT,
    SOCCER_SHAPED_SHOT_WEIGHT,
    SOCCER_SHAPED_TEAM_BONUS_CAP,
    SOCCER_SHAPED_TOUCH_WEIGHT,
    SOCCER_GOAL_ENERGY_REWARD,
    SOCCER_ASSIST_ENERGY_REWARD,
    SOCCER_WIN_ENERGY_REWARD,
    SOCCER_MAX_REWARD_PER_MATCH,
)
from core.minigames.soccer.selection import get_entity_id

if TYPE_CHECKING:
    from core.minigames.soccer.types import SoccerTelemetry


def _apply_energy_delta(entity: Any, amount: float, source: str) -> float:
    if not hasattr(entity, "modify_energy"):
        return 0.0
    return float(entity.modify_energy(amount, source=source))


def calculate_soccer_individual_rewards(
    player_map: Mapping[str, Any],
    winner_team: str | None,
    goals_by_fish: Mapping[int, int],
    assists_by_fish: Mapping[int, int],
    *,
    goal_bonus: float = SOCCER_GOAL_ENERGY_REWARD,
    assist_bonus: float = SOCCER_ASSIST_ENERGY_REWARD,
    win_bonus: float = SOCCER_WIN_ENERGY_REWARD,
    max_total_reward: float = SOCCER_MAX_REWARD_PER_MATCH,
) -> dict[str, float]:
    """Calculate the individual and team soccer rewards for each participant.

    Returns:
        Dict mapping participant_id (str) to calculated energy reward (float).
    """
    rewards: dict[str, float] = {}

    for participant_id, entity in player_map.items():
        fish_id = get_entity_id(entity)
        if fish_id is None:
            continue

        # 1. Goal bonus
        goals = goals_by_fish.get(fish_id, 0)
        goal_reward = goals * goal_bonus

        # 2. Assist bonus
        assists = assists_by_fish.get(fish_id, 0)
        assist_reward = assists * assist_bonus

        # 3. Team win bonus
        is_winner = winner_team and winner_team != "draw" and participant_id.startswith(winner_team)
        team_reward = win_bonus if is_winner else 0.0

        # 4. Total soccer reward capped
        total_reward = min(goal_reward + assist_reward + team_reward, max_total_reward)

        if total_reward > 0:
            rewards[participant_id] = total_reward

    return rewards


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
    goals_by_fish: Mapping[int, int] | None = None,
    assists_by_fish: Mapping[int, int] | None = None,
) -> dict[str, float]:
    """Apply energy rewards to the winning team and individuals via modify_energy()."""
    mode = reward_mode.lower().strip()
    entry_fees = entry_fees or {}
    goals_by_fish = goals_by_fish or {}
    assists_by_fish = assists_by_fish or {}

    rewards: dict[str, float] = {}
    if not winner_team:
        return rewards

    # First handle refund on draw
    if winner_team == "draw":
        for participant_id, entity in player_map.items():
            fee = entry_fees.get(get_entity_id(entity), 0.0)
            if fee <= 0:
                continue
            applied = _apply_energy_delta(entity, fee, draw_refund_source)
            if applied != 0:
                rewards[participant_id] = applied
        return rewards

    if mode == "pot_payout":
        winner_ids = [pid for pid in player_map if pid.startswith(winner_team)]
        if not winner_ids:
            return rewards
        pot = sum(fee for fee in entry_fees.values() if fee > 0.0)
        pot *= reward_multiplier
        if pot <= 0:
            return rewards
        share = pot / len(winner_ids)
        for participant_id in winner_ids:
            entity = player_map[participant_id]
            applied = _apply_energy_delta(entity, share, reward_source)
            if applied != 0:
                rewards[participant_id] = rewards.get(participant_id, 0.0) + applied

    elif mode == "refill_to_max":
        # Keep refill_to_max behavior but also apply goal/assist bonuses
        winner_ids = (
            [pid for pid in player_map if pid.startswith(winner_team)]
            if winner_team != "draw"
            else []
        )
        for participant_id in winner_ids:
            entity = player_map[participant_id]
            max_energy = getattr(entity, "max_energy", 1000.0)
            current_energy = getattr(entity, "energy", 0.0)
            delta = max_energy - current_energy
            if delta <= 0:
                continue
            applied = _apply_energy_delta(entity, delta, reward_source)
            if applied != 0:
                rewards[participant_id] = rewards.get(participant_id, 0.0) + applied

        # Also apply individual goal/assist rewards for refill_to_max
        indiv_rewards = calculate_soccer_individual_rewards(
            player_map,
            winner_team,
            goals_by_fish,
            assists_by_fish,
        )
        for participant_id, amount in indiv_rewards.items():
            fish_id = get_entity_id(player_map[participant_id])
            if fish_id is None:
                continue
            g_rew = goals_by_fish.get(fish_id, 0) * SOCCER_GOAL_ENERGY_REWARD
            a_rew = assists_by_fish.get(fish_id, 0) * SOCCER_ASSIST_ENERGY_REWARD
            goal_assist_amount = min(g_rew + a_rew, SOCCER_MAX_REWARD_PER_MATCH)
            if goal_assist_amount <= 0:
                continue
            entity = player_map[participant_id]
            applied = _apply_energy_delta(
                entity, goal_assist_amount * reward_multiplier, f"{reward_source}_individual"
            )
            if applied != 0:
                rewards[participant_id] = rewards.get(participant_id, 0.0) + applied

    return rewards


def calculate_shaped_bonuses(
    telemetry: SoccerTelemetry,
    *,
    progress_weight: float = SOCCER_SHAPED_PROGRESS_WEIGHT,
    touch_weight: float = SOCCER_SHAPED_TOUCH_WEIGHT,
    shot_weight: float = SOCCER_SHAPED_SHOT_WEIGHT,
    max_bonus_per_player: float = SOCCER_SHAPED_PER_PLAYER_CAP,
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
        team_players = [pid for pid, pt in telemetry.players.items() if pt.team == team]
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
    telemetry: SoccerTelemetry,
    *,
    entry_fees: Mapping[int, float] | None = None,
    reward_multiplier: float = 1.0,
    shaped_bonus_cap: float = SOCCER_SHAPED_TEAM_BONUS_CAP,
    progress_weight: float = SOCCER_SHAPED_PROGRESS_WEIGHT,
    touch_weight: float = SOCCER_SHAPED_TOUCH_WEIGHT,
    shot_weight: float = SOCCER_SHAPED_SHOT_WEIGHT,
    reward_source: str = "soccer_shaped",
    draw_refund_source: str = "soccer_draw_refund",
    goals_by_fish: Mapping[int, int] | None = None,
    assists_by_fish: Mapping[int, int] | None = None,
) -> dict[str, float]:
    """Apply shaped rewards: individual rewards (goals/assists/win) + shaped bonuses to all.

    This reward mode combines:
    1. Individual and team rewards based on goals, assists, and wins (replacing the simple pot payout)
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
        goals_by_fish: Goals scored by each fish ID
        assists_by_fish: Assists scored by each fish ID

    Returns:
        Dict mapping participant_id to total reward (pot share + shaped bonus)
    """
    entry_fees = entry_fees or {}
    goals_by_fish = goals_by_fish or {}
    assists_by_fish = assists_by_fish or {}
    rewards: dict[str, float] = {}

    # Step 1: Handle draw refunds
    if winner_team == "draw":
        for participant_id, entity in player_map.items():
            fee = entry_fees.get(get_entity_id(entity), 0.0)
            if fee > 0:
                applied = _apply_energy_delta(entity, fee, draw_refund_source)
                if applied != 0:
                    rewards[participant_id] = applied

    # Step 2: Individual and team rewards (even if it was a draw, goals/assists are rewarded)
    indiv_rewards = calculate_soccer_individual_rewards(
        player_map,
        winner_team,
        goals_by_fish,
        assists_by_fish,
    )
    for participant_id, amount in indiv_rewards.items():
        entity = player_map[participant_id]
        amount_scaled = amount * reward_multiplier
        applied = _apply_energy_delta(entity, amount_scaled, reward_source)
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
        component = getattr(entity, "reproduction_component", None)
        if component is None or not hasattr(component, "add_repro_credits"):
            continue
        applied = component.add_repro_credits(credit_award)
        if applied == 0:
            continue
        fish_id = get_entity_id(entity)
        deltas[fish_id] = deltas.get(fish_id, 0.0) + applied
    return deltas
