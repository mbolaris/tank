"""Soccer minigame evaluation entrypoint and reward handling."""

from __future__ import annotations

import uuid
from typing import Any, Mapping, Sequence

from core.minigames.soccer.match import SoccerMatch
from core.minigames.soccer.rewards import (
    apply_soccer_entry_fees,
    apply_soccer_repro_rewards,
    apply_soccer_rewards,
)
from core.minigames.soccer.seeds import derive_soccer_seed, stable_seed_from_parts
from core.minigames.soccer.selection import (
    SelectionStrategy,
    get_entity_id,
    select_soccer_participants,
)
from core.minigames.soccer.types import SoccerMatchSetup, SoccerMinigameOutcome


def create_soccer_match_from_participants(
    participants: Sequence[Any],
    *,
    duration_frames: int = 3000,
    code_source: Any | None = None,
    view_mode: str = "side",
    seed: int | None = None,
    match_id: str | None = None,
    match_counter: int = 0,
    selection_seed: int | None = None,
    entry_fee_energy: float = 0.0,
) -> SoccerMatchSetup:
    """Create a soccer match from pre-selected participants."""
    participants = list(participants)
    if len(participants) < 2:
        raise ValueError("Not enough participants for soccer minigame")
    if len(participants) % 2 != 0:
        raise ValueError("Soccer participants must be an even count")

    if entry_fee_energy > 0:
        # Validate eligibility before creating match object
        # Note: We don't charge here anymore, we charge via apply_soccer_entry_fees
        # But we need to ensure candidates are valid if they are expected to pay.
        # Actually, apply_soccer_entry_fees does the charging.
        # But the original code raised if they COULD NOT pay.
        # The new request is: "charge entry fees only to energy-backed entities... bots pay 0"
        # So we should valid that IF they are energy participants, they have enough.
        for entity in participants:
            _try_charge_entry_fee_dry_run(entity, entry_fee_energy)

    effective_seed = seed
    if effective_seed is None and match_id is not None:
        effective_seed = stable_seed_from_parts(match_id)

    if match_id is None:
        if effective_seed is not None:
            match_id = f"soccer_{effective_seed}_{match_counter}"
        else:
            match_id = str(uuid.uuid4())

    # Calculate fees (safe for bots)
    entry_fees = {}
    if entry_fee_energy > 0:
        for idx, p in enumerate(participants):
            fee = _try_charge_entry_fee(p, entry_fee_energy)
            if fee > 0:
                # Map fish_id to fee. Use safe ID extraction.
                fid = get_entity_id(p)
                entry_fees[fid] = fee

    match = SoccerMatch(
        match_id=match_id,
        fish_players=participants,
        duration_frames=duration_frames,
        code_source=code_source,
        view_mode=view_mode,
        seed=effective_seed,
    )

    return SoccerMatchSetup(
        match=match,
        seed=effective_seed,
        match_id=match_id,
        selected_count=len(participants),
        match_counter=match_counter,
        selection_seed=selection_seed,
        entry_fees=entry_fees,
    )


def create_soccer_match(
    candidates: Sequence[Any],
    *,
    num_players: int = 22,
    duration_frames: int = 3000,
    code_source: Any | None = None,
    view_mode: str = "side",
    seed: int | None = None,
    seed_base: int | None = None,
    match_counter: int = 0,
    match_id: str | None = None,
    strategy: SelectionStrategy = SelectionStrategy.STRATIFIED,
    cooldown_ids: frozenset[int] = frozenset(),
    selection_seed: int | None = None,
    allow_repeat_within_match: bool = False,
    entry_fee_energy: float = 0.0,
) -> SoccerMatchSetup:
    """Create a soccer match with deterministic participant selection and seed."""
    effective_selection_seed = selection_seed
    if effective_selection_seed is None and seed_base is not None:
        effective_selection_seed = derive_soccer_seed(seed_base, match_counter, "selection")

    selected = select_soccer_participants(
        candidates,
        num_players,
        strategy=strategy,
        cooldown_ids=cooldown_ids,
        seed=effective_selection_seed,
        allow_repeat_within_match=allow_repeat_within_match,
        entry_fee_energy=entry_fee_energy,
    )
    if len(selected) != num_players:
        raise ValueError("Not enough participants for soccer minigame")

    effective_seed = seed
    if effective_seed is None and seed_base is not None:
        effective_seed = derive_soccer_seed(seed_base, match_counter, "match")

    return create_soccer_match_from_participants(
        selected,
        duration_frames=duration_frames,
        code_source=code_source,
        view_mode=view_mode,
        seed=effective_seed,
        match_id=match_id,
        match_counter=match_counter,
        selection_seed=effective_selection_seed,
        entry_fee_energy=entry_fee_energy,
    )


def finalize_soccer_match(
    match: SoccerMatch,
    *,
    seed: int | None = None,
    match_counter: int = 0,
    selection_seed: int | None = None,
    entry_fees: Mapping[int, float] | None = None,
    reward_mode: str = "pot_payout",
    reward_multiplier: float = 1.0,
    repro_reward_mode: str = "credits",
    repro_credit_award: float = 0.0,
) -> SoccerMinigameOutcome:
    """Apply rewards and return a compact outcome summary."""
    state = match.get_state()
    entry_fees = dict(entry_fees or {})
    rewards = apply_soccer_rewards(
        match.player_map,
        match.winner_team,
        reward_mode=reward_mode,
        entry_fees=entry_fees,
        reward_multiplier=reward_multiplier,
    )
    repro_credit_deltas = apply_soccer_repro_rewards(
        match.player_map,
        match.winner_team,
        reward_mode=repro_reward_mode,
        credit_award=repro_credit_award,
    )
    score = state.get("score", {})
    energy_deltas: dict[int, float] = {}
    for fish_id, fee in entry_fees.items():
        energy_deltas[fish_id] = energy_deltas.get(fish_id, 0.0) - fee
    for participant_id, delta in rewards.items():
        entity = match.player_map.get(participant_id)
        if entity is None:
            continue
        fish_id = get_entity_id(entity)
        energy_deltas[fish_id] = energy_deltas.get(fish_id, 0.0) + delta

    return SoccerMinigameOutcome(
        match_id=match.match_id,
        match_counter=match_counter,
        winner_team=state.get("winner_team"),
        score_left=int(score.get("left", 0)),
        score_right=int(score.get("right", 0)),
        frames=int(state.get("frame", match.current_frame)),
        seed=seed,
        selection_seed=selection_seed,
        message=state.get("message", ""),
        rewarded=rewards,
        entry_fees=dict(entry_fees),
        energy_deltas=energy_deltas,
        repro_credit_deltas=repro_credit_deltas,
        last_goal=state.get("last_goal"),
        teams={
            "left": list(state.get("teams", {}).get("left", [])),
            "right": list(state.get("teams", {}).get("right", [])),
        },
    )


def run_soccer_minigame(
    candidates: Sequence[Any],
    *,
    num_players: int = 22,
    duration_frames: int = 3000,
    code_source: Any | None = None,
    seed: int | None = None,
    view_mode: str = "side",
    match_id: str | None = None,
) -> SoccerMinigameOutcome:
    """Recruit participants, run a deterministic match, and apply rewards."""
    setup = create_soccer_match(
        candidates,
        num_players=num_players,
        duration_frames=duration_frames,
        code_source=code_source,
        view_mode=view_mode,
        seed=seed,
        match_id=match_id,
    )
    match = setup.match

    while not match.game_over:
        match.step(num_steps=5)
    return finalize_soccer_match(match, seed=setup.seed)


def _try_charge_entry_fee(participant: Any, entry_fee_energy: float) -> float:
    """Returns fee charged (0 if not applicable). Never raises for non-energy participants."""
    if entry_fee_energy <= 0:
        return 0.0

    energy = getattr(participant, "energy", None)
    modify_energy = getattr(participant, "modify_energy", None)

    # Bots/algorithmic players: no energy ledger => free entry.
    if energy is None or not callable(modify_energy):
        return 0.0

    if float(energy) <= entry_fee_energy:
        # Not eligible (caller should skip / replace participant)
        raise ValueError("Participant cannot pay entry fee")

    modify_energy(-entry_fee_energy, source="soccer_entry_fee")
    return float(entry_fee_energy)


def _try_charge_entry_fee_dry_run(participant: Any, entry_fee_energy: float) -> None:
    """Raises ValueError if participant is eligible to pay but cannot."""
    if entry_fee_energy <= 0:
        return

    energy = getattr(participant, "energy", None)
    modify_energy = getattr(participant, "modify_energy", None)

    # Bots/algorithmic players: no energy ledger => free entry.
    if energy is None or not callable(modify_energy):
        return

    if float(energy) <= entry_fee_energy:
        raise ValueError("Participant cannot pay entry fee")
