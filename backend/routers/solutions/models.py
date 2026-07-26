"""Request models for the solutions API."""

from typing import Literal

from pydantic import BaseModel


class CaptureRequest(BaseModel):
    """Request to capture a solution from a tank."""

    name: str | None = None
    description: str | None = None
    author: str | None = None
    evaluate: bool = False

    # How to choose the fish to capture from the live tank.
    # - heuristic_elo: existing fast heuristic (default)
    # - tournament: evaluate a candidate pool head-to-head vs best submitted solutions
    selection_mode: Literal["heuristic_elo", "tournament"] = "heuristic_elo"

    # Tournament selection tuning (only used when selection_mode="tournament")
    candidate_pool_size: int = 12
    hands_per_matchup: int = 500
    opponent_limit: int = 8


class SubmitRequest(BaseModel):
    """Request to submit a solution to git."""

    solution_id: str
    commit_message: str | None = None
    push: bool = True
