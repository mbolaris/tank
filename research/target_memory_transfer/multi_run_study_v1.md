# Target Memory Transfer - Multi-Run Study Report

Scenario sets: `v2` | budget: 32 individuals x 30 generations x 5 runs | seeds: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 42, 123]

**Overall verdict (transfer_vs_disjoint): INCONCLUSIVE**

_verdict is positive/negative only when the 95% bootstrap CI of the mean effect excludes zero; otherwise inconclusive_

## Effects (zero-shot, held-out ball set)

| effect | mean | median | 95% CI | seeds positive | verdict |
|---|---|---|---|---|---|
| transfer_vs_disjoint | +0.0028 | +0.0042 | [-0.0023, +0.0075] | 67% | inconclusive |
| transfer_vs_neutral | +0.0267 | +0.0272 | [+0.0177, +0.0352] | 92% | positive |

## Per-family effects (food_trained - default)

| ball family | mean | median | 95% CI | seeds positive | verdict |
|---|---|---|---|---|---|
| bouncing | +0.0010 | +0.0005 | [-0.0111, +0.0103] | 50% | inconclusive |
| decelerating | +0.0039 | +0.0030 | [+0.0002, +0.0081] | 67% | positive |
| sudden_kick_with_decoy | +0.0091 | +0.0085 | [-0.0037, +0.0220] | 75% | inconclusive |
| swerve | -0.0028 | +0.0004 | [-0.0112, +0.0042] | 50% | inconclusive |

## Adaptation

Reference established on 5 of 12 seeds.
Where established, adaptation acceleration (default - food, generations): mean +5.8, median +2.0, 60% of established seeds positive.
