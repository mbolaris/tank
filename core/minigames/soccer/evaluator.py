"""Soccer minigame evaluation entrypoint and reward handling."""

from __future__ import annotations

import hashlib
import random
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from core.minigames.soccer.match import SoccerMatch


class SelectionStrategy(Enum):
    """How participants are selected for soccer matches."""

    TOP_ENERGY = "top_energy"  # Highest energy first (legacy)
    WEIGHTED_ENERGY = "weighted_energy"  # Roulette-wheel by energy
    STRATIFIED = "stratified"  # Diverse tiers (top/mid/low)
    RANDOM_ELIGIBLE = "random_eligible"  # Uniform random from eligible pool


@dataclass(frozen=True)
class SoccerMinigameOutcome:
    """Summary of a completed soccer minigame run."""

    match_id: str
    match_counter: int
    winner_team: str | None
    score_left: int
    score_right: int
    frames: int
    seed: int | None
    selection_seed: int | None
    message: str
    rewarded: dict[str, float]
    entry_fees: dict[int, float]
    energy_deltas: dict[int, float]
    repro_credit_deltas: dict[int, float]
    teams: dict[str, list[int]]
    skipped: bool = False
    skip_reason: str = ""


@dataclass(frozen=True)
class SoccerMatchSetup:
    """Created match plus deterministic metadata for logging."""

    match: SoccerMatch
    seed: int | None
    match_id: str
    selected_count: int
    match_counter: int
    selection_seed: int | None
    entry_fees: dict[int, float]


def _stable_seed_from_parts(*parts: Any) -> int:
    """Build a stable 32-bit seed from arbitrary parts."""
    seed_material = "|".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(seed_material).digest()[:4], "little") & 0xFFFFFFFF


def derive_soccer_seed(seed_base: int | None, match_counter: int, salt: str) -> int | None:
    """Derive deterministic seeds for soccer scheduling."""
    if seed_base is None:
        return None
    return _stable_seed_from_parts(seed_base, match_counter, salt)


def _get_entity_id(entity: Any) -> int:
    """Extract stable ID from an entity."""
    fish_id = getattr(entity, "fish_id", None)
    if fish_id is not None:
        return int(fish_id)
    return id(entity)


def _get_entity_energy(entity: Any) -> float:
    """Extract energy from an entity."""
    return float(getattr(entity, "energy", 0.0))


def _sort_key(entity: Any) -> tuple[float, str]:
    """Sort key for deterministic ordering: (-energy, id_str)."""
    return (-_get_entity_energy(entity), str(_get_entity_id(entity)))


def _weighted_sample(
    pool: list[Any],
    n: int,
    rng: random.Random,
    *,
    allow_repeat: bool = False,
) -> list[Any]:
    """Deterministic weighted sampling without replacement.

    Weight = energy + 1 (ensures nonzero weight for 0-energy fish).
    """
    if n <= 0 or not pool:
        return []

    if allow_repeat:
        weights = [_get_entity_energy(e) + 1.0 for e in pool]
        return list(rng.choices(pool, weights=weights, k=n))

    pool = list(pool)
    selected = []

    for _ in range(min(n, len(pool))):
        weights = [_get_entity_energy(e) + 1.0 for e in pool]
        total = sum(weights)
        if total <= 0:
            break

        r = rng.random() * total
        cumulative = 0.0
        chosen_idx = 0
        for i, w in enumerate(weights):
            cumulative += w
            if r <= cumulative:
                chosen_idx = i
                break

        selected.append(pool.pop(chosen_idx))

    return selected


def _select_top_energy(
    candidates: list[Any],
    num_players: int,
    *,
    allow_repeat: bool = False,
) -> list[Any]:
    """Original selection: highest energy first (deterministic)."""
    sorted_candidates = sorted(candidates, key=_sort_key)
    if allow_repeat and sorted_candidates:
        selected = []
        while len(selected) < num_players:
            for candidate in sorted_candidates:
                selected.append(candidate)
                if len(selected) >= num_players:
                    break
        return selected[:num_players]
    return sorted_candidates[:num_players]


def _select_weighted_energy(
    candidates: list[Any],
    num_players: int,
    rng: random.Random,
    *,
    allow_repeat: bool = False,
) -> list[Any]:
    """Roulette-wheel selection weighted by energy."""
    return _weighted_sample(candidates, num_players, rng, allow_repeat=allow_repeat)


def _select_stratified(
    candidates: list[Any],
    num_players: int,
    rng: random.Random,
    *,
    allow_repeat: bool = False,
) -> list[Any]:
    """Stratified selection: 50% top, 30% mid, 20% low energy tiers."""
    if not candidates:
        return []

    # Sort by energy descending for tier assignment
    sorted_pool = sorted(candidates, key=_sort_key)
    n = len(sorted_pool)

    # Split into thirds
    third = max(1, n // 3)
    top_tier = sorted_pool[:third]
    mid_tier = sorted_pool[third : 2 * third]
    low_tier = sorted_pool[2 * third :]

    # Allocate slots: 50% top, 30% mid, 20% low
    top_slots = max(1, int(num_players * 0.5))
    mid_slots = max(1, int(num_players * 0.3))
    low_slots = max(0, num_players - top_slots - mid_slots)

    selected = []
    selected.extend(_weighted_sample(top_tier, top_slots, rng, allow_repeat=allow_repeat))
    selected.extend(_weighted_sample(mid_tier, mid_slots, rng, allow_repeat=allow_repeat))
    selected.extend(_weighted_sample(low_tier, low_slots, rng, allow_repeat=allow_repeat))

    # Fill remaining slots from any tier if we came up short
    remaining = num_players - len(selected)
    if remaining > 0:
        used_ids = {_get_entity_id(e) for e in selected}
        leftover = [c for c in candidates if _get_entity_id(c) not in used_ids]
        selected.extend(_weighted_sample(leftover, remaining, rng, allow_repeat=allow_repeat))

    return selected[:num_players]


def _select_random_eligible(
    candidates: list[Any],
    num_players: int,
    rng: random.Random,
    *,
    allow_repeat: bool = False,
) -> list[Any]:
    """Uniform random selection from eligible pool."""
    if not candidates or num_players <= 0:
        return []
    if allow_repeat:
        return [rng.choice(candidates) for _ in range(num_players)]
    return rng.sample(candidates, num_players)


def select_soccer_participants(
    candidates: Sequence[Any],
    num_players: int,
    *,
    strategy: SelectionStrategy = SelectionStrategy.STRATIFIED,
    cooldown_ids: frozenset[int] = frozenset(),
    seed: int | None = None,
    allow_repeat_within_match: bool = False,
    entry_fee_energy: float = 0.0,
) -> list[Any]:
    """Select participants for a soccer match.

    Args:
        candidates: Pool of entities to select from.
        num_players: Number of players to select.
        strategy: Selection algorithm to use.
        cooldown_ids: Entity IDs to exclude (recently played).
        seed: RNG seed for deterministic selection.
        allow_repeat_within_match: Whether the same entity may appear multiple times.
        entry_fee_energy: Required energy to participate (0 disables fee filter).

    Returns:
        List of selected entities (even count, may be less than num_players).
    """
    if num_players <= 0 or not candidates:
        return []

    if num_players % 2 != 0:
        num_players -= 1
    if num_players < 2:
        return []

    # Filter by cooldown
    eligible = []
    for candidate in candidates:
        if _get_entity_id(candidate) in cooldown_ids:
            continue
        if entry_fee_energy > 0:
            if not hasattr(candidate, "modify_energy"):
                continue
            if _get_entity_energy(candidate) <= entry_fee_energy:
                continue
        eligible.append(candidate)

    if len(eligible) < 2:
        return []
    if not allow_repeat_within_match and len(eligible) < num_players:
        return []

    ordered = sorted(eligible, key=_sort_key)

    # Create seeded RNG for deterministic selection
    rng = random.Random(seed)

    # Select based on strategy
    if strategy == SelectionStrategy.TOP_ENERGY:
        selected = _select_top_energy(ordered, num_players, allow_repeat=allow_repeat_within_match)
    elif strategy == SelectionStrategy.WEIGHTED_ENERGY:
        selected = _select_weighted_energy(
            ordered, num_players, rng, allow_repeat=allow_repeat_within_match
        )
    elif strategy == SelectionStrategy.STRATIFIED:
        selected = _select_stratified(
            ordered, num_players, rng, allow_repeat=allow_repeat_within_match
        )
    elif strategy == SelectionStrategy.RANDOM_ELIGIBLE:
        selected = _select_random_eligible(
            ordered, num_players, rng, allow_repeat=allow_repeat_within_match
        )
    else:
        # Default fallback
        selected = _select_top_energy(ordered, num_players, allow_repeat=allow_repeat_within_match)

    if len(selected) != num_players:
        return []

    return selected


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
        fees[_get_entity_id(entity)] = -applied
    return fees


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
        for entity in participants:
            if not hasattr(entity, "modify_energy"):
                raise ValueError("Participant cannot pay entry fee")
            if _get_entity_energy(entity) <= entry_fee_energy:
                raise ValueError("Participant cannot pay entry fee")

    effective_seed = seed
    if effective_seed is None and match_id is not None:
        effective_seed = _stable_seed_from_parts(match_id)

    if match_id is None:
        if effective_seed is not None:
            match_id = f"soccer_{effective_seed}_{match_counter}"
        else:
            match_id = str(uuid.uuid4())

    entry_fees = apply_soccer_entry_fees(participants, entry_fee_energy)

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
        fish_id = _get_entity_id(entity)
        deltas[fish_id] = deltas.get(fish_id, 0.0) + applied
    return deltas


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
        fish_id = _get_entity_id(entity)
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
