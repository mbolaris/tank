"""Tests for Genome.normalize() - the self-healing invariant repair.

Genome.normalize() back-fills fields a genome may be missing (a required
poker strategy, and a soccer policy when soccer is enabled) so the "a genome
is complete" invariant lives on the type itself rather than being
re-implemented by every consumer that constructs or loads a Genome. See
docs/ARCHITECTURE_REVIEW.md open item 5's "Related smell" and
core/entities/fish.py's Fish.__init__, the sole current caller.
"""

import random

from core.code_pool.genome_code_pool import GenomeCodePool
from core.genetics import Genome
from core.genetics.code_policy_traits import SOCCER_POLICY
from core.genetics.trait import GeneticTrait


def _make_pool_with_default() -> GenomeCodePool:
    pool = GenomeCodePool()
    pool.register_builtin("soccer_default", SOCCER_POLICY, lambda *a, **k: (0.0, 0.0))
    pool.register_default(SOCCER_POLICY, "soccer_default")
    return pool


def _make_pool_without_default() -> GenomeCodePool:
    pool = GenomeCodePool()
    pool.register_builtin("soccer_alt_a", SOCCER_POLICY, lambda *a, **k: (0.0, 0.0))
    pool.register_builtin("soccer_alt_b", SOCCER_POLICY, lambda *a, **k: (0.0, 0.0))
    return pool


def test_normalize_is_noop_on_a_complete_genome():
    rng = random.Random(42)
    genome = Genome.random(rng=rng)
    before = genome.behavioral.poker_strategy
    assert before is not None and before.value is not None

    genome.normalize(rng=rng, code_pool=None, soccer_enabled=False)

    assert genome.behavioral.poker_strategy is before


def test_normalize_backfills_missing_poker_strategy_trait():
    rng = random.Random(7)
    genome = Genome.random(rng=rng)
    genome.behavioral.poker_strategy = None

    genome.normalize(rng=rng)

    assert genome.behavioral.poker_strategy is not None
    assert genome.behavioral.poker_strategy.value is not None


def test_normalize_backfills_poker_strategy_with_none_value_in_place():
    rng = random.Random(11)
    genome = Genome.random(rng=rng)
    trait = GeneticTrait(None)
    genome.behavioral.poker_strategy = trait

    genome.normalize(rng=rng)

    # Repaired in place (same trait object), not replaced, when the trait
    # wrapper already existed but its value was None.
    assert genome.behavioral.poker_strategy is trait
    assert genome.behavioral.poker_strategy.value is not None


def test_normalize_skips_soccer_backfill_when_disabled():
    rng = random.Random(13)
    genome = Genome.random(rng=rng)
    genome.behavioral.soccer_policy_id = None

    genome.normalize(rng=rng, code_pool=_make_pool_with_default(), soccer_enabled=False)

    assert genome.behavioral.soccer_policy_id is None


def test_normalize_skips_soccer_backfill_without_a_pool():
    rng = random.Random(17)
    genome = Genome.random(rng=rng)
    genome.behavioral.soccer_policy_id = None

    genome.normalize(rng=rng, code_pool=None, soccer_enabled=True)

    assert genome.behavioral.soccer_policy_id is None


def test_normalize_backfills_soccer_policy_from_pool_default():
    rng = random.Random(19)
    genome = Genome.random(rng=rng)
    genome.behavioral.soccer_policy_id = None
    genome.behavioral.soccer_policy_params = None

    genome.normalize(rng=rng, code_pool=_make_pool_with_default(), soccer_enabled=True)

    assert genome.behavioral.soccer_policy_id is not None
    assert genome.behavioral.soccer_policy_id.value == "soccer_default"
    assert genome.behavioral.soccer_policy_params is not None
    assert genome.behavioral.soccer_policy_params.value == {}


def test_normalize_backfills_soccer_policy_randomly_without_a_default():
    rng = random.Random(23)
    genome = Genome.random(rng=rng)
    genome.behavioral.soccer_policy_id = None

    pool = _make_pool_without_default()
    genome.normalize(rng=rng, code_pool=pool, soccer_enabled=True)

    assert genome.behavioral.soccer_policy_id is not None
    assert genome.behavioral.soccer_policy_id.value in pool.get_components_by_kind(SOCCER_POLICY)


def test_normalize_leaves_existing_soccer_policy_untouched():
    rng = random.Random(29)
    genome = Genome.random(rng=rng)
    genome.behavioral.soccer_policy_id = GeneticTrait("already_set")

    genome.normalize(rng=rng, code_pool=_make_pool_with_default(), soccer_enabled=True)

    assert genome.behavioral.soccer_policy_id.value == "already_set"


def test_normalize_is_idempotent():
    rng = random.Random(31)
    genome = Genome.random(rng=rng)
    genome.behavioral.poker_strategy = None
    genome.behavioral.soccer_policy_id = None

    pool = _make_pool_with_default()
    genome.normalize(rng=rng, code_pool=pool, soccer_enabled=True)
    poker_after_first = genome.behavioral.poker_strategy
    soccer_after_first = genome.behavioral.soccer_policy_id

    genome.normalize(rng=rng, code_pool=pool, soccer_enabled=True)

    assert genome.behavioral.poker_strategy is poker_after_first
    assert genome.behavioral.soccer_policy_id is soccer_after_first
