# Control-arm campaign: preregistration

**Status:** criteria fixed before any campaign result existed.
**Committed:** as its own commit, ahead of the commit carrying results, so the
ordering is checkable in `git log` rather than asserted here.

Theme 10.6 of [IMPROVEMENT_PROPOSALS.md](IMPROVEMENT_PROPOSALS.md) asks for the
one thing Theme 10 never produced: a *result*. Four external reviews in a row
have said the same sentence about this project — the platform is stronger than
the scientific evidence. The machinery for a non-AI control arm shipped in 10.5
(`tools/non_ai_baseline.py`) and has never been run at a meaningful budget.

This document fixes the design **before** the numbers exist. Review #3 named
preregistration as one of six requirements for a defensible claim; a bar chosen
after seeing results is not a bar.

## The question

> On a fixed benchmark and seed matrix, what does a deterministic non-AI
> parameter search achieve, and how does that compare with what the AI-agent
> arm has achieved on the same benchmark?

## Arms

| arm | operator | search space | logged as |
|---|---|---|---|
| control | Gaussian parameter mutation (`tools/param_mutator.py`) | `ComposableBehavior` sub-behavior parameters | `agent_id=non-ai-random-search` |
| AI | LLM-proposed source edits, reviewed and gated through CI | unrestricted | merged PRs; `champions/**` history |

**The arms are not symmetric, and this document does not pretend otherwise.**
See *Declared limits* below — that asymmetry is itself one of the findings, and
it is stated here in advance rather than discovered in the discussion section.

## Instrument admission rule (decided before budget is spent)

A benchmark is admitted to the campaign only if the control arm's operator can
**demonstrably move its score**. The pre-flight probe runs `K = 5` mutation
plans on one seed and requires at least one to change the score by more than
`1e-9`.

This rule exists because it already excluded a benchmark. Pre-flight on
`tank/foraging_gym`:

| plan | mutations applied | score | delta |
|---|---|---|---|
| baseline | — | 0.890476 | — |
| 1 | 10 | 0.890476 | +0.000000 |
| 2 | 11 | 0.890476 | +0.000000 |
| 3 | 10 | 0.890476 | +0.000000 |
| 4 | 11 | 0.890476 | +0.000000 |
| 5 | 7 | 0.890476 | +0.000000 |

Fifty-two parameter mutations, zero score movement. The foraging gym pins its
traits at neutral and exercises only the food-pursuit path, while this operator
mutates flee, cohesion, rest, ambush and poker parameters — none of which the
gym can see. Running the arm there would have produced a 0% acceptance rate
that describes the *instrument*, not random search, and it would have looked
exactly like a finding. `tank/foraging_gym` is therefore **excluded**.

## Design

- **Tuning benchmark:** `tank/survival_5k` — the arm searches here.
- **Held-out evaluator:** `heldout/survival_heldout_5k` — a locked path
  (`tools/check_locked_paths.py`) with a deliberately different world config.
  Every **accepted** candidate is re-scored here. The arm never searches on it.
- **Seeds:** 42, 7, 123 for every evaluation, tuning and held-out alike.
- **Acceptance rule:** the arm's existing pre-registered rule in
  `majority_improvement()` — mean gain over the reference, a majority of seeds
  improving, and no seed regressing by more than 10%. Not re-tuned for this
  campaign.
- **Reference:** the **paired local baseline** — unmutated code, same machine,
  same three seeds, measured in the same session as the candidates. Not the
  committed champion record. See the rule below for why.

## Reference admission rule (and an erratum)

**Erratum.** The first version of this document, and the pre-flight artifact
committed with it, claimed that `champions/tank/survival_5k.json` did not
reproduce on this machine — a 15.47-point "cross-platform drift" between CI's
Python 3.10 and this container's 3.11. **That claim was wrong, and it was my
error, not the champion's.** It is corrected here rather than quietly deleted,
because the original is in the pushed history and because the mistake is
instructive.

What actually happened: matrix-format champions store the **mean across their
seed matrix** as the top-level `score`, while the `seed` field names only the
primary seed. The check compared that three-seed mean against a **single-seed**
local run of seed 42 — apples to oranges. `tools/validate_reproduction.py`
documents this exact trap in a comment, and the check walked into it anyway.

Measured like with like, the champion reproduces **exactly**:

| seed | champion `per_seed` | this machine | delta |
|---|---|---|---|
| 42 | 702.5775136245999 | 702.5775136245999 | 0.0 |
| 7 | 749.4781982900204 | 749.4781982900204 | 0.0 |
| 123 | 609.2674835157783 | 609.2674835157783 | 0.0 |
| mean | 687.1077318101328 | 687.1077318101328 | 0.0 |

`check_reference_validity()` now re-runs **every seed the champion records** and
compares each against its own recorded score, with `champion_seed_scores()`
preferring `per_seed` over the mean. A regression test pins the matrix case
using these exact numbers.

**What this does and does not change.** It does not change a single campaign
number. The campaign scored candidates against the **paired local baseline**
measured on the same three seeds, which is bit-identical to the champion on
every seed — so the run is simultaneously a paired-baseline comparison and a
champion comparison, and the acceptance decisions stand exactly as recorded.
The paired baseline also remains the better reference for an independent
reason that survives the erratum: `majority_improvement()` needs per-seed
scores on both sides, and a reference carrying only a mean would silently
degenerate to a single-seed comparison, discarding two thirds of the evidence.

The rule itself is kept, because a champion that genuinely fails to reproduce
would still poison an acceptance rate — the gap between machines would be
scored as though the arm's mutations had caused it. What changed is that the
rule now measures the right thing.

## Preregistered criteria

1. **Primary.** Report the control arm's acceptance rate as
   `accepted / candidates`, with the exact binomial 95% interval. There is no
   pass/fail attached: the number is the result.
2. **Transfer (the criterion that can embarrass the arm).** For every accepted
   candidate, report the held-out delta. The arm is credited with a *transferred*
   improvement only where the held-out score also improves under the same
   `majority_improvement()` rule. **Prediction recorded in advance:** most
   accepted candidates will fail to transfer, because the acceptance rule is
   being applied to a noisy trajectory-sensitive benchmark.
3. **Best achieved.** Report the arm's best mean score against the paired
   local baseline, which is numerically the champion. This is the only
   quantity comparable across the two arms at all.
4. **Compute.** Report wall-clock seconds and benchmark-run count for the whole
   campaign.

## Kill criteria

- If the pre-flight sensitivity probe fails on the tuning benchmark, the
  campaign does not run and that fact is published.
- If the champion reference does not reproduce locally, the campaign runs
  against the paired local baseline and says so; it does not silently score
  against an unreproducible number.
- If the campaign is interrupted, whatever completed is published with its true
  candidate count. The ledger is append-only and written incrementally
  precisely so a partial campaign is still honest evidence.

## Publication rule

**Every attempt is published, including rejections and errors.** The ledger
default (`research/attempts.jsonl`) is gitignored and therefore per-checkout —
which is how review #3's "sixteen rows" measurement evaporated. This campaign
writes to `research/control_arm/`, which is committed. Negative results are the
point, not the residue.

## Declared limits

- **Acceptance rates are not comparable between the arms.** The control arm has
  a denominator because every candidate it draws is logged. The AI arm's
  rejected attempts were never systematically logged — rejections live in
  unmerged branches and abandoned diffs. Comparing the two acceptance rates
  would divide by a number that does not exist. Only criterion 3 (best achieved
  score) is a legitimate cross-arm comparison.
- **The control arm searches a strictly smaller space** — bounded numeric
  parameters, not source edits. It cannot express the changes the AI arm makes.
  A parameter search losing to source edits is unsurprising; a parameter search
  *winning* would be the informative outcome.
- **One tuning benchmark.** Results describe `tank/survival_5k` and its held-out
  sibling; they do not generalise to the soccer or poker ladders.
