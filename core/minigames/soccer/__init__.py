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
    create_soccer_match,
    create_soccer_match_from_participants,
    derive_soccer_seed,
    finalize_soccer_match,
    run_soccer_minigame,
    select_soccer_participants,
)
from core.minigames.soccer.fake_server import FakeRCSSServer
from core.minigames.soccer.field_profiles import (
    SoccerFieldGeometry,
    get_field_profile,
    rcss_standard_105x68,
    tank_small_sided,
)
from core.minigames.soccer.league_runtime import SoccerLeagueRuntime
from core.minigames.soccer.match import SoccerMatch
from core.minigames.soccer.match_runner import AgentResult, EpisodeResult, SoccerMatchRunner
from core.minigames.soccer.params import DEFAULT_RCSS_PARAMS, SOCCER_CANONICAL_PARAMS, RCSSParams
from core.minigames.soccer.participant import (
    SoccerParticipant,
    create_participants_from_fish,
    fish_to_participant,
)
from core.minigames.soccer.reconciliation import (
    InMemoryReconciliationStore,
    ReconciliationResult,
    SoccerSettlement,
    SourceIdentity,
    reconcile_match,
)
from core.minigames.soccer.rewards import apply_soccer_entry_fees, apply_soccer_rewards
from core.minigames.soccer.roster_snapshot import (
    RosterSnapshot,
    SoccerParticipantSnapshot,
    SoccerRosterSnapshot,
    snapshot_roster,
)
from core.minigames.soccer.scheduler import SoccerMinigameScheduler

__all__ = [
    # Engine
    "RCSSParams",
    "DEFAULT_RCSS_PARAMS",
    "SOCCER_CANONICAL_PARAMS",
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
    "SoccerFieldGeometry",
    "rcss_standard_105x68",
    "tank_small_sided",
    "get_field_profile",
    "SoccerParticipantSnapshot",
    "SoccerRosterSnapshot",
    "RosterSnapshot",
    "snapshot_roster",
    "SourceIdentity",
    "SoccerSettlement",
    "ReconciliationResult",
    "InMemoryReconciliationStore",
    "reconcile_match",
    "select_soccer_participants",
    "derive_soccer_seed",
    "SoccerMinigameScheduler",
    "SoccerLeagueRuntime",
    # Participants
    "SoccerParticipant",
    "fish_to_participant",
    "create_participants_from_fish",
]
