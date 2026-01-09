"""Soccer minigame evaluation entrypoint and reward handling."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.minigames.soccer.match import SoccerMatch


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


def select_soccer_participants(candidates: Sequence[Any], num_players: int) -> list[Any]:
    """Select participants for a soccer match based on energy."""
    if num_players <= 0 or not candidates:
        return []

    def sort_key(entity: Any) -> tuple[float, str]:
        energy = float(getattr(entity, "energy", 0.0))
        stable_id = getattr(entity, "fish_id", None)
        if stable_id is None:
            stable_id = id(entity)
        return (-energy, str(stable_id))

    selected = sorted(candidates, key=sort_key)[:num_players]
    if len(selected) % 2 != 0:
        selected = selected[:-1]
    return selected


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
    selected = select_soccer_participants(candidates, num_players)
    if len(selected) < 2:
        raise ValueError("Not enough participants for soccer minigame")

    if match_id is None:
        match_id = f"soccer_{seed}" if seed is not None else str(uuid.uuid4())

    match = SoccerMatch(
        match_id=match_id,
        fish_players=selected,
        duration_frames=duration_frames,
        code_source=code_source,
        view_mode=view_mode,
        seed=seed,
    )

    while not match.game_over:
        match.step(num_steps=5)

    state = match.get_state()
    rewards = apply_soccer_rewards(match.player_map, match.winner_team)
    score = state.get("score", {})

    return SoccerMinigameOutcome(
        match_id=match_id,
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
