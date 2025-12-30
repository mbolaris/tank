import random
from core.genetics import Genome
from core.evolution.mutation import calculate_adaptive_mutation_rate
import statistics

R = random.Random(123)

p1 = Genome.random(rng=random.Random(1))
p2 = Genome.random(rng=random.Random(2))


def run_variation(N=10000):
    count_meta_rate_changed = 0
    count_meta_strength_changed = 0
    count_hgt_changed = 0
    values = []
    # compute adaptive rate/strength for logging
    ar, as_ = calculate_adaptive_mutation_rate(0.1, 0.1)
    for i in range(N):
        o = Genome.from_parents(
            p1, p2, mutation_rate=0.1, mutation_strength=0.1, rng=random.Random(i)
        )
        m_rate = o.physical.eye_size.mutation_rate
        m_strength = o.physical.eye_size.mutation_strength
        hgt = o.physical.eye_size.hgt_probability
        if m_rate != (p1.physical.eye_size.mutation_rate + p2.physical.eye_size.mutation_rate) / 2:
            count_meta_rate_changed += 1
        if (
            m_strength
            != (p1.physical.eye_size.mutation_strength + p2.physical.eye_size.mutation_strength) / 2
        ):
            count_meta_strength_changed += 1
        if hgt != (p1.physical.eye_size.hgt_probability + p2.physical.eye_size.hgt_probability) / 2:
            count_hgt_changed += 1
        values.append(o.physical.eye_size.value)
    print(f"adaptive_rate={ar:.3f} adaptive_strength={as_:.3f} N={N}")
    print(" meta_rate_changed:", count_meta_rate_changed)
    print(" meta_strength_changed:", count_meta_strength_changed)
    print(" hgt_meta_changed:", count_hgt_changed)
    print(" eye mean:", statistics.mean(values), "stdev:", statistics.stdev(values))


if __name__ == "__main__":
    run_variation(N=10000)
