"""Deterministic contracts for structured movement-intent arbitration."""

from __future__ import annotations

from types import SimpleNamespace

from core.movement.considerations import GraphBehaviorConsideration, MovementArbiter
from core.movement.intents import MovementIntent


class _IntentDrive:
    def __init__(self, name: str, intent: MovementIntent | None) -> None:
        self.name = name
        self._intent = intent
        self.calls = 0

    def intent(self, strategy: object, fish: object) -> MovementIntent | None:
        self.calls += 1
        return self._intent


def _fish() -> object:
    return SimpleNamespace(environment=SimpleNamespace(engine=None))


def test_zero_velocity_is_inactive_and_does_not_preempt_lower_priority_drive() -> None:
    graph = GraphBehaviorConsideration()
    soccer = _IntentDrive(
        "ball_pursuit",
        MovementIntent.from_velocity(
            (1.0, 0.0), kind="soccer_pursuit", source="ball_pursuit", urgency=0.42
        ),
    )
    code_policy = _IntentDrive(
        "code_policy",
        MovementIntent.from_velocity((0.0, 1.0), kind="code_policy", source="code_policy"),
    )
    strategy = SimpleNamespace(_get_graph_velocity=lambda fish: (0.0, 0.0))

    result = MovementArbiter([graph, soccer, code_policy]).arbitrate(strategy, _fish())

    assert result.selected is not None
    assert result.selected.source == "ball_pursuit"
    assert result.suppressed_sources == ("code_policy",)
    assert soccer.calls == 1
    assert code_policy.calls == 0


def test_selected_intent_preserves_priority_without_evaluating_suppressed_drives() -> None:
    first = _IntentDrive(
        "policy_override",
        MovementIntent.from_velocity((1.0, 0.0), kind="policy_override", source="policy_override"),
    )
    second = _IntentDrive(
        "behavior_graph",
        MovementIntent.from_velocity((0.0, 1.0), kind="graph_behavior", source="behavior_graph"),
    )

    result = MovementArbiter([first, second]).arbitrate(object(), _fish())

    assert result.selected is not None
    assert result.selected.velocity == (1.0, 0.0)
    assert result.suppressed_sources == ("behavior_graph",)
    assert first.calls == 1
    assert second.calls == 0


def test_movement_intent_normalizes_metadata_and_can_mark_empty_velocity_inactive() -> None:
    assert (
        MovementIntent.from_velocity((0.0, 0.0), kind="graph", source="graph", allow_zero=False)
        is None
    )
    assert MovementIntent.from_velocity((0.0, 0.0), kind="policy", source="policy") is not None

    intent = MovementIntent.from_velocity(
        (3.0, 4.0), kind="food_pursuit", source="behavior_graph", urgency=2.0, confidence=-1.0
    )

    assert intent is not None
    assert intent.urgency == 1.0
    assert intent.confidence == 0.0
