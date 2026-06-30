from __future__ import annotations

import random
from types import SimpleNamespace

from core.genetics import Genome
from core.reproduction.mutation_controller import DiversityMutationController


def _same_behavior_genome(seed: int) -> Genome:
    genome = Genome.random(use_algorithm=False, rng=random.Random(seed))
    genome.behavioral.behavior = None
    return genome


def test_genetic_outlier_gets_lineage_preservation_without_behavior_id() -> None:
    common = _same_behavior_genome(1)
    outlier = _same_behavior_genome(2)

    common.physical.size_modifier.value = 0.5
    common.physical.fin_size.value = 0.5
    common.physical.tail_size.value = 0.5
    common.behavioral.aggression.value = 0.0
    common.behavioral.pursuit_aggression.value = 0.0
    common.behavioral.hunting_stamina.value = 0.0
    common.invalidate_caches()

    outlier.physical.size_modifier.value = 2.0
    outlier.physical.fin_size.value = 2.0
    outlier.physical.tail_size.value = 2.0
    outlier.behavioral.aggression.value = 1.0
    outlier.behavioral.pursuit_aggression.value = 1.0
    outlier.behavioral.hunting_stamina.value = 1.0
    outlier.invalidate_caches()

    crowd = [SimpleNamespace(genome=common) for _ in range(5)]
    rare_parent = SimpleNamespace(genome=outlier)
    fish = [*crowd, rare_parent]
    controller = DiversityMutationController(
        diversity_score_provider=lambda: 0.18,
        fish_provider=lambda: fish,
    )

    context = controller.context_for_parents(rare_parent)

    assert context.preserve_parent_lineage


def test_crowded_genetic_niche_does_not_get_lineage_preservation() -> None:
    common = _same_behavior_genome(3)
    fish = [SimpleNamespace(genome=common) for _ in range(6)]
    controller = DiversityMutationController(
        diversity_score_provider=lambda: 0.18,
        fish_provider=lambda: fish,
    )

    context = controller.context_for_parents(fish[0])

    assert not context.preserve_parent_lineage
