# Target Memory Learnability Audit

Seed: `42` | Sweep: 21 points | Ablation: 32 pop × 30 gen × 3 runs | Elapsed: 105.6s

## Food Domain

### Parameter Sensitivity (1-D Sweeps)

| Parameter | Default | Best | Improvement | Gradient % | Train-Val Corr |
|---|---|---|---|---|---|
| memory_duration | 90.0000 | 10.0000 | +0.0000 | 0% | 0.000 |
| motion_extrapolation_duration | 30.0000 | 0.0000 | +0.0000 | 0% | 0.000 |

### Evolutionary Ablations (evolve single param vs all)

| Evolved | Train Score | Val Score | Improvement vs Default |
|---|---|---|---|
| memory_duration | 0.7304 | 0.7962 | +0.0000 |
| motion_extrapolation_duration | 0.7309 | 0.7962 | +0.0000 |
| **all** | **0.7308** | **0.7962** | **+0.0000** |

## Ball Domain

### Parameter Sensitivity (1-D Sweeps)

| Parameter | Default | Best | Improvement | Gradient % | Train-Val Corr |
|---|---|---|---|---|---|
| memory_duration | 90.0000 | 82.5000 | +0.0000 | 24% | 0.835 |
| motion_extrapolation_duration | 30.0000 | 54.0000 | +0.0077 | 95% | 0.631 |

### Evolutionary Ablations (evolve single param vs all)

| Evolved | Train Score | Val Score | Improvement vs Default |
|---|---|---|---|
| memory_duration | 0.6774 | 0.6207 | -0.0181 |
| motion_extrapolation_duration | 0.6802 | 0.6348 | -0.0040 |
| **all** | **0.6802** | **0.6344** | **-0.0044** |

## Diagnosis

### Food Domain

**No parameters show meaningful improvement > 0.002.**

**Genetic noise** (flat landscape, improvement <= 0.002):
- `memory_duration`: +0.0000
- `motion_extrapolation_duration`: +0.0000

### Ball Domain

**Evolvable parameters** (improvement > 0.002):
- `motion_extrapolation_duration`: best improvement +0.0077

**Genetic noise** (flat landscape, improvement <= 0.002):
- `memory_duration`: +0.0000
