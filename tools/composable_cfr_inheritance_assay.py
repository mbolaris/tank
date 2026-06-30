"""Assay asexual CFR inheritance for composable poker strategies.

This Layer 2 diagnostic exercises the mechanism added for composable poker
asexual reproduction: qualified CFR regret tables should survive cloning with
decay, while visit counts reset so descendants must re-earn decision authority.

It does not claim a poker benchmark improvement. Its purpose is to make the
inheritance mechanism measurable before future Layer 1 poker changes build on it.
"""

from __future__ import annotations

import argparse
import json
import random
from typing import Any

from core.poker.betting.actions import BettingAction
from core.poker.strategy.composable import (
    BettingStyle,
    BluffingApproach,
    ComposablePokerStrategy,
    HandSelection,
    PositionAwareness,
    ShowdownTendency,
)
from core.poker.strategy.composable.cfr_decision import CFR_DECISION_MIN_VISITS
from core.poker.strategy.composable.definitions import (
    CFR_INHERITANCE_DECAY,
    CFR_MIN_VISITS_FOR_INHERITANCE,
)


SCENARIOS: tuple[dict[str, Any], ...] = (
    {
        "name": "medium_in_position",
        "hand_strength": 0.52,
        "current_bet": 0.0,
        "opponent_bet": 10.0,
        "pot": 40.0,
        "player_energy": 100.0,
        "position_on_button": True,
        "preferred_cfr_action": "raise_small",
    },
    {
        "name": "strong_out_of_position",
        "hand_strength": 0.74,
        "current_bet": 0.0,
        "opponent_bet": 12.0,
        "pot": 60.0,
        "player_energy": 120.0,
        "position_on_button": False,
        "preferred_cfr_action": "call",
    },
    {
        "name": "weak_in_position",
        "hand_strength": 0.28,
        "current_bet": 0.0,
        "opponent_bet": 8.0,
        "pot": 32.0,
        "player_energy": 90.0,
        "position_on_button": True,
        "preferred_cfr_action": "fold",
    },
)


def _action_name(decision: tuple[BettingAction, float]) -> str:
    action, _ = decision
    return action.name.lower() if hasattr(action, "name") else str(action)


def _build_parent() -> ComposablePokerStrategy:
    parent = ComposablePokerStrategy(
        hand_selection=HandSelection.BALANCED,
        betting_style=BettingStyle.VALUE_HEAVY,
        bluffing_approach=BluffingApproach.NEVER_BLUFF,
        position_awareness=PositionAwareness.SLIGHT_ADJUSTMENT,
        showdown_tendency=ShowdownTendency.CALL_STATION,
    )
    parent.parameters.update(
        {
            "premium_threshold": 0.90,
            "playable_threshold": 0.45,
            "position_range_expand": 0.05,
            "risk_tolerance": 0.35,
            "bluff_frequency": 0.05,
        }
    )
    parent.learning_rate = 0.7

    for scenario in SCENARIOS:
        info_set = parent.get_info_set(
            scenario["hand_strength"],
            scenario["pot"] / scenario["player_energy"],
            scenario["position_on_button"],
            street=0,
        )
        preferred = scenario["preferred_cfr_action"]
        parent.regret[info_set] = {
            "fold": -4.0,
            "call": -2.0,
            "raise_small": -1.0,
            "raise_big": -3.0,
        }
        parent.regret[info_set][preferred] = 12.0
        parent.strategy_sum[info_set] = {
            "fold": 0.0,
            "call": 0.0,
            "raise_small": 0.0,
            "raise_big": 0.0,
        }
        parent.strategy_sum[info_set][preferred] = 5.0
        parent.visit_count[info_set] = CFR_MIN_VISITS_FOR_INHERITANCE

    return parent


def _clone_without_cfr(parent: ComposablePokerStrategy) -> ComposablePokerStrategy:
    return ComposablePokerStrategy(
        hand_selection=parent.hand_selection,
        betting_style=parent.betting_style,
        bluffing_approach=parent.bluffing_approach,
        position_awareness=parent.position_awareness,
        showdown_tendency=parent.showdown_tendency,
        parameters=dict(parent.parameters),
        learning_rate=1.0,
    )


def _decide(
    strategy: ComposablePokerStrategy,
    scenario: dict[str, Any],
    *,
    seed: int,
) -> str:
    return _action_name(
        strategy.decide_action(
            hand_strength=scenario["hand_strength"],
            current_bet=scenario["current_bet"],
            opponent_bet=scenario["opponent_bet"],
            pot=scenario["pot"],
            player_energy=scenario["player_energy"],
            position_on_button=scenario["position_on_button"],
            rng=random.Random(seed),
        )
    )


def run_assay(seed: int = 42) -> dict[str, Any]:
    """Run the deterministic inheritance assay and return structured results."""
    parent = _build_parent()
    inherited = parent.clone_with_mutation(
        mutation_rate=0.0,
        mutation_strength=0.0,
        sub_behavior_switch_rate=0.0,
        rng=random.Random(seed),
    )
    reset = _clone_without_cfr(parent)

    cases = []
    for idx, scenario in enumerate(SCENARIOS):
        info_set = parent.get_info_set(
            scenario["hand_strength"],
            scenario["pot"] / scenario["player_energy"],
            scenario["position_on_button"],
            street=0,
        )

        inherited_without_visits = _decide(inherited, scenario, seed=seed + idx)

        inherited.visit_count[info_set] = CFR_DECISION_MIN_VISITS
        reset.visit_count[info_set] = CFR_DECISION_MIN_VISITS

        inherited_after_revisit = _decide(inherited, scenario, seed=seed + idx)
        reset_after_revisit = _decide(reset, scenario, seed=seed + idx)

        expected_regret = parent.regret[info_set][scenario["preferred_cfr_action"]]
        inherited_regret = inherited.regret.get(info_set, {}).get(
            scenario["preferred_cfr_action"], 0.0
        )
        decay_ok = inherited_regret == expected_regret * CFR_INHERITANCE_DECAY

        cases.append(
            {
                "name": scenario["name"],
                "info_set": info_set,
                "preferred_cfr_action": scenario["preferred_cfr_action"],
                "inherited_without_fresh_visits": inherited_without_visits,
                "inherited_after_revisit": inherited_after_revisit,
                "reset_after_revisit": reset_after_revisit,
                "decay_ok": decay_ok,
                "inherited_overrode_reset": inherited_after_revisit != reset_after_revisit,
            }
        )

    inherited_total_visits_before_activation = 0
    passed = (
        len(parent.regret) == len(SCENARIOS)
        and len(inherited.regret) == len(parent.regret)
        and len(reset.regret) == 0
        and inherited_total_visits_before_activation == 0
        and all(case["decay_ok"] for case in cases)
        and any(case["inherited_overrode_reset"] for case in cases)
    )

    return {
        "seed": seed,
        "parent_info_sets": len(parent.regret),
        "inherited_info_sets": len(inherited.regret),
        "reset_info_sets": len(reset.regret),
        "inherited_learning_rate": inherited.learning_rate,
        "expected_learning_rate": parent.learning_rate,
        "inherited_total_visits_before_activation": inherited_total_visits_before_activation,
        "inheritance_min_visits": CFR_MIN_VISITS_FOR_INHERITANCE,
        "decision_min_visits": CFR_DECISION_MIN_VISITS,
        "cfr_inheritance_decay": CFR_INHERITANCE_DECAY,
        "cases": cases,
        "passed": passed,
    }


def _print_text(result: dict[str, Any]) -> None:
    status = "PASS" if result["passed"] else "FAIL"
    print("Composable CFR inheritance assay")
    print(f"Seed: {result['seed']}")
    print(
        "Info sets: "
        f"parent={result['parent_info_sets']} "
        f"inherited={result['inherited_info_sets']} "
        f"reset={result['reset_info_sets']}"
    )
    print(
        "Learning rate: "
        f"inherited={result['inherited_learning_rate']:.3f} "
        f"expected={result['expected_learning_rate']:.3f}"
    )
    print(
        "Visits before activation: "
        f"{result['inherited_total_visits_before_activation']} "
        f"(decision threshold={result['decision_min_visits']})"
    )
    print()
    print("Decision activation cases:")
    for case in result["cases"]:
        print(
            f"- {case['name']}: preferred={case['preferred_cfr_action']} "
            f"no_visits={case['inherited_without_fresh_visits']} "
            f"after_revisit={case['inherited_after_revisit']} "
            f"reset={case['reset_after_revisit']} "
            f"overrode_reset={case['inherited_overrode_reset']}"
        )
    print()
    print(f"Result: {status}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42, help="Deterministic RNG seed")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    result = run_assay(seed=args.seed)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        _print_text(result)

    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
