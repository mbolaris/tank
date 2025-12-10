import random
from core.genetics import Genome

p1 = Genome.random(rng=random.Random(1))
p2 = Genome.random(rng=random.Random(2))
o = Genome.from_parents(p1, p2, mutation_rate=0.1, mutation_strength=0.1, rng=random.Random(3))
print('offspring eye_size:', o.eye_size)
print('offspring mutation_rate metadata for eye:', o.physical.eye_size.mutation_rate)
print('offspring mutation_strength metadata for eye:', o.physical.eye_size.mutation_strength)
