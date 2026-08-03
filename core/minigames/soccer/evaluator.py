"""Soccer minigame evaluation entrypoint and reward handling."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from core.minigames.soccer.match import SoccerMatch
from core.minigames.soccer.reconciliation import (
    SoccerSettlement,
    SourceIdentity,
    reconcile_match,
    resolve_source,
)
from core.minigames.soccer.rewards import (
    apply_shaped_soccer_rewards,
    apply_soccer_entry_fees,
    apply_soccer_repro_rewards,
    apply_soccer_rewards,
)
from core.minigames.soccer.seeds import derive_soccer_seed, stable_seed_from_parts
from core.minigames.soccer.selection import (
    SelectionStrategy,
    get_entity_energy,
    get_entity_id,
    select_soccer_participants,
)
from core.minigames.soccer.types import SoccerMatchSetup, SoccerMinigameOutcome


class _CreditRecorder:
    def __init__(self) -> None:
        self.amount = 0.0
        self.repro_credits = 0.0

    def add_repro_credits(self, amount: float) -> float:
        applied = max(0.0, float(amount))
        self.amount += applied
        self.repro_credits += applied
        return applied


class _SettlementParticipant:
    """Detached value object used to calculate rewards without live writes."""

    def __init__(self, participant: Any) -> None:
        self.fish_id = getattr(participant, "fish_id", None)
        self.tank_id = getattr(participant, "tank_id", None)
        self.tank_name = getattr(participant, "tank_name", None) or "Unknown Tank"
        self.offspring_count = int(getattr(participant, "offspring_count", 0) or 0)
        raw_energy = getattr(participant, "energy", None)
        raw_max_energy = getattr(participant, "max_energy", None)
        self._energy: float = float(raw_energy) if isinstance(raw_energy, (int, float)) else 0.0
        self.max_energy: float = (
            float(raw_max_energy) if isinstance(raw_max_energy, (int, float)) else 1000.0
        )
        component = getattr(participant, "reproduction_component", None) or getattr(
            participant, "_reproduction_component", None
        )
        repro_capable = bool(getattr(participant, "repro_credit_capable", False)) or hasattr(
            component, "add_repro_credits"
        )
        self.reproduction_component: _CreditRecorder | None = (
            _CreditRecorder() if repro_capable else None
        )

    def modify_energy(self, amount: float, *, source: str = "unknown") -> float:
        before = self._energy
        target = max(0.0, min(self.max_energy, before + float(amount)))
        self._energy = target
        return target - before

    @property
    def energy(self) -> float:
        return self._energy


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
    target_pursuit_module_enabled: bool | None = None,
    source_resolver: Any | None = None,
    reconciliation_store: Any | None = None,
) -> SoccerMatchSetup:
    """Create a soccer match from pre-selected participants."""
    participants = list(participants)
    if len(participants) < 2:
        raise ValueError("Not enough participants for soccer minigame")
    if len(participants) % 2 != 0:
        raise ValueError("Soccer participants must be an even count")

    if entry_fee_energy > 0:
        for entity in participants:
            if not hasattr(entity, "modify_energy"):
                raise ValueError("Participant cannot pay entry fee")
            if get_entity_energy(entity) <= entry_fee_energy:
                raise ValueError("Participant cannot pay entry fee")

    effective_seed = seed
    if effective_seed is None and match_id is not None:
        effective_seed = stable_seed_from_parts(match_id)

    if match_id is None:
        if effective_seed is not None:
            match_id = f"soccer_{effective_seed}_{match_counter}"
        else:
            match_id = str(uuid.uuid4())

    entry_fees = apply_soccer_entry_fees(participants, entry_fee_energy)

    match = SoccerMatch(
        match_id=match_id,
        entities=participants,
        duration_frames=duration_frames,
        code_source=code_source,
        view_mode=view_mode,
        seed=effective_seed,
        target_pursuit_module_enabled=target_pursuit_module_enabled,
    )

    return SoccerMatchSetup(
        match=match,
        seed=effective_seed,
        match_id=match_id,
        selected_count=len(participants),
        match_counter=match_counter,
        selection_seed=selection_seed,
        entry_fees=entry_fees,
        source_resolver=source_resolver,
        reconciliation_store=reconciliation_store,
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
    target_pursuit_module_enabled: bool | None = None,
    source_resolver: Any | None = None,
    reconciliation_store: Any | None = None,
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
        target_pursuit_module_enabled=target_pursuit_module_enabled,
        source_resolver=source_resolver,
        reconciliation_store=reconciliation_store,
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
    source_resolver: Any | None = None,
    reconciliation_store: Any | None = None,
) -> SoccerMinigameOutcome:
    """Apply rewards and return a compact outcome summary."""
    state = match.get_state()
    entry_fees = dict(entry_fees or {})

    # Per-fish scoring stats from the match's goal log (participant -> fish id)
    goals_by_fish: dict[int, int] = {}
    assists_by_fish: dict[int, int] = {}
    for goal in getattr(match, "goal_log", []):
        for key, counts in (("scorer_id", goals_by_fish), ("assist_id", assists_by_fish)):
            participant_id = goal.get(key)
            if not participant_id:
                continue
            entity = match.player_map.get(participant_id)
            if entity is None:
                continue
            fish_id = get_entity_id(entity)
            counts[fish_id] = counts.get(fish_id, 0) + 1

    # Resolve current sources only in orchestration. The match itself never
    # owns this resolver or any live fish references.
    source_by_participant: dict[str, Any] = {}
    if source_resolver is not None:
        for participant in match.roster_snapshot.participants:
            if participant.fish_id is None or participant.tank_id is None:
                continue
            identity = SourceIdentity(participant.fish_id, participant.tank_id)
            source_by_participant[participant.participant_id] = resolve_source(
                source_resolver, identity
            )

    # Calculate against detached settlement participants using full-time
    # source state when available. No source fish is mutated while calculating.
    settlement_map = {
        participant_id: _SettlementParticipant(source_by_participant.get(participant_id, entity))
        for participant_id, entity in match.player_map.items()
    }

    # Dispatch reward logic based on reward_mode
    if reward_mode.lower().strip() == "shaped_pot":
        rewards = apply_shaped_soccer_rewards(
            settlement_map,
            match.winner_team,
            match.telemetry,
            entry_fees=entry_fees,
            reward_multiplier=reward_multiplier,
            goals_by_fish=goals_by_fish,
            assists_by_fish=assists_by_fish,
        )
    else:
        rewards = apply_soccer_rewards(
            settlement_map,
            match.winner_team,
            reward_mode=reward_mode,
            entry_fees=entry_fees,
            reward_multiplier=reward_multiplier,
            goals_by_fish=goals_by_fish,
            assists_by_fish=assists_by_fish,
        )

    repro_credit_deltas = apply_soccer_repro_rewards(
        settlement_map,
        match.winner_team,
        reward_mode=repro_reward_mode,
        credit_award=repro_credit_award,
    )
    score = state.get("score", {})
    energy_deltas: dict[int, float] = {}
    for fish_id, fee in entry_fees.items():
        energy_deltas[fish_id] = energy_deltas.get(fish_id, 0.0) - fee
    for participant_id, delta in rewards.items():
        settlement_participant = settlement_map.get(participant_id)
        if settlement_participant is None:
            continue
        fish_id = get_entity_id(settlement_participant)
        energy_deltas[fish_id] = energy_deltas.get(fish_id, 0.0) + delta

    # The charged entry fee remains an accounting input and is already applied
    # at setup. It is intentionally excluded from post-match reconciliation.
    identity_by_participant: dict[str, SourceIdentity] = {
        participant.participant_id: SourceIdentity(participant.fish_id, participant.tank_id)
        for participant in match.roster_snapshot.participants
        if participant.fish_id is not None and participant.tank_id is not None
    }
    post_match_energy: dict[SourceIdentity, float] = {}
    for participant_id, delta in rewards.items():
        settlement_identity = identity_by_participant.get(participant_id)
        if settlement_identity is not None:
            post_match_energy[settlement_identity] = post_match_energy.get(
                settlement_identity, 0.0
            ) + float(delta)
    post_match_repro: dict[SourceIdentity, float] = {}
    for fish_id, delta in repro_credit_deltas.items():
        repro_identity: SourceIdentity | None = next(
            (value for value in identity_by_participant.values() if value.fish_id == fish_id), None
        )
        if repro_identity is not None:
            post_match_repro[repro_identity] = post_match_repro.get(repro_identity, 0.0) + float(
                delta
            )
    statistics = {
        identity: {
            "goals": goals_by_fish.get(identity.fish_id, 0),
            "assists": assists_by_fish.get(identity.fish_id, 0),
        }
        for identity in identity_by_participant.values()
    }
    settlement = SoccerSettlement.for_match(
        match.match_id,
        entry_fees={
            identity: float(entry_fees.get(identity.fish_id, 0.0))
            for identity in identity_by_participant.values()
            if identity.fish_id in entry_fees
        },
        energy_deltas=post_match_energy,
        repro_credit_deltas=post_match_repro,
        statistics=statistics,
        energy_source=(
            "soccer_shaped" if reward_mode.lower().strip() == "shaped_pot" else "soccer_win"
        ),
    )
    reconciliation_result = None
    if source_resolver is not None:
        reconciliation_result = reconcile_match(
            settlement,
            source_resolver,
            # A missing injected store uses reconciliation.py's process-level
            # idempotency store. Do not create a new store per retry.
            store=reconciliation_store,
        )

    # Reconciliation is authoritative for live-world effects. Entry fees were
    # already charged at setup and remain in the outcome separately.
    if reconciliation_result is not None:
        applied_by_participant = {
            participant_id: reconciliation_result.applied_energy_deltas.get(
                SourceIdentity(participant.fish_id, participant.tank_id), 0.0
            )
            for participant_id, participant in (
                (p.participant_id, p) for p in match.roster_snapshot.participants
            )
            if participant.fish_id is not None
        }
        rewards = {
            participant_id: applied_by_participant.get(participant_id, 0.0)
            for participant_id in rewards
            if applied_by_participant.get(participant_id, 0.0) != 0.0
        }
        energy_deltas = {fish_id: -float(entry_fees.get(fish_id, 0.0)) for fish_id in entry_fees}
        for identity, amount in reconciliation_result.applied_energy_deltas.items():
            energy_deltas[identity.fish_id] = energy_deltas.get(identity.fish_id, 0.0) + amount
        repro_credit_deltas = {
            identity.fish_id: amount
            for identity, amount in reconciliation_result.applied_repro_credit_deltas.items()
        }

    tank_names_by_fish: dict[int, str] = {}
    tank_ids_by_fish: dict[int, str] = {}
    offspring_count_by_fish: dict[int, int] = {}
    for participant_id, entity in match.player_map.items():
        fish_id = get_entity_id(entity)
        if fish_id is not None:
            source = source_by_participant.get(participant_id, entity)
            tank_names_by_fish[fish_id] = (
                getattr(source, "tank_name", None)
                or getattr(entity, "tank_name", None)
                or "Unknown Tank"
            )
            tank_ids_by_fish[fish_id] = (
                getattr(source, "tank_id", None) or getattr(entity, "tank_id", None) or "unknown"
            )
            offspring_count_by_fish[fish_id] = int(
                getattr(source, "offspring_count", None)
                or getattr(entity, "offspring_count", 0)
                or 0
            )

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
        telemetry=match.telemetry,
        goals_by_fish=goals_by_fish,
        assists_by_fish=assists_by_fish,
        tank_names_by_fish=tank_names_by_fish,
        tank_ids_by_fish=tank_ids_by_fish,
        offspring_count_by_fish=offspring_count_by_fish,
        reconciliation_id=settlement.reconciliation_id,
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
    source_resolver: Any | None = None,
    reconciliation_store: Any | None = None,
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
        source_resolver=source_resolver,
        reconciliation_store=reconciliation_store,
    )
    match = setup.match

    while not match.game_over:
        match.step(num_steps=5)
    return finalize_soccer_match(
        match,
        seed=setup.seed,
        source_resolver=source_resolver or getattr(setup, "source_resolver", None),
        reconciliation_store=reconciliation_store or getattr(setup, "reconciliation_store", None),
    )
