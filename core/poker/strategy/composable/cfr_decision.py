"""Decision-time CFR regret matching for composable poker strategies."""

from __future__ import annotations

import random
from typing import Protocol

from core.poker.betting.actions import BettingAction

# Decision-time regret needs a higher bar than inheritance: low-sample regret
# quickly overfits single hands and perturbs ecosystem benchmark trajectories.
CFR_DECISION_MIN_VISITS = 50


class CfrDecisionStrategy(Protocol):
    """Composable strategy surface needed for decision-time CFR lookup."""

    parameters: dict[str, float]
    visit_count: dict[str, int]

    def get_info_set(
        self,
        hand_strength: float,
        pot_ratio: float,
        position_on_button: bool,
        street: int = 0,
    ) -> str: ...

    def sample_cfr_action(self, info_set: str, rng: random.Random | None = None) -> str | None: ...


def decide_from_cfr_regret(
    strategy: CfrDecisionStrategy,
    *,
    hand_strength: float,
    call_amount: float,
    pot: float,
    player_energy: float,
    position_on_button: bool,
    rng: random.Random,
) -> tuple[BettingAction, float] | None:
    """Return a learned CFR decision, or None when this state has no positive regret."""
    pot_ratio = pot / max(1.0, player_energy)
    info_set = strategy.get_info_set(hand_strength, pot_ratio, position_on_button, street=0)
    if strategy.visit_count.get(info_set, 0) < CFR_DECISION_MIN_VISITS:
        return None

    cfr_action = strategy.sample_cfr_action(info_set, rng)
    if cfr_action is None:
        return None

    if cfr_action == "fold":
        return _fold_or_check(call_amount)
    if cfr_action == "call":
        if call_amount <= 0:
            return (BettingAction.CHECK, 0.0)
        return (BettingAction.CALL, min(call_amount, player_energy))
    if cfr_action in {"raise_small", "raise_big"}:
        return _raise_decision(strategy, cfr_action, call_amount, pot, player_energy)

    return None


def _fold_or_check(call_amount: float) -> tuple[BettingAction, float]:
    if call_amount > 0:
        return (BettingAction.FOLD, 0.0)
    return (BettingAction.CHECK, 0.0)


def _raise_decision(
    strategy: CfrDecisionStrategy,
    cfr_action: str,
    call_amount: float,
    pot: float,
    player_energy: float,
) -> tuple[BettingAction, float]:
    if player_energy <= 0:
        return _fold_or_check(call_amount)

    pot_fraction = 0.33 if cfr_action == "raise_small" else 0.75
    call_multiplier = 1.5 if cfr_action == "raise_small" else 2.5
    target = max(pot * pot_fraction, call_amount * call_multiplier, 10.0)

    risk_tolerance = strategy.parameters.get("risk_tolerance", 0.35)
    if cfr_action == "raise_big":
        risk_tolerance = max(risk_tolerance, 0.45)
    target = min(target, player_energy * risk_tolerance)

    if target <= call_amount:
        if call_amount > 0:
            return (BettingAction.CALL, min(call_amount, player_energy))
        return (BettingAction.CHECK, 0.0)

    return (BettingAction.RAISE, min(target, player_energy))
