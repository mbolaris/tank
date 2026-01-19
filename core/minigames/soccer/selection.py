"""Deterministic participant selection for soccer matches."""

from __future__ import annotations

import random
from enum import Enum
from typing import Any, Sequence


class SelectionStrategy(Enum):
    """How participants are selected for soccer matches."""

    TOP_ENERGY = "top_energy"  # Highest energy first (legacy)
    WEIGHTED_ENERGY = "weighted_energy"  # Roulette-wheel by energy
    STRATIFIED = "stratified"  # Diverse tiers (top/mid/low)
    RANDOM_ELIGIBLE = "random_eligible"  # Uniform random from eligible pool


def get_entity_id(entity: Any) -> int:
    """Extract stable ID from an entity."""
    fish_id = getattr(entity, "fish_id", None)
    if fish_id is not None:
        return int(fish_id)
    return id(entity)


def get_entity_energy(entity: Any) -> float:
    """Extract energy from an entity."""
    return float(getattr(entity, "energy", 0.0))


def _sort_key(entity: Any) -> tuple[float, str]:
    """Sort key for deterministic ordering: (-energy, id_str)."""
    return (-get_entity_energy(entity), str(get_entity_id(entity)))


def _weighted_sample(
    pool: list[Any],
    n: int,
    rng: random.Random,
    *,
    allow_repeat: bool = False,
) -> list[Any]:
    """Deterministic weighted sampling without replacement."""
    if n <= 0 or not pool:
        return []

    if allow_repeat:
        weights = [get_entity_energy(e) + 1.0 for e in pool]
        return list(rng.choices(pool, weights=weights, k=n))

    pool = list(pool)
    selected: list[Any] = []

    for _ in range(min(n, len(pool))):
        weights = [get_entity_energy(e) + 1.0 for e in pool]
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
        selected: list[Any] = []
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

    sorted_pool = sorted(candidates, key=_sort_key)
    n = len(sorted_pool)

    third = max(1, n // 3)
    top_tier = sorted_pool[:third]
    mid_tier = sorted_pool[third : 2 * third]
    low_tier = sorted_pool[2 * third :]

    top_slots = max(1, int(num_players * 0.5))
    mid_slots = max(1, int(num_players * 0.3))
    low_slots = max(0, num_players - top_slots - mid_slots)

    selected: list[Any] = []
    selected.extend(_weighted_sample(top_tier, top_slots, rng, allow_repeat=allow_repeat))
    selected.extend(_weighted_sample(mid_tier, mid_slots, rng, allow_repeat=allow_repeat))
    selected.extend(_weighted_sample(low_tier, low_slots, rng, allow_repeat=allow_repeat))

    remaining = num_players - len(selected)
    if remaining > 0:
        used_ids = {get_entity_id(e) for e in selected}
        leftover = [c for c in candidates if get_entity_id(c) not in used_ids]
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
    """Select participants for a soccer match."""
    if num_players <= 0 or not candidates:
        return []

    if num_players % 2 != 0:
        num_players -= 1
    if num_players < 2:
        return []

    eligible = []
    for candidate in candidates:
        if get_entity_id(candidate) in cooldown_ids:
            continue
        if entry_fee_energy > 0:
            if not hasattr(candidate, "modify_energy"):
                continue
            if get_entity_energy(candidate) <= entry_fee_energy:
                continue
        eligible.append(candidate)

    if len(eligible) < 2:
        return []
    if not allow_repeat_within_match and len(eligible) < num_players:
        return []

    ordered = sorted(eligible, key=_sort_key)
    rng = random.Random(seed)

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
        selected = _select_top_energy(ordered, num_players, allow_repeat=allow_repeat_within_match)

    if len(selected) != num_players:
        return []

    return selected
