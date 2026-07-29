"""The phase validator must not cry wolf.

``validate_system_phase_declarations`` warns when a system declares an
``UpdatePhase`` but is not scheduled in the explicit phase loop. It checks that
by comparing against a hand-written ``phase_map`` that duplicates what
``SystemCoordinator.run_*`` actually calls - and the two drifted: the map's
INTERACTION entry listed only the two poker systems, while
``run_interaction()`` also calls ``tank_interaction_system``. Every tank run
therefore logged

    System TankInteractions declares phase INTERACTION but is not scheduled
    in the explicit phase loop

about a system that was running perfectly well. A warning nobody can trust is
worse than no warning, and this one shipped on every benchmark run.
"""

from __future__ import annotations

import logging

import pytest

from core.simulation.coordinator import SystemCoordinator
from core.worlds import WorldRegistry

CONFIG = {
    "headless": True,
    "screen_width": 2000,
    "screen_height": 2000,
    "max_population": 60,
    "plants_enabled": False,
}


def _phase_warnings(records: list[logging.LogRecord]) -> list[str]:
    return [
        record.getMessage()
        for record in records
        if record.levelno >= logging.WARNING
        and (
            "not scheduled in the explicit phase loop" in record.getMessage()
            or "but runs in" in record.getMessage()
        )
    ]


@pytest.mark.parametrize("world_type", ["tank", "petri"])
def test_no_phase_declaration_warnings_on_world_setup(
    world_type: str, caplog: pytest.LogCaptureFixture
) -> None:
    """A correctly wired world must produce no phase warnings at all."""
    with caplog.at_level(logging.WARNING):
        try:
            world = WorldRegistry.create_world(world_type, seed=42, config=CONFIG)
        except Exception as exc:  # unregistered world type in this build
            pytest.skip(f"world type {world_type!r} unavailable: {exc}")
        world.reset(seed=42, config=CONFIG)

    warnings = _phase_warnings(caplog.records)
    assert not warnings, "phase validator reported systems that are in fact scheduled:\n  " + (
        "\n  ".join(warnings)
    )


def test_tank_interaction_system_is_actually_run_in_the_interaction_phase() -> None:
    """Pins the substance behind the warning, not just its absence.

    If ``run_interaction`` stops calling ``tank_interaction_system``, silencing
    the warning by listing it in the validator's map would be wrong - so assert
    the coordinator really does execute it.
    """
    world = WorldRegistry.create_world("tank", seed=42, config=CONFIG)
    world.reset(seed=42, config=CONFIG)
    engine = world.engine

    assert engine.tank_interaction_system is not None, "tank world has no interaction system"

    calls: list[int] = []
    original = engine.tank_interaction_system.update
    engine.tank_interaction_system.update = lambda frame: calls.append(frame)  # type: ignore[method-assign]
    try:
        coordinator = SystemCoordinator()
        coordinator.tank_interaction_system = engine.tank_interaction_system
        coordinator.run_interaction(7)
    finally:
        engine.tank_interaction_system.update = original  # type: ignore[method-assign]

    assert calls == [7], "SystemCoordinator.run_interaction did not run the interaction system"
