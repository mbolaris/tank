# Target Memory Transfer - Multi-Run Study Report

Scenario sets: `v3` | budget: 32 individuals x 30 generations x 5 runs | seeds: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 42, 123]

**Overall verdict (transfer_vs_disjoint): INCONCLUSIVE**

_verdict is positive/negative only when the 95% bootstrap CI of the mean effect excludes zero; otherwise inconclusive_

## Effects (zero-shot, held-out ball set)

| effect | mean | median | 95% CI | seeds positive | verdict |
|---|---|---|---|---|---|
| transfer_vs_disjoint | +0.0003 | +0.0000 | [-0.0036, +0.0046] | 42% | inconclusive |
| transfer_vs_neutral | +0.0131 | +0.0110 | [+0.0079, +0.0189] | 92% | positive |
| memory_mechanism_gain | +0.1581 | +0.1686 | [+0.1422, +0.1741] | 100% | positive |
| source_learning | +0.0022 | +0.0000 | [-0.0016, +0.0074] | 25% | inconclusive |
| target_learnability | +0.0001 | -0.0000 | [-0.0029, +0.0031] | 33% | inconclusive |

## Validity Ladder

| step | metric | mean | median | 95% CI | seeds positive | verdict |
|---|---|---|---|---|---|---|
| 1. memory mechanism gain (default - naive on ball) | +0.1581 | +0.1686 | [+0.1422, +0.1741] | 100% | positive |
| 2. source learning (food_trained - default on food val) | +0.0022 | +0.0000 | [-0.0016, +0.0074] | 25% | inconclusive |
| 3. target learnability (ball_trained - default on ball) | +0.0001 | -0.0000 | [-0.0029, +0.0031] | 33% | inconclusive |
| 4. zero-shot transfer (food_trained - default on ball) | +0.0003 | +0.0000 | [-0.0036, +0.0046] | 42% | inconclusive |
| 5. selection-specific transfer (food_trained - neutral) | +0.0131 | +0.0110 | [+0.0079, +0.0189] | 92% | positive |

## Evolved Genomes (Parameter Drift)

| Parameter | Founder | Food-Trained (Mean ± SD) | Ball-Trained (Mean ± SD) |
|---|---|---|---|
| memory_duration | 90.0000 | 127.3302 ± 64.4733 | 137.5377 ± 78.4214 |
| confidence_decay | 0.0200 | 0.0215 ± 0.0215 | 0.0205 ± 0.0207 |
| switch_threshold | 1.4000 | 1.6890 ± 0.4835 | 1.4740 ± 0.5904 |
| commitment_strength | 0.5000 | 0.5386 ± 0.2118 | 0.4744 ± 0.2696 |
| motion_extrapolation_duration | 30.0000 | 51.5135 ± 27.7852 | 52.7604 ± 27.1205 |
| mutation_rate | 1.0000 | 1.1174 ± 1.0441 | 1.5131 ± 1.3399 |
| mutation_strength | 1.0000 | 1.2871 ± 1.1437 | 1.3161 ± 1.0736 |

## Per-family effects (food_trained - default)

| ball family | mean | median | 95% CI | seeds positive | verdict |
|---|---|---|---|---|---|
| bouncing | +0.0018 | +0.0000 | [-0.0110, +0.0175] | 33% | inconclusive |
| decelerating | -0.0028 | -0.0010 | [-0.0056, -0.0004] | 8% | negative |
| sudden_kick_with_decoy | +0.0039 | +0.0000 | [+0.0006, +0.0090] | 33% | positive |
| swerve | -0.0016 | +0.0000 | [-0.0049, +0.0012] | 33% | inconclusive |

## Adaptation

Reference established on 2 of 12 seeds.
Where established, adaptation acceleration (default - food, generations): mean -5.5, median -5.5, 0% of established seeds positive.
