# Target Memory Transfer - Multi-Run Study Report

Scenario sets: `v3` | budget: 32 individuals x 30 generations x 5 runs | seeds: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 42, 123]

**Overall verdict (transfer_vs_disjoint): INCONCLUSIVE**

_verdict is positive/negative only when the 95% bootstrap CI of the mean effect excludes zero; otherwise inconclusive_

## Effects (zero-shot, held-out ball set)

| effect | mean | median | 95% CI | seeds positive | verdict |
|---|---|---|---|---|---|
| transfer_vs_disjoint | -0.0008 | +0.0007 | [-0.0092, +0.0060] | 50% | inconclusive |
| transfer_vs_neutral | +0.0040 | +0.0028 | [-0.0036, +0.0109] | 75% | inconclusive |
| memory_mechanism_gain | +0.1581 | +0.1686 | [+0.1422, +0.1741] | 100% | positive |
| source_learning | +0.0012 | -0.0000 | [-0.0030, +0.0060] | 25% | inconclusive |
| target_learnability | +0.0004 | +0.0000 | [-0.0029, +0.0037] | 42% | inconclusive |

## Validity Ladder

| step | metric | mean | median | 95% CI | seeds positive | verdict |
|---|---|---|---|---|---|---|
| 1. memory mechanism gain (default - naive on ball) | +0.1581 | +0.1686 | [+0.1422, +0.1741] | 100% | positive |
| 2. source learning (food_trained - default on food val) | +0.0012 | -0.0000 | [-0.0030, +0.0060] | 25% | inconclusive |
| 3. target learnability (ball_trained - default on ball) | +0.0004 | +0.0000 | [-0.0029, +0.0037] | 42% | inconclusive |
| 4. zero-shot transfer (food_trained - default on ball) | -0.0008 | +0.0007 | [-0.0092, +0.0060] | 50% | inconclusive |
| 5. selection-specific transfer (food_trained - neutral) | +0.0040 | +0.0028 | [-0.0036, +0.0109] | 75% | inconclusive |

## Evolved Genomes (Parameter Drift)

| Parameter | Founder | Food-Trained (Mean ± SD) | Ball-Trained (Mean ± SD) |
|---|---|---|---|
| memory_duration | 90.0000 | 143.4130 ± 73.1007 | 133.1773 ± 67.2187 |
| confidence_decay | 0.0200 | 0.0224 ± 0.0229 | 0.0272 ± 0.0263 |
| switch_threshold | 1.4000 | 1.8066 ± 0.6251 | 1.5129 ± 0.4605 |
| commitment_strength | 0.5000 | 0.5508 ± 0.3053 | 0.4788 ± 0.2316 |
| motion_extrapolation_duration | 30.0000 | 59.0143 ± 32.5283 | 53.8627 ± 27.1948 |

## Per-family effects (food_trained - default)

| ball family | mean | median | 95% CI | seeds positive | verdict |
|---|---|---|---|---|---|
| bouncing | +0.0036 | +0.0000 | [-0.0107, +0.0215] | 25% | inconclusive |
| decelerating | -0.0027 | -0.0005 | [-0.0091, +0.0017] | 25% | inconclusive |
| sudden_kick_with_decoy | +0.0002 | +0.0000 | [-0.0193, +0.0154] | 25% | inconclusive |
| swerve | -0.0044 | +0.0000 | [-0.0104, +0.0006] | 33% | inconclusive |

## Adaptation

Reference established on 2 of 12 seeds.
Where established, adaptation acceleration (default - food, generations): mean +0.0, median +0.0, 50% of established seeds positive.
