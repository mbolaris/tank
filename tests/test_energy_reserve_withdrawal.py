"""A fish must spend its own reserves before starving while holding them.

Between 29% and 51% of the starvation deaths measured in ``tank/survival_5k``
were fish at exactly zero energy with a non-empty reproduction bank, so these pin
the rule that changed: the bank is spendable on staying alive, and only down to the
starvation threshold, so a fish living off savings still behaves as a starving
one.
"""

from core.config.fish import STARVATION_THRESHOLD_RATIO
from core.entities.fish import Fish
from core.movement_strategy import MovementStrategy
from core.simulation.engine import SimulationEngine


class _StillMovement(MovementStrategy):
    def move(self, sprite: Fish) -> None:
        return None


def _lone_fish(energy: float = 100.0) -> Fish:
    """A fish in an otherwise empty world, so nothing else touches its energy."""
    engine = SimulationEngine(headless=True, seed=42)
    engine.config.ecosystem.initial_fish_count = 0
    engine.config.server.plants_enabled = False
    engine.setup()
    environment = engine.environment
    assert environment is not None

    fish = Fish(
        environment=environment,
        movement_strategy=_StillMovement(),
        species="test_fish",
        x=50,
        y=50,
        speed=5,
    )
    fish._energy_component.energy = energy
    return fish


def test_fish_with_an_empty_bank_still_dies_exactly_as_before() -> None:
    fish = _lone_fish(energy=10.0)
    assert fish._reproduction_component.overflow_energy_bank == 0.0

    fish.modify_energy(-10.0, source="metabolism")

    assert fish.energy == 0.0
    assert fish.is_dead()


def test_fish_spends_its_bank_rather_than_starve_holding_it() -> None:
    fish = _lone_fish(energy=10.0)
    fish._reproduction_component.overflow_energy_bank = 500.0

    fish.modify_energy(-10.0, source="metabolism")

    assert not fish.is_dead()
    assert fish.energy > 0.0
    assert fish._reproduction_component.overflow_energy_bank < 500.0


def test_withdrawal_restores_only_the_starvation_threshold() -> None:
    """Enough to live on, and no more.

    The top-up lands exactly on the threshold, which ``is_starving`` tests
    strictly, so at that instant the fish reads as critical rather than
    starving. It is back under the line as soon as it burns anything - which is
    the point: a fish on reserves keeps foraging instead of coasting.
    """
    fish = _lone_fish(energy=10.0)
    fish._reproduction_component.overflow_energy_bank = 500.0

    fish.modify_energy(-10.0, source="metabolism")

    expected = fish.max_energy * STARVATION_THRESHOLD_RATIO
    assert fish.energy == expected
    assert fish._reproduction_component.overflow_energy_bank == 500.0 - expected
    assert fish.is_critical_energy()

    fish.modify_energy(-0.01, source="metabolism")
    assert fish.is_starving()


def test_a_partial_bank_is_spent_down_to_nothing() -> None:
    """A bank too small to reach the threshold is still worth more than dying."""
    fish = _lone_fish(energy=10.0)
    fish._reproduction_component.overflow_energy_bank = 1.5

    fish.modify_energy(-10.0, source="metabolism")

    assert not fish.is_dead()
    assert fish.energy == 1.5
    assert fish._reproduction_component.overflow_energy_bank == 0.0


def test_a_fish_living_off_reserves_dies_once_they_run_out() -> None:
    """The bank buys time, not immortality."""
    fish = _lone_fish(energy=10.0)
    fish._reproduction_component.overflow_energy_bank = 20.0

    for _ in range(200):
        if fish.is_dead():
            break
        fish.modify_energy(-10.0, source="metabolism")

    assert fish.is_dead()
    assert fish._reproduction_component.overflow_energy_bank == 0.0


def test_gaining_energy_is_untouched_by_the_withdrawal_path() -> None:
    """Overflow still banks on the way up; only the death branch changed."""
    fish = _lone_fish(energy=10.0)
    fish.modify_energy(fish.max_energy * 2, source="ate_food")

    assert fish.energy == fish.max_energy
    assert fish._reproduction_component.overflow_energy_bank > 0.0
