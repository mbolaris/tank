from __future__ import annotations

from dataclasses import dataclass

from core.entities.fish import Fish
from core.environment import Environment
from core.movement_strategy import AlgorithmicMovement
from core.state_machine import EntityState


@dataclass
class FakeMigrationHandler:
    result: bool = True
    last_call: tuple[str, str, str] | None = None

    def attempt_entity_migration(self, entity, direction: str, source_tank_id: str) -> bool:
        self.last_call = (type(entity).__name__, direction, source_tank_id)
        return self.result


def _make_fish(env: Environment) -> Fish:
    return Fish(
        environment=env,
        movement_strategy=AlgorithmicMovement(),
        species="george1.png",
        x=100,
        y=100,
        speed=3,
    )


def test_fish_migration_returns_false_without_handler() -> None:
    env = Environment(width=800, height=600)
    env.tank_id = "tank-1"
    fish = _make_fish(env)

    assert fish._attempt_migration("left") is False

    assert fish.state.state != EntityState.REMOVED


def test_fish_migration_returns_false_without_tank_id() -> None:
    env = Environment(width=800, height=600)
    env.migration_handler = FakeMigrationHandler(result=True)
    fish = _make_fish(env)

    assert fish._attempt_migration("left") is False

    assert fish.state.state != EntityState.REMOVED


def test_fish_migration_marks_for_removal_on_success() -> None:
    env = Environment(width=800, height=600)
    env.tank_id = "tank-123"
    handler = FakeMigrationHandler(result=True)
    env.migration_handler = handler
    fish = _make_fish(env)

    assert fish._attempt_migration("right") is True

    assert fish.state.state == EntityState.REMOVED
    assert handler.last_call == ("Fish", "right", "tank-123")
