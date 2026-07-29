"""Guards the tank ecosystem against silent energy-economy regressions.

Motivation
----------
Commit d94ae59d ("Add exploration_tendency trait and memory-driven exploration")
made fish swim toward stale remembered food locations whenever no food was
visible, replacing an energy-conserving idle with constant motion. On seed 42 it
drove ``avg_energy`` 12120 -> 7807 and ``starvation_deaths`` 150 -> 295, breaching
the survival_5k validity gate and collapsing the benchmark score 786.6 -> 0.0. It
sat on master for 13 days.

It went unnoticed because the obvious health signal did not move: emergency
spawns and reproduction defend the population setpoint, so ``avg_pop`` drifted
only 51.92 -> 51.39 while the ecosystem underneath was failing. Population is a
*controlled* variable here; energy and death counts are the free ones.

The nightly ``verify-champions`` job did detect it, but that job had already been
red since 2026-06-22 for unrelated reasons, so a new failure was invisible.

What this test actually proves (and what it does not)
-----------------------------------------------------
This test is ``slow``-marked, so it runs in ``nightly-full``, not in the
ordinary PR gates. An earlier version of this docstring claimed the latter;
that was wrong.

More importantly, its discriminating power is far narrower than the headline
numbers suggest. Extending the same comparison from 3 seeds to 12 (current tree
vs the pre-revert tree, same platform, identical benchmark and config):

===========  =====================  ==============  ====================
tree         mean score             valid seeds     mean avg_energy
===========  =====================  ==============  ====================
healthy      550.3 +/- 276          10 of 12        10218
regressed    516.1 +/- 261          10 of 12        9401
===========  =====================  ==============  ====================

That score difference is t = 0.31 - not significant - and the healthy tree wins
on only 5 of the 12 seeds. The spectacular 786.6 -> 0.0 collapse on seed 42 is
the 0.95 starvation validity gate tripping on a knife-edge metric: both trees
sit near 0.89 starvation with ~0.05 spread, so *both* cross the gate on about 2
seeds in 12. Seeds 42 and 123 happen to tip on the regressed tree; seeds 2 and
777 tip on the healthy one.

So this test catches *this* regression on *these three* seeds. It would have
missed an equivalent regression that did not tip seeds 42 or 123, and it will
fail on a legitimate future change that nudges them over the gate. Treat a
failure here as "look at the energy economy", not as proof of a regression, and
confirm any finding across many more seeds before acting on it. Detecting the
mean score difference above at conventional significance needs on the order of
260 seeds; the ~8% avg_energy difference needs roughly 15-20.

The cheap, deterministic half of this guard lives in
``tests/test_foraging_energy_invariants.py``, which pins the *mechanism* the
revert established (no energy spent travelling to stale remembered food unless
already critical) with no simulation and no seed noise, and does run in the
ordinary PR gates.

Thresholds
----------
Assertions are deliberately loose. ``benchmarks/tank/ecosystem_health_10k`` is
known not to be bit-identical between Windows and Linux CI, and per-seed scores
here are trajectory-sensitive, so this test asserts a *magnitude* of health
rather than exact reproduction (``tools/verify_all_champions.py`` owns exact
reproduction). Reference values on the fixed tree are 799.1 / 682.6 / 774.1 with
3 of 3 seeds valid (mean 751.9); the regressed tree scored 0.0 / 780.9 / 0.0 with
1 of 3 valid (mean 260.3). The bounds below sit roughly midway, leaving ~2x
margin on both sides.
"""

import statistics

import pytest

from benchmarks.tank.survival_5k import MAX_VALID_STARVATION_RATE, run

# Seeds recommended by CLAUDE.md for cross-checking tank changes.
SEEDS = (42, 7, 123)

# The regressed tree produced a mean of 260.3; the healthy tree 751.9.
MIN_MEAN_SCORE = 400.0

# The regressed tree kept only 1 of 3 seeds under the starvation gate.
MIN_VALID_SEEDS = 2


@pytest.fixture(scope="module")
def results() -> dict[int, dict]:
    """Run the benchmark once per seed and share across tests (~30s per seed)."""
    return {seed: run(seed) for seed in SEEDS}


@pytest.mark.slow
def test_survival_5k_ecosystem_stays_healthy_across_seeds(results: dict[int, dict]) -> None:
    """Fish must still be able to feed themselves, not merely be respawned."""
    valid_seeds = [seed for seed, r in results.items() if r["metadata"]["score_valid"]]
    scores = [r["score"] for r in results.values()]
    mean_score = statistics.mean(scores)

    report = "\n".join(
        "  seed {:>4}: score={:>8.1f} starvation_rate={:.4f} avg_energy={:>8.0f} "
        "avg_pop={:.2f} valid={}".format(
            seed,
            r["score"],
            r["metadata"]["starvation_rate"],
            r["metadata"]["avg_energy"],
            r["metadata"]["avg_pop"],
            r["metadata"]["score_valid"],
        )
        for seed, r in results.items()
    )

    assert len(valid_seeds) >= MIN_VALID_SEEDS, (
        f"Only {len(valid_seeds)} of {len(SEEDS)} seeds stayed under the "
        f"{MAX_VALID_STARVATION_RATE} starvation gate (need >= {MIN_VALID_SEEDS}). "
        f"Fish are starving faster than they can forage.\n{report}"
    )

    assert mean_score >= MIN_MEAN_SCORE, (
        f"Mean survival_5k score {mean_score:.1f} is below the {MIN_MEAN_SCORE} "
        f"regression floor. The energy economy has degraded.\n{report}"
    )


@pytest.mark.slow
def test_survival_5k_population_is_not_the_health_signal(results: dict[int, dict]) -> None:
    """Pin the trap that hid the original regression.

    ``avg_pop`` is defended by emergency spawns, so it stays near the cap even
    when the ecosystem is collapsing. If a future change makes population a
    genuinely sensitive signal this test should be revisited - but until then,
    nobody should diagnose ecosystem health from it.
    """
    meta = results[42]["metadata"]

    assert meta["avg_pop"] > 40, (
        "Population floor breached - this benchmark assumes spawn logic holds "
        f"population near the cap, but avg_pop was {meta['avg_pop']:.2f}."
    )
    assert meta["population_scope"] == "fish"
