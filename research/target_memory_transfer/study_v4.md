# Target Memory Transfer - Multi-Run Study Report

Scenario sets: `v4` | budget: 32 individuals x 30 generations x 5 runs | seeds: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 42, 123]

**Overall verdict (transfer_vs_disjoint): POSITIVE**

_verdict is positive/negative only when the 95% bootstrap CI of the mean effect excludes zero; otherwise inconclusive_

## Effects (zero-shot, held-out ball set)

| effect | mean | median | 95% CI | seeds positive | verdict |
|---|---|---|---|---|---|
| transfer_vs_disjoint | -0.0115 | -0.0066 | [-0.0225, -0.0034] | 8% | negative |
| transfer_vs_founders | +0.0301 | +0.0332 | [+0.0204, +0.0395] | 100% | positive |
| transfer_vs_neutral | -0.0108 | -0.0055 | [-0.0241, -0.0009] | 33% | negative |
| transfer_efficiency | +0.7488 | +0.8245 | [+0.5216, +0.9680] | 100% | positive |
| memory_mechanism_gain | +0.1581 | +0.1686 | [+0.1422, +0.1741] | 100% | positive |
| source_learning | +0.0193 | +0.0196 | [+0.0114, +0.0266] | 83% | positive |
| target_learnability | +0.0419 | +0.0411 | [+0.0351, +0.0491] | 100% | positive |

## Validity Ladder

| step | metric | mean | median | 95% CI | seeds positive | verdict |
|---|---|---|---|---|---|---|
| 1. memory mechanism gain (default - naive on ball) | +0.1581 | +0.1686 | [+0.1422, +0.1741] | 100% | positive |
| 2. source learning (food_trained - founders on food test) | +0.0193 | +0.0196 | [+0.0114, +0.0266] | 83% | positive |
| 3. target learnability (ball_trained - founders on ball) | +0.0419 | +0.0411 | [+0.0351, +0.0491] | 100% | positive |
| 4. zero-shot transfer (food_trained - founders on ball) | +0.0301 | +0.0332 | [+0.0204, +0.0395] | 100% | positive |
| 5. selection-specific transfer (food_trained - neutral on ball) | -0.0108 | -0.0055 | [-0.0241, -0.0009] | 33% | negative |
| 6. transfer efficiency (zero-shot / target learning) | +0.7488 | +0.8245 | [+0.5216, +0.9680] | 100% | positive |

## Evolved Genomes (Parameter Drift & Trajectories)

| Parameter | Founder (Mean ± SD) | Neutral (Mean ± SD) | Food-Trained (Mean ± SD) | Ball-Trained (Mean ± SD) |
|---|---|---|---|---|
| memory_duration | 116.8792 ± 92.1874 | 109.6630 ± 41.0440 | 95.8254 ± 64.5924 | 136.7820 ± 69.0563 |
| motion_extrapolation_duration | 49.9338 ± 39.6535 | 45.7835 ± 21.0969 | 46.6248 ± 22.9307 | 50.9362 ± 22.9795 |

## Per-family effects (food_trained - default)

| ball family | mean | median | 95% CI | seeds positive | verdict |
|---|---|---|---|---|---|
| bouncing | -0.0062 | +0.0000 | [-0.0156, +0.0016] | 17% | inconclusive |
| decelerating | -0.0234 | -0.0035 | [-0.0433, -0.0070] | 17% | negative |
| sudden_kick_with_decoy | -0.0077 | -0.0005 | [-0.0164, -0.0012] | 8% | negative |
| swerve | -0.0088 | -0.0001 | [-0.0221, +0.0007] | 25% | inconclusive |

## Adaptation

Ref established: Reference established on 2 of 12 seeds.
Where established, adaptation acceleration (default - food, generations): mean -0.5, median -0.5, 0% of established seeds positive.
