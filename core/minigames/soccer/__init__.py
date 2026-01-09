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
    SoccerMatchSetup,
    SoccerMinigameOutcome,
    apply_soccer_rewards,
    create_soccer_match,
    finalize_soccer_match,
    run_soccer_minigame,
    select_soccer_participants,
)
from core.minigames.soccer.fake_server import FakeRCSSServer
from core.minigames.soccer.match import SoccerMatch
from core.minigames.soccer.match_runner import AgentResult, EpisodeResult, SoccerMatchRunner
from core.minigames.soccer.params import DEFAULT_RCSS_PARAMS, RCSSParams
from core.minigames.soccer.participant import (
    SoccerParticipant,
    create_participants_from_fish,
    fish_to_participant,
)

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
    "SoccerMatchSetup",
    "SoccerMinigameOutcome",
    "run_soccer_minigame",
    "create_soccer_match",
    "finalize_soccer_match",
    "apply_soccer_rewards",
    "select_soccer_participants",
    # Participants
    "SoccerParticipant",
    "fish_to_participant",
    "create_participants_from_fish",
]
