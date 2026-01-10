"""Soccer Minigame (RCSS-Lite).

This package provides an RCSS-compatible soccer minigame engine for
training policies that can transfer to the real RoboCup Soccer Simulator.

Components:
- RCSSLiteEngine: Core physics engine with RCSS-compatible stepping
- SoccerMatch: Interactive match manager for frontend integration
- SoccerMatchRunner: Training runner for evolution experiments
- SoccerParticipant: Entity-agnostic participant protocol
"""

from core.minigames.soccer.engine import RCSSCommand, RCSSLiteEngine, RCSSVector
from core.minigames.soccer.evaluator import (
    SelectionStrategy,
    SoccerMatchSetup,
    SoccerMinigameOutcome,
    apply_soccer_entry_fees,
    apply_soccer_rewards,
    create_soccer_match,
    create_soccer_match_from_participants,
    derive_soccer_seed,
    finalize_soccer_match,
    run_soccer_minigame,
    select_soccer_participants,
)
from core.minigames.soccer.fake_server import FakeRCSSServer
from core.minigames.soccer.league_runtime import SoccerLeagueRuntime
from core.minigames.soccer.match import SoccerMatch
from core.minigames.soccer.match_runner import AgentResult, EpisodeResult, SoccerMatchRunner
from core.minigames.soccer.params import DEFAULT_RCSS_PARAMS, RCSSParams
from core.minigames.soccer.participant import (
    SoccerParticipant,
    create_participants_from_fish,
    fish_to_participant,
)
from core.minigames.soccer.scheduler import SoccerMinigameScheduler

__all__ = [
    # Engine
    "RCSSParams",
    "DEFAULT_RCSS_PARAMS",
    "RCSSLiteEngine",
    "RCSSCommand",
    "RCSSVector",
    "FakeRCSSServer",
    # Match
    "SoccerMatch",
    "SoccerMatchRunner",
    "AgentResult",
    "EpisodeResult",
    # Evaluation
    "SelectionStrategy",
    "SoccerMatchSetup",
    "SoccerMinigameOutcome",
    "run_soccer_minigame",
    "create_soccer_match",
    "create_soccer_match_from_participants",
    "finalize_soccer_match",
    "apply_soccer_entry_fees",
    "apply_soccer_rewards",
    "select_soccer_participants",
    "derive_soccer_seed",
    "SoccerMinigameScheduler",
    "SoccerLeagueRuntime",
    # Participants
    "SoccerParticipant",
    "fish_to_participant",
    "create_participants_from_fish",
]
