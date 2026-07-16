# Target Memory Learnability Audit

Seed: `42` | Sweep: 21 points | Ablation: 32 pop × 30 gen × 3 runs | Elapsed: 150.2s

## Food Domain

### Parameter Sensitivity (1-D Sweeps)

| Parameter | Default | Best | Improvement | Gradient % | Train-Val Corr |
|---|---|---|---|---|---|
| memory_duration | 90.0000 | 39.0000 | +0.0000 | 10% | 0.999 |
| confidence_decay | 0.0200 | 0.0010 | +0.0000 | 0% | 0.000 |
| switch_threshold | 1.4000 | 1.7000 | +0.0005 | 0% | -0.742 |
| commitment_strength | 0.5000 | 0.8000 | +0.0005 | 0% | 0.000 |
| motion_extrapolation_duration | 30.0000 | 30.0000 | +0.0000 | 19% | 0.962 |

### Evolutionary Ablations (evolve single param vs all)

| Evolved | Train Score | Val Score | Improvement vs Default |
|---|---|---|---|
| memory_duration | 0.8091 | 0.7982 | -0.0000 |
| confidence_decay | 0.8091 | 0.7982 | -0.0000 |
| switch_threshold | 0.8091 | 0.7982 | -0.0000 |
| commitment_strength | 0.8091 | 0.7982 | -0.0000 |
| motion_extrapolation_duration | 0.8091 | 0.7982 | -0.0000 |
| **all** | **0.8091** | **0.7982** | **-0.0000** |

## Ball Domain

### Parameter Sensitivity (1-D Sweeps)

| Parameter | Default | Best | Improvement | Gradient % | Train-Val Corr |
|---|---|---|---|---|---|
| memory_duration | 90.0000 | 82.5000 | +0.0000 | 24% | 0.835 |
| confidence_decay | 0.0200 | 0.0010 | +0.0000 | 0% | 0.000 |
| switch_threshold | 1.4000 | 1.0000 | +0.0000 | 0% | 0.000 |
| commitment_strength | 0.5000 | 0.0000 | +0.0000 | 0% | 0.000 |
| motion_extrapolation_duration | 30.0000 | 54.0000 | +0.0077 | 95% | 0.631 |

### Evolutionary Ablations (evolve single param vs all)

| Evolved | Train Score | Val Score | Improvement vs Default |
|---|---|---|---|
| memory_duration | 0.6777 | 0.6171 | -0.0217 |
| confidence_decay | 0.6796 | 0.6388 | +0.0000 |
| switch_threshold | 0.6760 | 0.6388 | +0.0000 |
| commitment_strength | 0.6760 | 0.6388 | +0.0000 |
| motion_extrapolation_duration | 0.6793 | 0.6361 | -0.0027 |
| **all** | **0.6840** | **0.6348** | **-0.0040** |

## Diagnosis

### Food Domain

**No parameters show meaningful improvement > 0.002.**

**Genetic noise** (flat landscape, improvement <= 0.002):
- `switch_threshold`: +0.0005
- `commitment_strength`: +0.0005
- `memory_duration`: +0.0000
- `confidence_decay`: +0.0000
- `motion_extrapolation_duration`: +0.0000

### Ball Domain

**Evolvable parameters** (improvement > 0.002):
- `motion_extrapolation_duration`: best improvement +0.0077

**Genetic noise** (flat landscape, improvement <= 0.002):
- `memory_duration`: +0.0000
- `confidence_decay`: +0.0000
- `switch_threshold`: +0.0000
- `commitment_strength`: +0.0000
