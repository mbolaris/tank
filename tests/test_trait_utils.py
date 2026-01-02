"""Tests for core.genetics.trait_utils module."""

from core.genetics.trait import GeneticTrait
from core.genetics.trait_utils import get_trait_value, has_trait_value


class TestGetTraitValue:
    """Tests for the get_trait_value helper function."""

    def test_extracts_value_from_valid_trait(self):
        """Should return the inner value from a GeneticTrait."""
        trait = GeneticTrait(1.5)
        assert get_trait_value(trait, default=0.0) == 1.5

    def test_returns_default_for_none_trait(self):
        """Should return default when trait is None."""
        assert get_trait_value(None, default=42.0) == 42.0

    def test_returns_default_for_none_value(self):
        """Should return default when trait.value is None."""
        trait = GeneticTrait(None)
        assert get_trait_value(trait, default=99) == 99

    def test_returns_none_without_default(self):
        """Should return None if no default provided and trait is None."""
        assert get_trait_value(None) is None

    def test_works_with_int_values(self):
        """Should work with integer trait values."""
        trait = GeneticTrait(5)
        assert get_trait_value(trait, default=0) == 5

    def test_works_with_string_values(self):
        """Should work with string trait values."""
        trait = GeneticTrait("hello")
        assert get_trait_value(trait, default="") == "hello"


class TestHasTraitValue:
    """Tests for the has_trait_value helper function."""

    def test_true_for_valid_trait(self):
        """Should return True for a trait with a valid value."""
        trait = GeneticTrait(1.0)
        assert has_trait_value(trait) is True

    def test_false_for_none_trait(self):
        """Should return False when trait is None."""
        assert has_trait_value(None) is False

    def test_false_for_none_value(self):
        """Should return False when trait.value is None."""
        trait = GeneticTrait(None)
        assert has_trait_value(trait) is False

    def test_true_for_zero_value(self):
        """Should return True for zero (0 is a valid value, not None)."""
        trait = GeneticTrait(0)
        assert has_trait_value(trait) is True

    def test_true_for_empty_string(self):
        """Should return True for empty string ('' is a valid value)."""
        trait = GeneticTrait("")
        assert has_trait_value(trait) is True
