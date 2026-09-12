"""Gathering the series each domain measures with.

`test_skill_progress.py` covers what a series *means*; this covers getting one,
and the two places that is easy to get wrong: rescaling foraging onto the
ladder's 0-100 scale, and not counting the same evaluation twice.
"""

import pytest

from backend.skill_progress_service import (
    DOMAINS,
    SkillProgressService,
    foraging_observation,
    foraging_skill_index,
)

# Shape and values taken from a live /api/skill/foraging-gym/observatory response.
LIVE_RESULT = {
    "status": "success",
    "world_id": "w1",
    "evaluated_at_frame": 131134,
    "evaluated_at_generation": 113,
    "tank_average": 0.9646701599733836,
    "wandering_mean": 0.0994583622283865,
    "perfect_mean": 1.0,
}


class TestForagingRescale:
    def test_the_floor_is_the_wandering_baseline_not_zero(self) -> None:
        """A fish that ignores food already scores ~0.1, so treating the raw
        ratio as a percentage would report 10% skill for doing nothing."""
        assert foraging_skill_index(0.0994583622283865, 0.0994583622283865, 1.0) == 0.0

    def test_matching_the_oracle_is_the_ceiling(self) -> None:
        assert foraging_skill_index(1.0, 0.0995, 1.0) == pytest.approx(100.0)

    def test_a_live_value_lands_between_them(self) -> None:
        index = foraging_skill_index(0.9646701599733836, 0.0994583622283865, 1.0)
        assert index == pytest.approx(96.08, abs=0.01)

    def test_below_the_floor_is_clamped_rather_than_negative(self) -> None:
        assert foraging_skill_index(0.05, 0.0995, 1.0) == 0.0

    def test_a_degenerate_ruler_reports_the_floor_instead_of_dividing_by_zero(self) -> None:
        assert foraging_skill_index(0.5, 1.0, 1.0) == 0.0


class TestForagingObservation:
    def test_a_successful_evaluation_becomes_one_measurement(self) -> None:
        observation = foraging_observation(LIVE_RESULT)
        assert observation is not None
        assert observation.generation == 113
        assert observation.frame == 131134
        assert observation.skill_index == pytest.approx(96.08, abs=0.01)

    def test_a_high_score_short_of_the_oracle_is_not_the_ceiling(self) -> None:
        """96% of oracle is excellent and still has somewhere to go; calling it
        'at ceiling' would stop reporting the last 4%."""
        observation = foraging_observation(LIVE_RESULT)
        assert observation is not None
        assert observation.rungs_beaten == 1
        assert observation.total_rungs == 2
        assert observation.at_ceiling is False

    def test_matching_the_oracle_is_the_ceiling(self) -> None:
        observation = foraging_observation({**LIVE_RESULT, "tank_average": 1.0})
        assert observation is not None
        assert observation.at_ceiling is True

    @pytest.mark.parametrize(
        "result",
        [
            {"status": "no_data", "message": "pending"},
            {"status": "success"},
            {**LIVE_RESULT, "tank_average": "not a number"},
        ],
    )
    def test_absence_of_evidence_is_not_a_measurement_of_zero(self, result: dict) -> None:
        assert foraging_observation(result) is None


class TestTheService:
    def test_a_pending_evaluation_records_nothing(self) -> None:
        service = SkillProgressService(world_manager=None)
        service.record_foraging_result("w1", {"status": "no_data"})
        assert service.foraging_observations("w1") == []

    def test_the_same_evaluation_twice_counts_once(self) -> None:
        """The latest result is re-persisted and re-read; a replay must not look
        like more evidence than it is."""
        service = SkillProgressService(world_manager=None)
        service.record_foraging_result("w1", LIVE_RESULT)
        service.record_foraging_result("w1", LIVE_RESULT)
        assert len(service.foraging_observations("w1")) == 1

    def test_a_later_evaluation_extends_the_series(self) -> None:
        service = SkillProgressService(world_manager=None)
        service.record_foraging_result("w1", LIVE_RESULT)
        service.record_foraging_result(
            "w1", {**LIVE_RESULT, "evaluated_at_frame": 140000, "evaluated_at_generation": 120}
        )
        assert len(service.foraging_observations("w1")) == 2

    def test_worlds_do_not_share_a_series(self) -> None:
        service = SkillProgressService(world_manager=None)
        service.record_foraging_result("w1", LIVE_RESULT)
        assert service.foraging_observations("w2") == []

    def test_every_domain_is_always_reported(self) -> None:
        """A domain that is switched off must still appear, saying so, rather
        than vanishing from the panel."""
        service = SkillProgressService(world_manager=None)
        assessments = service.assess("w1")
        assert [a.domain for a in assessments] == list(DOMAINS)
        assert all(a.verdict == "no_data" for a in assessments)

    def test_a_world_manager_that_knows_nothing_degrades_quietly(self) -> None:
        class EmptyManager:
            def get_world(self, world_id: str) -> None:
                return None

        service = SkillProgressService(world_manager=EmptyManager())
        assert all(a.verdict == "no_data" for a in service.assess("w1"))
