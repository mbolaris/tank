# Target Memory Transfer - Multi-Run Study Report

Scenario sets: `v3` | budget: 32 individuals x 30 generations x 5 runs | seeds: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 42, 123]

**Overall verdict (transfer_vs_disjoint): INCONCLUSIVE**

_verdict is positive/negative only when the 95% bootstrap CI of the mean effect excludes zero; otherwise inconclusive_

## Effects (zero-shot, held-out ball set)

| effect | mean | median | 95% CI | seeds positive | verdict |
|---|---|---|---|---|---|
| transfer_vs_disjoint | +0.0027 | +0.0008 | [-0.0017, +0.0076] | 50% | inconclusive |
| transfer_vs_neutral | +0.0094 | +0.0053 | [+0.0035, +0.0158] | 83% | positive |
| memory_mechanism_gain | +0.1581 | +0.1686 | [+0.1422, +0.1741] | 100% | positive |
| source_learning | +0.0031 | +0.0000 | [-0.0004, +0.0083] | 42% | inconclusive |
| target_learnability | +0.0003 | +0.0000 | [-0.0030, +0.0037] | 42% | inconclusive |

## Validity Ladder

| step | metric | mean | median | 95% CI | seeds positive | verdict |
|---|---|---|---|---|---|---|
| 1. memory mechanism gain (default - naive on ball) | +0.1581 | +0.1686 | [+0.1422, +0.1741] | 100% | positive |
| 2. source learning (food_trained - default on food val) | +0.0031 | +0.0000 | [-0.0004, +0.0083] | 42% | inconclusive |
| 3. target learnability (ball_trained - default on ball) | +0.0003 | +0.0000 | [-0.0030, +0.0037] | 42% | inconclusive |
| 4. zero-shot transfer (food_trained - default on ball) | +0.0027 | +0.0008 | [-0.0017, +0.0076] | 50% | inconclusive |
| 5. selection-specific transfer (food_trained - neutral) | +0.0094 | +0.0053 | [+0.0035, +0.0158] | 83% | positive |

## Evolved Genomes (Parameter Drift)

| Parameter | Founder | Food-Trained (Mean ± SD) | Ball-Trained (Mean ± SD) |
|---|---|---|---|
| memory_duration | 90.0000 | 129.2858 ± 53.7441 | 152.6241 ± 75.7586 |
| confidence_decay | 0.0200 | 0.0235 ± 0.0257 | 0.0226 ± 0.0237 |
| switch_threshold | 1.4000 | 1.7918 ± 0.5548 | 1.5913 ± 0.5435 |
| commitment_strength | 0.5000 | 0.5829 ± 0.2585 | 0.5455 ± 0.2588 |
| motion_extrapolation_duration | 30.0000 | 58.6158 ± 30.0962 | 53.9976 ± 25.2042 |
| mutation_rate | 1.0000 | 0.9979 ± 0.0307 | 0.9956 ± 0.0231 |
| mutation_strength | 1.0000 | 0.9957 ± 0.0385 | 0.9982 ± 0.0301 |

## Per-family effects (food_trained - default)

| ball family | mean | median | 95% CI | seeds positive | verdict |
|---|---|---|---|---|---|
| bouncing | +0.0048 | +0.0000 | [-0.0101, +0.0248] | 25% | inconclusive |
| decelerating | +0.0016 | +0.0000 | [-0.0008, +0.0045] | 33% | inconclusive |
| sudden_kick_with_decoy | +0.0068 | +0.0000 | [-0.0001, +0.0161] | 25% | inconclusive |
| swerve | -0.0023 | +0.0000 | [-0.0067, +0.0015] | 33% | inconclusive |

## Adaptation

Reference established on 3 of 12 seeds.
Where established, adaptation acceleration (default - food, generations): mean +8.3, median +1.0, 67% of established seeds positive.
