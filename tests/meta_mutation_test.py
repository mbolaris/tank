import random
from core.genetics import Genome
from core.evolution.mutation import calculate_adaptive_mutation_rate

R = random.Random(42)

# Create two parents with controlled metadata to observe meta-mutation
p1 = Genome.random(rng=random.Random(1))
p2 = Genome.random(rng=random.Random(2))

# Record initial metadata for eye_size
init_rate = (p1.physical.eye_size.mutation_rate + p2.physical.eye_size.mutation_rate) / 2
init_strength = (
    p1.physical.eye_size.mutation_strength + p2.physical.eye_size.mutation_strength
) / 2

N = 1000
count_meta_rate_changed = 0
count_meta_strength_changed = 0
count_hgt_changed = 0
value_changes = []

for i in range(N):
    o = Genome.from_parents(p1, p2, mutation_rate=0.1, mutation_strength=0.1, rng=random.Random(i))
    m_rate = o.physical.eye_size.mutation_rate
    m_strength = o.physical.eye_size.mutation_strength
    hgt = o.physical.eye_size.hgt_probability
    if abs(m_rate - init_rate) > 1e-9 and m_rate != init_rate:
        count_meta_rate_changed += 1
    if abs(m_strength - init_strength) > 1e-9 and m_strength != init_strength:
        count_meta_strength_changed += 1
    if hgt != (p1.physical.eye_size.hgt_probability + p2.physical.eye_size.hgt_probability) / 2:
        count_hgt_changed += 1
    value_changes.append(o.physical.eye_size.value)

import statistics

print("meta_rate_changed_count:", count_meta_rate_changed, "/", N)
print("meta_strength_changed_count:", count_meta_strength_changed, "/", N)
print("hgt_meta_changed_count:", count_hgt_changed, "/", N)
print("eye_size mean:", statistics.mean(value_changes))
print("eye_size stdev:", statistics.stdev(value_changes))
print("sample values:", value_changes[:10])

# Diagnostic: print adaptive rate/strength for base 0.1 under current config
ar, as_ = calculate_adaptive_mutation_rate(0.1, 0.1)
print("diagnostic adaptive_rate:", ar, "adaptive_strength:", as_)
