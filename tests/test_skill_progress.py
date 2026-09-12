"""Verdict rules for the skill-progress indicator.

The case that shapes every other one is `test_a_real_noisy_series_reads_as
_stalled`: 35 live poker samples taken off a running tank across 107
generations. `skill_index` there takes five values and jumps the full range
between adjacent samples, so the point of these tests is that a verdict survives
that noise rather than narrating it.
"""

import pytest

from core.research.skill_progress import (
    MIN_SAMPLES,
    ProgressAssessment,
    SkillObservation,
    assess_domain,
)

# Captured from a live tank: /api/skill/snapshots?domain=poker, 111 generations
# in. (generation, frame, skill_index, rungs_beaten, total_rungs)
REAL_POKER_SERIES = [
    (5, 10000, 75, 3, 4),
    (9, 10000, 100, 4, 4),
    (9, 10000, 50, 2, 4),
    (12, 13915, 50, 2, 4),
    (12, 13915, 75, 3, 4),
    (13, 13915, 50, 2, 4),
    (27, 33926, 100, 4, 4),
    (27, 33926, 50, 2, 4),
    (29, 33926, 75, 3, 4),
    (30, 39902, 100, 4, 4),
    (32, 39902, 75, 3, 4),
    (33, 39902, 0, 0, 4),
    (49, 59913, 50, 2, 4),
    (50, 59913, 50, 2, 4),
    (51, 59913, 50, 2, 4),
    (52, 62234, 100, 4, 4),
    (52, 62234, 75, 3, 4),
    (53, 62234, 25, 1, 4),
    (65, 82245, 75, 3, 4),
    (66, 82245, 75, 3, 4),
    (67, 82245, 0, 0, 4),
    (83, 102256, 75, 3, 4),
    (84, 102256, 50, 2, 4),
    (84, 102268, 25, 1, 4),
    (85, 102268, 75, 3, 4),
    (85, 102268, 50, 2, 4),
    (101, 122279, 100, 4, 4),
    (102, 122279, 75, 3, 4),
    (102, 122279, 75, 3, 4),
    (111, 129975, 75, 3, 4),
    (111, 129975, 50, 2, 4),
    (111, 129975, 100, 4, 4),
    (111, 131133, 100, 4, 4),
    (111, 131133, 100, 4, 4),
    (112, 131133, 100, 4, 4),
]


def series(values: list[float], *, total_rungs: int = 4) -> list[SkillObservation]:
    """A clean series, one sample per generation, ascending frames."""
    return [
        SkillObservation(
            generation=i,
            frame=i * 1000,
            skill_index=value,
            rungs_beaten=round(value / 100 * total_rungs),
            total_rungs=total_rungs,
        )
        for i, value in enumerate(values)
    ]


def real_series() -> list[SkillObservation]:
    return [
        SkillObservation(generation=g, frame=f, skill_index=i, rungs_beaten=b, total_rungs=t)
        for g, f, i, b, t in REAL_POKER_SERIES
    ]


class TestNotEnoughEvidence:
    def test_an_unmeasured_domain_is_not_stalled(self) -> None:
        """The distinction that stops someone debugging a subsystem that never ran."""
        assessment = assess_domain("soccer", [])
        assert assessment.verdict == "no_data"
        assert assessment.samples == 0

    @pytest.mark.parametrize("count", list(range(1, MIN_SAMPLES)))
    def test_a_short_series_reports_how_short_it_is(self, count: int) -> None:
        assessment = assess_domain("poker", series([50.0] * count))
        assert assessment.verdict == "no_data"
        assert assessment.samples == count
        assert str(MIN_SAMPLES) in assessment.reason


class TestTheRealSeries:
    def test_a_real_noisy_series_reads_as_stalled(self) -> None:
        """35 live samples over 107 generations: the mean barely moves and the
        noise dwarfs it. A latest-versus-previous indicator would have called
        this progressing, because the last sample is 100 and an earlier one 0."""
        assessment = assess_domain("poker", real_series())

        assert assessment.verdict == "stalled"
        assert assessment.samples == 35
        assert assessment.generation_span == 107
        assert assessment.delta == pytest.approx(4.41, abs=0.01)
        assert assessment.standard_error == pytest.approx(9.39, abs=0.01)
        # The claim the verdict rests on: the move is inside the noise.
        assert abs(assessment.delta) < assessment.standard_error

    def test_the_reason_quotes_the_noise_it_was_judged_against(self) -> None:
        assessment = assess_domain("poker", real_series())
        assert "noise" in assessment.reason
        assert "107 generations" in assessment.reason

    def test_shuffled_input_gives_the_same_verdict(self) -> None:
        """Snapshots arrive in evaluation order, not frame order."""
        forward = assess_domain("poker", real_series())
        backward = assess_domain("poker", list(reversed(real_series())))
        assert backward.as_dict() == forward.as_dict()


class TestTheThreeStates:
    def test_a_clear_climb_is_progressing(self) -> None:
        assessment = assess_domain("foraging", series([20, 25, 22, 24, 70, 75, 72, 74]))
        assert assessment.verdict == "progressing"
        assert assessment.delta > 0

    def test_a_climb_buried_in_noise_is_only_possibly_progressing(self) -> None:
        """Same direction as above, but the windows overlap heavily."""
        assessment = assess_domain("foraging", series([0, 50, 100, 25, 50, 75, 100, 50]))
        assert assessment.verdict in {"possibly_progressing", "stalled"}

    def test_a_flat_series_is_stalled(self) -> None:
        assessment = assess_domain("soccer", series([50, 25, 75, 50, 25, 75, 50, 50]))
        assert assessment.verdict == "stalled"

    def test_a_decline_is_stalled_and_says_so(self) -> None:
        """A fall is not progress either way, but hiding it would be dishonest."""
        assessment = assess_domain("soccer", series([75, 80, 78, 76, 20, 25, 22, 24]))
        assert assessment.verdict == "stalled"
        assert assessment.delta < 0
        assert "decline" in assessment.reason


class TestTheCeiling:
    def test_beating_every_rung_is_not_stalled(self) -> None:
        """The opposite of failure, and it must not be reported as failure."""
        assessment = assess_domain("poker", series([100] * 10))
        assert assessment.verdict == "at_ceiling"
        assert "nothing taller" in assessment.reason

    def test_one_unlucky_sample_does_not_demote_a_saturated_substrate(self) -> None:
        assessment = assess_domain(
            "poker", series([100, 100, 100, 100, 100, 100, 75, 100, 100, 100])
        )
        assert assessment.verdict == "at_ceiling"

    def test_the_ceiling_is_read_from_rung_counts_not_the_index(self) -> None:
        """skill_index may exceed 100 when a heuristic ceiling is beaten, so the
        rung counts are the stronger test (see core/skill/ladder.py)."""
        beyond = [
            SkillObservation(
                generation=i, frame=i * 10, skill_index=140.0, rungs_beaten=4, total_rungs=4
            )
            for i in range(8)
        ]
        assert assess_domain("poker", beyond).verdict == "at_ceiling"

    def test_a_high_but_incomplete_ladder_is_still_judged_on_its_trend(self) -> None:
        """3 of 4 rungs every time is not the ceiling, however high the index."""
        steady = [
            SkillObservation(
                generation=i, frame=i * 10, skill_index=75.0, rungs_beaten=3, total_rungs=4
            )
            for i in range(8)
        ]
        assert assess_domain("poker", steady).verdict == "stalled"


class TestPerfectlyConsistentWindows:
    def test_an_unambiguous_step_with_no_variance_is_progressing(self) -> None:
        """Zero noise makes any gap real; dividing by it must not blow up."""
        assessment = assess_domain("foraging", series([25, 25, 25, 25, 50, 50, 50, 50]))
        assert assessment.verdict == "progressing"
        assert assessment.standard_error == 0.0

    def test_a_perfectly_flat_series_is_stalled_not_progressing(self) -> None:
        assessment = assess_domain("foraging", series([50] * 8, total_rungs=4))
        assert assessment.verdict == "stalled"
        assert assessment.delta == 0.0


def test_the_payload_is_json_safe_and_rounded() -> None:
    payload = assess_domain("poker", real_series()).as_dict()
    assert payload["verdict"] == "stalled"
    assert isinstance(payload["delta"], float)
    assert payload["domain"] == "poker"


def test_an_assessment_is_immutable() -> None:
    assessment = assess_domain("poker", real_series())
    with pytest.raises(AttributeError):
        assessment.verdict = "progressing"  # type: ignore[misc]
    assert isinstance(assessment, ProgressAssessment)
