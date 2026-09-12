"""The regulation sweep's arithmetic, and one short real run to keep it honest."""

import pytest

from core.research.regulation import (
    RegulationPoint,
    RegulationSweep,
    SteadyState,
    measure_steady_state,
    spread_ratio,
)


def _steady(**kwargs: float) -> SteadyState:
    base: dict[str, float] = {
        "population": 60.0,
        "raw_energy": 5010.0,
        "banked_energy": 6200.0,
        "food_stock": 90.0,
        "samples": 30,
        "drift": 0.0,
    }
    base.update(kwargs)
    return SteadyState(**base)  # type: ignore[arg-type]


def test_spread_ratio_reports_magnitude_of_variation() -> None:
    assert spread_ratio([2.0, 4.0, 8.0]) == 4.0
    assert spread_ratio([5.0, 5.0]) == 1.0


def test_spread_ratio_refuses_to_call_a_collapsed_run_infinitely_responsive() -> None:
    """A zero floor would give an unbounded ratio, which reads as the opposite
    of what a collapsed population means."""
    assert spread_ratio([0.0, 100.0]) == 0.0
    assert spread_ratio([]) == 0.0


def test_energy_per_fish_is_regulated_energy_over_capped_population() -> None:
    assert _steady().raw_energy_per_fish == pytest.approx(83.5)


def test_energy_per_fish_survives_an_extinct_sample() -> None:
    assert _steady(population=0.0).raw_energy_per_fish == 0.0


def _sweep() -> RegulationSweep:
    return RegulationSweep(
        benchmark_id="tank/survival_5k",
        key="auto_food_spawn_rate",
        points=(
            RegulationPoint(2, 42, _steady(raw_energy=5766.5, banked_energy=9181.0)),
            RegulationPoint(9, 42, _steady(raw_energy=5010.3, banked_energy=6200.0)),
            RegulationPoint(36, 42, _steady(raw_energy=2500.0, banked_energy=1000.0)),
        ),
    )


def test_output_spread_is_reported_against_the_input_spread() -> None:
    """The comparison the sweep exists to make: how far the output moved
    against how far the input was pushed."""
    sweep = _sweep()
    assert sweep.input_spread() == 18.0
    assert sweep.field_spread("raw_energy") == pytest.approx(2.3066, abs=1e-4)
    assert sweep.field_spread("population") == 1.0


def test_banked_energy_is_reported_apart_from_regulated_energy() -> None:
    """The food controller sums fish.energy and never sees the bank, while the
    benchmark score counts both - so a sweep that merged them would hide the
    only unregulated term."""
    sweep = _sweep()
    assert sweep.field_spread("banked_energy") > sweep.field_spread("raw_energy")
    point = sweep.as_dict()["points"][0]
    assert point["raw_energy"] == 5766.5
    assert point["banked_energy"] == 9181.0


def test_values_are_deduplicated_in_order() -> None:
    sweep = RegulationSweep(
        benchmark_id="b",
        key="k",
        points=(
            RegulationPoint(9, 1, _steady()),
            RegulationPoint(9, 2, _steady()),
            RegulationPoint(2, 3, _steady()),
        ),
    )
    assert sweep.values() == [9, 2]


@pytest.mark.parametrize("warmup", [-0.1, 1.0, 2.0])
def test_a_warmup_that_would_discard_everything_is_rejected(warmup: float) -> None:
    import benchmarks.tank.survival_5k as benchmark

    with pytest.raises(ValueError, match="warmup_fraction"):
        measure_steady_state(benchmark, 42, frames=10, warmup_fraction=warmup)


def test_a_short_real_run_reports_a_populated_tank() -> None:
    """Cheap end-to-end check that the sampler reads the world, not a shape."""
    import benchmarks.tank.survival_5k as benchmark

    steady = measure_steady_state(
        benchmark, 42, frames=300, warmup_fraction=0.0, sample_interval=50
    )

    assert steady.samples == 6
    assert steady.population > 0
    assert steady.raw_energy > 0
    assert steady.raw_energy_per_fish > 0
