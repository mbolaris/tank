# Target Memory Transfer - Multi-Run Study Report

Scenario sets: `v4` | budget: 32 individuals x 30 generations x 5 runs | seeds: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 42, 123]

Code provenance: `5489e8cce11ffcd46df56afde0bafc3917350b82` | configuration identity: `8b31e3c7876bc2b95ac54378eb2284df801d450bff4d1e5a7fcc3d9ee0464d84`

**Overall verdict (transfer_vs_neutral): INCONCLUSIVE**

_positive only when the 95% bootstrap CI lower bound exceeds 0.01; negative when the upper bound is below zero; otherwise inconclusive_

## Effects (zero-shot, held-out ball set)

| effect | mean | median | 95% CI | seeds positive | verdict |
|---|---|---|---|---|---|
| transfer_vs_disjoint | -0.0127 | -0.0094 | [-0.0200, -0.0058] | 17% | negative |
| transfer_vs_founders | +0.0357 | +0.0348 | [+0.0252, +0.0462] | 100% | positive |
| transfer_vs_neutral | -0.0072 | +0.0004 | [-0.0175, +0.0025] | 58% | inconclusive |
| transfer_efficiency | +0.7445 | +0.7810 | [+0.5297, +0.9676] | 100% | positive |
| memory_mechanism_gain | +0.1581 | +0.1686 | [+0.1422, +0.1741] | 100% | positive |
| source_learning | +0.0213 | +0.0228 | [+0.0135, +0.0291] | 83% | positive |
| target_learnability | +0.0484 | +0.0460 | [+0.0402, +0.0564] | 100% | positive |

## Validity Ladder

| step | metric | mean | median | 95% CI | seeds positive | verdict |
|---|---|---|---|---|---|---|
| 1. memory mechanism gain (default - naive on ball) | +0.1581 | +0.1686 | [+0.1422, +0.1741] | 100% | positive |
| 2. source learning (food_trained - founders on food test) | +0.0213 | +0.0228 | [+0.0135, +0.0291] | 83% | positive |
| 3. target learnability (ball_trained - founders on ball) | +0.0484 | +0.0460 | [+0.0402, +0.0564] | 100% | positive |
| 4. zero-shot transfer (food_trained - founders on ball) | +0.0357 | +0.0348 | [+0.0252, +0.0462] | 100% | positive |
| 5. selection-specific transfer (food_trained - neutral on ball) | -0.0072 | +0.0004 | [-0.0175, +0.0025] | 58% | inconclusive |
| 6. transfer efficiency (zero-shot / target learning) | +0.7445 | +0.7810 | [+0.5297, +0.9676] | 100% | positive |

## Evolved Genomes (Parameter Drift & Trajectories)

| Parameter | Founder (Mean ± SD) | Neutral (Mean ± SD) | Food-Trained (Mean ± SD) | Ball-Trained (Mean ± SD) |
|---|---|---|---|---|
| memory_duration | 118.4227 ± 92.1623 | 110.5672 ± 43.5623 | 96.5255 ± 68.7559 | 131.3102 ± 65.0353 |
| motion_extrapolation_duration | 39.2609 ± 35.6413 | 40.4807 ± 19.6404 | 44.8177 ± 24.3883 | 50.3264 ± 22.6806 |

## Per-family effects (food_trained - default)

| ball family | mean | median | 95% CI | seeds positive | verdict |
|---|---|---|---|---|---|
| bouncing | -0.0085 | -0.0003 | [-0.0177, -0.0007] | 25% | negative |
| decelerating | -0.0263 | -0.0151 | [-0.0442, -0.0101] | 25% | negative |
| sudden_kick_with_decoy | -0.0097 | -0.0017 | [-0.0180, -0.0028] | 0% | negative |
| swerve | -0.0064 | -0.0000 | [-0.0147, +0.0003] | 25% | inconclusive |

## Adaptation

Ref established: Reference established on 2 of 12 seeds.
Where established, adaptation acceleration (default - food, generations): mean -0.5, median -0.5, 0% of established seeds positive.

## Preregistered selection-specific replication

Primary contrast: `transfer_vs_neutral`; practical threshold: 0.01. Verdict: **INCONCLUSIVE**.
Source learning established: True. Next action: `test_bounded_mechanism`. Independent confirmation: false.
