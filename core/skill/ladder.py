"""Skill ladder schema: a shared shape for frozen-ruler skill measurement.

A skill ladder benchmark evaluates the evolvable substrate of one domain
(poker, foraging, soccer, ...) against a set of *frozen rulers* - reference
opponents or oracles that never change once committed. Because the rulers are
immutable, ladder metrics stay comparable across champion re-baselines and
config changes, unlike raw benchmark scores.

Benchmarks embed the summary under ``result["metadata"]["skill"]`` via
:meth:`SkillLadderSummary.to_dict`, which makes it land in the champion
registry automatically. Consumers (``tools/skill_status.py``, dashboards)
read it back with :func:`summary_from_champion_data` without caring which
domain produced it.

Conventions:
- ``skill_index`` is calibrated so 0 = floor and 100 = the benchmark's
  ceiling rung. It may exceed 100 when the substrate beats a heuristic
  ceiling (e.g. a greedy oracle is an estimate, not a bound) - report it
  unclamped and let readers see that the ruler needs a taller rung.
- Rungs are ordered weakest to strongest. Changing an existing rung's
  behavior invalidates longitudinal comparisons; add a new rung instead.
"""

from __future__ import annotations

import glob
import json
import os
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RungResult:
    """The substrate's measured performance against one frozen ruler."""

    rung: str
    """Ladder position label, e.g. ``"L0"``."""

    rung_id: str
    """Stable identifier of the ruler, e.g. ``"loose_passive"`` or ``"oracle_greedy"``."""

    metric: float
    """Domain metric against this rung (bb/100, energy ratio, goal diff, ...)."""

    ci_95: tuple[float, float] | None = None
    """Optional 95% confidence interval on ``metric``."""

    beaten: bool = False
    """Whether the substrate beats this rung (domain-defined, ideally CI-backed)."""

    detail: dict[str, Any] = field(default_factory=dict)
    """Free-form domain extras (hands played, sample variance, ...)."""

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "rung": self.rung,
            "rung_id": self.rung_id,
            "metric": self.metric,
            "beaten": self.beaten,
        }
        if self.ci_95 is not None:
            data["ci_95"] = [self.ci_95[0], self.ci_95[1]]
        if self.detail:
            data["detail"] = dict(self.detail)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RungResult:
        ci_raw = data.get("ci_95")
        ci: tuple[float, float] | None = None
        if isinstance(ci_raw, (list, tuple)) and len(ci_raw) == 2:
            ci = (float(ci_raw[0]), float(ci_raw[1]))
        return cls(
            rung=str(data["rung"]),
            rung_id=str(data["rung_id"]),
            metric=float(data["metric"]),
            ci_95=ci,
            beaten=bool(data.get("beaten", False)),
            detail=dict(data.get("detail", {})),
        )


@dataclass(frozen=True)
class SkillLadderSummary:
    """A domain's skill measurement against its frozen ruler ladder."""

    domain: str
    """Domain name: ``"poker"``, ``"foraging"``, ``"soccer"``, ..."""

    benchmark_id: str
    """The benchmark that produced this summary, e.g. ``"poker/ladder_20k"``."""

    metric_name: str
    """Name of the per-rung metric, e.g. ``"bb_per_100"``."""

    skill_index: float
    """Normalized skill: 0 = floor, 100 = ceiling rung (unclamped, see module doc)."""

    rungs: tuple[RungResult, ...]
    """Per-rung results, ordered weakest to strongest."""

    notes: str = ""
    """Honest caveats about the rulers (heuristic ceiling, sample size, ...)."""

    @property
    def rungs_beaten(self) -> int:
        return sum(1 for r in self.rungs if r.beaten)

    @property
    def total_rungs(self) -> int:
        return len(self.rungs)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "domain": self.domain,
            "benchmark_id": self.benchmark_id,
            "metric_name": self.metric_name,
            "skill_index": self.skill_index,
            "rungs_beaten": self.rungs_beaten,
            "total_rungs": self.total_rungs,
            "rungs": [r.to_dict() for r in self.rungs],
        }
        if self.notes:
            data["notes"] = self.notes
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillLadderSummary:
        return cls(
            domain=str(data["domain"]),
            benchmark_id=str(data["benchmark_id"]),
            metric_name=str(data["metric_name"]),
            skill_index=float(data["skill_index"]),
            rungs=tuple(RungResult.from_dict(r) for r in data.get("rungs", [])),
            notes=str(data.get("notes", "")),
        )


def ladder_position_index(rungs: tuple[RungResult, ...]) -> float:
    """Skill index for a *play-against-the-ladder* domain (poker, soccer).

    The substrate plays each frozen ruler; ``skill_index`` is the fraction of
    rungs beaten, scaled to 0-100. 100 means the substrate beats every rung on
    the current ladder - a saturation signal that the ceiling is no longer
    challenging and a taller rung should be added, not proof of perfect play.
    Per-rung margins in the summary preserve the finer picture (including any
    non-monotonicity, e.g. beating a nominal "expert" by more than a weaker
    rung).
    """
    if not rungs:
        return 0.0
    beaten = sum(1 for r in rungs if r.beaten)
    return 100.0 * beaten / len(rungs)


def interpolated_index(metric: float, floor_metric: float, ceiling_metric: float) -> float:
    """Skill index for a *same-task* domain with floor and ceiling references.

    Used when a floor (random) and ceiling (oracle) perform the identical task
    the substrate does, so ``metric`` is directly comparable to both:
    ``100 * (metric - floor) / (ceiling - floor)``. 0 = floor, 100 = ceiling.
    Reported unclamped: >100 means the substrate beat a heuristic ceiling (the
    oracle is an estimate, not a hard bound); <0 means it underperformed the
    floor.
    """
    span = ceiling_metric - floor_metric
    if abs(span) < 1e-12:
        return 0.0
    return 100.0 * (metric - floor_metric) / span


def summary_from_champion_data(champion_data: dict[str, Any]) -> SkillLadderSummary | None:
    """Extract the skill summary from a champion registry JSON structure.

    Accepts both the standard nested format (``{"champion": {...}}``) and a
    bare champion record. Returns None for champions whose benchmark does not
    emit skill metadata (e.g. ecosystem-level benchmarks).
    """
    record = champion_data.get("champion", champion_data)
    metadata = record.get("metadata")
    if not isinstance(metadata, dict):
        return None
    skill = metadata.get("skill")
    if not isinstance(skill, dict):
        return None
    try:
        return SkillLadderSummary.from_dict(skill)
    except (KeyError, TypeError, ValueError):
        return None


def load_ladder_summaries(champions_dir: str | os.PathLike[str]) -> list[SkillLadderSummary]:
    """Load every skill summary embedded in a champion registry directory.

    Scans ``champions_dir`` recursively for ``*.json`` and returns the skill
    summaries of the benchmarks that emit one, sorted by domain then
    benchmark id. Malformed or skill-less champion files are skipped.
    """
    summaries: list[SkillLadderSummary] = []
    pattern = os.path.join(str(champions_dir), "**", "*.json")
    for champ_path in sorted(glob.glob(pattern, recursive=True)):
        try:
            with open(champ_path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        summary = summary_from_champion_data(data)
        if summary is not None:
            summaries.append(summary)
    return sorted(summaries, key=lambda s: (s.domain, s.benchmark_id))
