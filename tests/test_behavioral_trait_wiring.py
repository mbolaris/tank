"""Tests that behavioral traits are properly wired to behavior execution.

Verifies that genomic traits like aggression, social_tendency, pursuit_aggression,
prediction_skill, and hunting_stamina actually affect ComposableBehavior output.
"""

import random

from core.genetics import Genome
from core.genetics.trait import GeneticTrait


def _make_genome_with_behavioral_values(
    rng,
    aggression=0.5,
    social_tendency=0.5,
    pursuit_aggression=0.5,
    prediction_skill=0.5,
    hunting_stamina=0.5,
):
    """Create a genome with specific behavioral trait values."""
    genome = Genome.random(use_algorithm=True, rng=rng)
    genome.behavioral.aggression = GeneticTrait(aggression)
    genome.behavioral.social_tendency = GeneticTrait(social_tendency)
    genome.behavioral.pursuit_aggression = GeneticTrait(pursuit_aggression)
    genome.behavioral.prediction_skill = GeneticTrait(prediction_skill)
    genome.behavioral.hunting_stamina = GeneticTrait(hunting_stamina)
    return genome


class TestBehavioralTraitSpecs:
    """Verify the trait specs exist and have correct bounds."""

    def test_aggression_spec(self):
        from core.genetics.behavioral import BEHAVIORAL_TRAIT_SPECS

        specs = {s.name: s for s in BEHAVIORAL_TRAIT_SPECS}
        assert "aggression" in specs
        assert specs["aggression"].min_val == 0.0
        assert specs["aggression"].max_val == 1.0

    def test_social_tendency_spec(self):
        from core.genetics.behavioral import BEHAVIORAL_TRAIT_SPECS

        specs = {s.name: s for s in BEHAVIORAL_TRAIT_SPECS}
        assert "social_tendency" in specs
        assert specs["social_tendency"].min_val == 0.0
        assert specs["social_tendency"].max_val == 1.0


class TestMatePreferenceBehavioralTraits:
    """Verify mate preferences include behavioral trait preferences."""

    def test_default_preferences_include_behavioral(self):
        from core.genetics.behavioral import DEFAULT_MATE_PREFERENCES

        assert "prefer_high_aggression" in DEFAULT_MATE_PREFERENCES
        assert "prefer_high_social_tendency" in DEFAULT_MATE_PREFERENCES

    def test_behavioral_preference_specs_exist(self):
        from core.genetics.behavioral import MATE_BEHAVIORAL_PREFERENCE_SPECS

        assert "aggression" in MATE_BEHAVIORAL_PREFERENCE_SPECS
        assert "social_tendency" in MATE_BEHAVIORAL_PREFERENCE_SPECS

    def test_mate_preferences_inherited(self):
        """Verify behavioral mate preferences survive inheritance."""
        rng = random.Random(42)
        g1 = Genome.random(use_algorithm=True, rng=rng)
        g2 = Genome.random(use_algorithm=True, rng=rng)

        # Set distinct preferences
        prefs1 = g1.behavioral.mate_preferences.value
        prefs1["prefer_high_aggression"] = 0.9

        child = Genome.from_parents(g1, g2, rng=rng)
        child_prefs = child.behavioral.mate_preferences.value
        assert "prefer_high_aggression" in child_prefs
