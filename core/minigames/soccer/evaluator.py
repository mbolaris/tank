"""Soccer minigame evaluation entrypoint and reward handling."""

from __future__ import annotations

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


@dataclass(frozen=True)
class SoccerMinigameOutcome:
    """Summary of a completed soccer minigame run."""

    match_id: str
    winner_team: str | None
    score_left: int
    score_right: int
    frames: int
    seed: int | None
    message: str
    rewarded: dict[str, float]
    teams: dict[str, list[int]]


@dataclass(frozen=True)
class SoccerMatchSetup:
    """Created match plus deterministic metadata for logging."""

    match: SoccerMatch
    seed: int | None
    match_id: str
    selected_count: int


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
) -> list[Any]:
    """Deterministic weighted sampling without replacement.

    Weight = energy + 1 (ensures nonzero weight for 0-energy fish).
    """
    if n <= 0 or not pool:
        return []

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
) -> list[Any]:
    """Original selection: highest energy first (deterministic)."""
    sorted_candidates = sorted(candidates, key=_sort_key)
    return sorted_candidates[:num_players]


def _select_weighted_energy(
    candidates: list[Any],
    num_players: int,
    rng: random.Random,
) -> list[Any]:
    """Roulette-wheel selection weighted by energy."""
    return _weighted_sample(candidates, num_players, rng)


def _select_stratified(
    candidates: list[Any],
    num_players: int,
    rng: random.Random,
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
    selected.extend(_weighted_sample(top_tier, top_slots, rng))
    selected.extend(_weighted_sample(mid_tier, mid_slots, rng))
    selected.extend(_weighted_sample(low_tier, low_slots, rng))

    # Fill remaining slots from any tier if we came up short
    remaining = num_players - len(selected)
    if remaining > 0:
        used_ids = {_get_entity_id(e) for e in selected}
        leftover = [c for c in candidates if _get_entity_id(c) not in used_ids]
        selected.extend(_weighted_sample(leftover, remaining, rng))

    return selected[:num_players]


def select_soccer_participants(
    candidates: Sequence[Any],
    num_players: int,
    *,
    strategy: SelectionStrategy = SelectionStrategy.STRATIFIED,
    cooldown_ids: frozenset[int] = frozenset(),
    seed: int | None = None,
) -> list[Any]:
    """Select participants for a soccer match.

    Args:
        candidates: Pool of entities to select from.
        num_players: Number of players to select.
        strategy: Selection algorithm to use.
        cooldown_ids: Entity IDs to exclude (recently played).
        seed: RNG seed for deterministic selection.

    Returns:
        List of selected entities (even count, may be less than num_players).
    """
    if num_players <= 0 or not candidates:
        return []

    # Filter by cooldown
    eligible = [c for c in candidates if _get_entity_id(c) not in cooldown_ids]
    if len(eligible) < 2:
        return []

    # Create seeded RNG for deterministic selection
    rng = random.Random(seed)

    # Select based on strategy
    if strategy == SelectionStrategy.TOP_ENERGY:
        selected = _select_top_energy(eligible, num_players)
    elif strategy == SelectionStrategy.WEIGHTED_ENERGY:
        selected = _select_weighted_energy(eligible, num_players, rng)
    elif strategy == SelectionStrategy.STRATIFIED:
        selected = _select_stratified(eligible, num_players, rng)
    else:
        # Default fallback
        selected = _select_top_energy(eligible, num_players)

    # Ensure even count for team balance
    if len(selected) % 2 != 0:
        selected = selected[:-1]

    return selected


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
) -> SoccerMatchSetup:
    """Create a soccer match with deterministic participant selection and seed."""
    selected = select_soccer_participants(candidates, num_players)
    if len(selected) < 2:
        raise ValueError("Not enough participants for soccer minigame")

    effective_seed = seed
    if effective_seed is None and seed_base is not None:
        effective_seed = (int(seed_base) + int(match_counter)) & 0xFFFFFFFF

    if match_id is None:
        if effective_seed is not None:
            match_id = f"soccer_{effective_seed}_{match_counter}"
        else:
            match_id = str(uuid.uuid4())

    match = SoccerMatch(
        match_id=match_id,
        fish_players=selected,
        duration_frames=duration_frames,
        code_source=code_source,
        view_mode=view_mode,
        seed=effective_seed,
    )

    return SoccerMatchSetup(
        match=match,
        seed=effective_seed,
        match_id=match_id,
        selected_count=len(selected),
    )


def apply_soccer_rewards(
    player_map: Mapping[str, Any],
    winner_team: str | None,
    *,
    reward_source: str = "soccer_win",
) -> dict[str, float]:
    """Apply energy rewards to the winning team via modify_energy()."""
    if not winner_team or winner_team == "draw":
        return {}

    rewards: dict[str, float] = {}
    for participant_id, entity in player_map.items():
        if not participant_id.startswith(winner_team):
            continue

        max_energy = getattr(entity, "max_energy", 1000.0)
        current_energy = getattr(entity, "energy", 0.0)
        delta = max_energy - current_energy
        if delta <= 0:
            continue

        if hasattr(entity, "modify_energy"):
            applied = entity.modify_energy(delta, source=reward_source)
        else:
            entity.energy = max_energy
            applied = delta

        rewards[participant_id] = applied

    return rewards


def finalize_soccer_match(match: SoccerMatch, *, seed: int | None = None) -> SoccerMinigameOutcome:
    """Apply rewards and return a compact outcome summary."""
    state = match.get_state()
    rewards = apply_soccer_rewards(match.player_map, match.winner_team)
    score = state.get("score", {})

    return SoccerMinigameOutcome(
        match_id=match.match_id,
        winner_team=state.get("winner_team"),
        score_left=int(score.get("left", 0)),
        score_right=int(score.get("right", 0)),
        frames=int(state.get("frame", match.current_frame)),
        seed=seed,
        message=state.get("message", ""),
        rewarded=rewards,
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
