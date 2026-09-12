"""Decide whether a skill domain is progressing, might be, or has stalled.

The question "is evolution getting better at poker?" looks like it should be
answered by comparing the last measurement to the one before it. Measured, that
would be worthless. A live ladder snapshot evaluates *one sampled individual or
team*, and `skill_index` is `rungs_beaten / total_rungs * 100`, so on a real
tank it takes only five values - 0, 25, 50, 75, 100 - and adjacent samples jump
the whole way. One observed poker series moved 100 -> 0 -> 50 between
consecutive snapshots while the population underneath it was not changing at
all. An indicator built on "latest versus previous" would flip between
"progressing" and "stalled" every few seconds and mean nothing.

So a verdict here is a claim about a *distribution over time*, and it is made
the way such a claim has to be: compare the mean of a recent window against the
mean of an earlier one, and require the difference to be larger than the
sampling noise can comfortably explain. The noise estimate is the standard error
of the difference of the two means, which is why a domain needs a handful of
samples before any verdict is offered at all.

Three states were asked for; two more are here because without them the honest
answer would have to be a lie:

* `no_data` - nothing has been measured yet. A domain that has never been
  evaluated is not stalled, and saying so would send someone hunting for a
  problem in a subsystem that simply never ran.
* `at_ceiling` - the substrate beats every rung on the ruler. There is nothing
  left to climb, so "stalled" would read as failure when it is the opposite.
  The ladder's own docstring anticipates this: a ceiling that is reached is a
  sign the ruler needs a taller rung.

A decline is reported as `stalled` with the drop named in the reason, rather
than as a sixth state: the question asked was whether progress is happening,
and the answer there is no either way.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean, variance

#: `skill_index` is calibrated so 100 is the ruler's ceiling rung (core/skill/ladder.py).
CEILING_INDEX = 100.0

#: Below this, the two windows cannot support a variance estimate worth having.
#: Six keeps at least three samples on each side of the split.
MIN_SAMPLES = 6

#: Multiples of the standard error of the difference. Two is the usual bar for
#: "not plausibly noise"; one is the honest middle ground the "possibly" state
#: exists to express.
STRONG_SIGMA = 2.0
WEAK_SIGMA = 1.0

#: Share of the recent window that must sit at the ceiling to call it reached.
#: Not 1.0: a single unlucky sample of a saturated substrate should not demote
#: the verdict to "stalled".
CEILING_SHARE = 0.8

VERDICTS = ("no_data", "at_ceiling", "progressing", "possibly_progressing", "stalled")


@dataclass(frozen=True)
class SkillObservation:
    """One live ladder evaluation of one sampled subject."""

    generation: int
    frame: int
    skill_index: float
    rungs_beaten: int = 0
    total_rungs: int = 0

    @property
    def at_ceiling(self) -> bool:
        """Whether this sample beat every rung the ruler offers.

        Prefers the rung counts to the index: `skill_index` is documented as
        able to exceed 100 when the substrate beats a heuristic ceiling, so a
        comparison against 100 alone would be the weaker test.
        """
        if self.total_rungs > 0:
            return self.rungs_beaten >= self.total_rungs
        return self.skill_index >= CEILING_INDEX


@dataclass(frozen=True)
class ProgressAssessment:
    """A verdict about one domain, with the numbers that produced it."""

    domain: str
    verdict: str
    reason: str
    samples: int
    earlier_mean: float | None = None
    recent_mean: float | None = None
    delta: float | None = None
    standard_error: float | None = None
    generation_span: int = 0
    ceiling_share: float = 0.0

    def as_dict(self) -> dict[str, object]:
        return {
            "domain": self.domain,
            "verdict": self.verdict,
            "reason": self.reason,
            "samples": self.samples,
            "earlier_mean": _round(self.earlier_mean),
            "recent_mean": _round(self.recent_mean),
            "delta": _round(self.delta),
            "standard_error": _round(self.standard_error),
            "generation_span": self.generation_span,
            "ceiling_share": round(self.ceiling_share, 3),
        }


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 3)


def _standard_error(earlier: list[float], recent: list[float]) -> float:
    """Standard error of the difference between the two window means.

    Welch's form - the windows are not assumed to share a variance, because a
    substrate that has become *consistent* is a real and interesting outcome
    that pooling would smear away.
    """
    earlier_var = variance(earlier) if len(earlier) > 1 else 0.0
    recent_var = variance(recent) if len(recent) > 1 else 0.0
    return float((earlier_var / len(earlier) + recent_var / len(recent)) ** 0.5)


def assess_domain(domain: str, observations: list[SkillObservation]) -> ProgressAssessment:
    """Judge one domain from its live ladder samples."""
    ordered = sorted(observations, key=lambda o: (o.frame, o.generation))
    samples = len(ordered)

    if samples == 0:
        return ProgressAssessment(
            domain=domain,
            verdict="no_data",
            reason="Nothing measured yet in this world.",
            samples=0,
        )

    span = ordered[-1].generation - ordered[0].generation
    ceiling_share = sum(1 for o in ordered if o.at_ceiling) / samples

    if samples < MIN_SAMPLES:
        return ProgressAssessment(
            domain=domain,
            verdict="no_data",
            reason=(
                f"Only {samples} measurement{'s' if samples != 1 else ''} so far; "
                f"{MIN_SAMPLES} are needed before a trend means anything."
            ),
            samples=samples,
            generation_span=span,
            ceiling_share=ceiling_share,
        )

    split = samples // 2
    earlier = [o.skill_index for o in ordered[:split]]
    recent = [o.skill_index for o in ordered[samples - split :]]
    earlier_mean, recent_mean = fmean(earlier), fmean(recent)
    delta = recent_mean - earlier_mean
    error = _standard_error(earlier, recent)

    recent_ceiling = sum(1 for o in ordered[samples - split :] if o.at_ceiling) / split
    if recent_ceiling >= CEILING_SHARE:
        return ProgressAssessment(
            domain=domain,
            verdict="at_ceiling",
            reason=(
                f"Beats every rung in {recent_ceiling:.0%} of recent samples - "
                "this ruler has nothing taller left to measure."
            ),
            samples=samples,
            earlier_mean=earlier_mean,
            recent_mean=recent_mean,
            delta=delta,
            standard_error=error,
            generation_span=span,
            ceiling_share=ceiling_share,
        )

    over = f"over {span} generations" if span > 0 else "so far"

    if error == 0.0:
        # Both windows are perfectly consistent, so any gap at all is real.
        verdict = "progressing" if delta > 0 else "stalled"
        reason = (
            f"Every sample in both windows was identical; the index moved " f"{delta:+.0f} {over}."
        )
    elif delta >= STRONG_SIGMA * error:
        verdict = "progressing"
        reason = (
            f"Skill index rose {delta:+.1f} {over}, " f"{delta / error:.1f}x the sampling noise."
        )
    elif delta >= WEAK_SIGMA * error:
        verdict = "possibly_progressing"
        reason = (
            f"Skill index is up {delta:+.1f} {over}, but only "
            f"{delta / error:.1f}x the sampling noise - not yet separable from luck."
        )
    elif delta <= -STRONG_SIGMA * error:
        verdict = "stalled"
        reason = (
            f"Skill index fell {delta:+.1f} {over}, "
            f"{abs(delta) / error:.1f}x the sampling noise. This is a decline, not a plateau."
        )
    else:
        verdict = "stalled"
        reason = (
            f"Skill index moved {delta:+.1f} {over}, well inside the "
            f"{error:.1f} of noise these samples carry."
        )

    return ProgressAssessment(
        domain=domain,
        verdict=verdict,
        reason=reason,
        samples=samples,
        earlier_mean=earlier_mean,
        recent_mean=recent_mean,
        delta=delta,
        standard_error=error,
        generation_span=span,
        ceiling_share=ceiling_share,
    )
