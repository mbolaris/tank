"""Tests for the skill-ladder schema and status tooling."""

import json
import subprocess
import sys
import unittest
from pathlib import Path

from core.skill import (
    RungResult,
    SkillLadderSummary,
    interpolated_index,
    ladder_position_index,
    summary_from_champion_data,
)

ROOT = Path(__file__).resolve().parents[2]


def _make_summary() -> SkillLadderSummary:
    return SkillLadderSummary(
        domain="poker",
        benchmark_id="poker/ladder_20k",
        metric_name="bb_per_100",
        skill_index=75.0,
        rungs=(
            RungResult("L0", "random", 1000.0, ci_95=(900.0, 1100.0), beaten=True),
            RungResult("L1", "loose_passive", 500.0, beaten=True),
            RungResult("L2", "tight_aggressive", -20.0, ci_95=(-60.0, 20.0), beaten=False),
        ),
        notes="test",
    )


class TestSkillLadderSchema(unittest.TestCase):
    def test_roundtrip_preserves_fields(self):
        summary = _make_summary()
        restored = SkillLadderSummary.from_dict(summary.to_dict())
        self.assertEqual(restored, summary)

    def test_rung_counts(self):
        summary = _make_summary()
        self.assertEqual(summary.total_rungs, 3)
        self.assertEqual(summary.rungs_beaten, 2)

    def test_ci_roundtrip_and_none(self):
        with_ci = RungResult("L0", "random", 1.0, ci_95=(0.5, 1.5))
        self.assertEqual(RungResult.from_dict(with_ci.to_dict()).ci_95, (0.5, 1.5))
        without = RungResult("L1", "x", 1.0)
        self.assertIsNone(RungResult.from_dict(without.to_dict()).ci_95)


class TestSkillIndices(unittest.TestCase):
    def test_ladder_position_index_fraction_beaten(self):
        rungs = (
            RungResult("L0", "a", 1.0, beaten=True),
            RungResult("L1", "b", 1.0, beaten=True),
            RungResult("L2", "c", 1.0, beaten=False),
            RungResult("L3", "d", 1.0, beaten=False),
        )
        self.assertEqual(ladder_position_index(rungs), 50.0)

    def test_ladder_position_index_empty(self):
        self.assertEqual(ladder_position_index(()), 0.0)

    def test_interpolated_index_endpoints_and_midpoint(self):
        self.assertAlmostEqual(interpolated_index(0.0, 0.0, 100.0), 0.0)
        self.assertAlmostEqual(interpolated_index(100.0, 0.0, 100.0), 100.0)
        self.assertAlmostEqual(interpolated_index(42.0, 0.0, 100.0), 42.0)

    def test_interpolated_index_unclamped_above_ceiling(self):
        self.assertGreater(interpolated_index(120.0, 0.0, 100.0), 100.0)

    def test_interpolated_index_degenerate_span(self):
        self.assertEqual(interpolated_index(5.0, 3.0, 3.0), 0.0)


class TestSummaryFromChampion(unittest.TestCase):
    def test_extracts_nested_champion(self):
        champ = {"champion": {"metadata": {"skill": _make_summary().to_dict()}}}
        summary = summary_from_champion_data(champ)
        self.assertIsNotNone(summary)
        assert summary is not None
        self.assertEqual(summary.domain, "poker")

    def test_returns_none_without_skill_metadata(self):
        self.assertIsNone(summary_from_champion_data({"champion": {"metadata": {}}}))
        self.assertIsNone(summary_from_champion_data({"champion": {}}))
        self.assertIsNone(summary_from_champion_data({}))


class TestSkillStatusCli(unittest.TestCase):
    def test_json_output_includes_poker(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "skill_status.py"), "--json"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        domains = {entry["domain"] for entry in payload}
        self.assertIn("poker", domains)


if __name__ == "__main__":
    unittest.main()
