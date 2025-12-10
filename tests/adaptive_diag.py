from core.evolution.mutation import calculate_adaptive_mutation_rate

for base in [0.02, 0.05, 0.1, 0.15, 0.25, 0.4]:
    for stress in [0.0, 0.2, 0.5, 1.0]:
        ar, as_ = calculate_adaptive_mutation_rate(base, base, population_stress=stress)
        print(f'base={base:.3f} stress={stress:.2f} -> adaptive_rate={ar:.3f} adaptive_strength={as_:.3f}')
