import logging
import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from core.genetics import expression
from core.genetics.genome import Genome


class TestGenomeExpressionRefactor(unittest.TestCase):
    def setUp(self):
        self.genome = Genome.random()

    def test_speed_modifier_delegation(self):
        """Verify speed_modifier property delegates to expression logic."""
        modifier = self.genome.speed_modifier
        self.assertIsInstance(modifier, float)
        self.assertGreaterEqual(modifier, 0.5)
        self.assertLessEqual(modifier, 1.5)

        # Verify it matches direct calculation
        expected = expression.calculate_speed_modifier(self.genome.physical)
        self.assertAlmostEqual(modifier, expected)

    def test_metabolism_rate_delegation(self):
        """Verify metabolism_rate property delegates to expression logic."""
        rate = self.genome.metabolism_rate
        self.assertIsInstance(rate, float)
        self.assertGreaterEqual(rate, 0.5)

        # Verify it matches direct calculation
        expected = expression.calculate_metabolism_rate(
            self.genome.physical, self.genome.speed_modifier
        )
        self.assertAlmostEqual(rate, expected)

    def test_vision_range_delegation(self):
        """Verify vision_range property delegates to expression logic."""
        vision = self.genome.vision_range
        self.assertIsInstance(vision, float)

        expected = expression.calculate_vision_range(self.genome.physical)
        self.assertAlmostEqual(vision, expected)

    def test_color_tint_delegation(self):
        """Verify get_color_tint method delegates to expression logic."""
        tint = self.genome.get_color_tint()
        self.assertIsInstance(tint, tuple)
        self.assertEqual(len(tint), 3)

        expected = expression.calculate_color_tint(self.genome.physical)
        self.assertEqual(tint, expected)

    def test_mate_attraction_delegation(self):
        """Verify calculate_mate_attraction delegates correctly."""
        other = Genome.random()
        score = self.genome.calculate_mate_attraction(other)
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

        expected = expression.calculate_mate_attraction(
            self.genome.physical, self.genome.behavioral, other.physical
        )
        self.assertAlmostEqual(score, expected)

    def test_disassortative_mating_preferences(self):
        """Verify that prefer_similar_size and prefer_different_color modulate attraction scores."""
        from core.genetics.genome import Genome

        # Create identical clones (except preference alleles)
        g1 = Genome.random()
        g2 = Genome.random()

        # Make physical traits identical so similarity = 1.0
        g2.physical = g1.physical

        # Test 1: Assortative Mating for Size (prefer_similar_size = 1.0)
        g1.behavioral.mate_preferences.value["prefer_similar_size"] = 1.0
        g1.behavioral.mate_preferences.value["prefer_different_color"] = 0.5  # neutral
        score_assortative = g1.calculate_mate_attraction(g2)

        # Test 2: Disassortative Mating for Size (prefer_similar_size = 0.0)
        g1.behavioral.mate_preferences.value["prefer_similar_size"] = 0.0
        score_disassortative = g1.calculate_mate_attraction(g2)

        # Because g1 and g2 are identical (size similarity is 1.0):
        # - Assortative (prefer_similar_size = 1.0) gets size similarity = 1.0 with weight 1.0.
        # - Disassortative (prefer_similar_size = 0.0) gets size similarity = 0.0 with weight 1.0.
        # So score_assortative should be strictly greater than score_disassortative.
        self.assertGreater(score_assortative, score_disassortative)

        # Test 3: Assortative Mating for Color (prefer_different_color = 0.0)
        g1.behavioral.mate_preferences.value["prefer_similar_size"] = 0.5  # neutral
        g1.behavioral.mate_preferences.value["prefer_different_color"] = 0.0
        score_color_assortative = g1.calculate_mate_attraction(g2)

        # Test 4: Disassortative Mating for Color (prefer_different_color = 1.0)
        g1.behavioral.mate_preferences.value["prefer_different_color"] = 1.0
        score_color_disassortative = g1.calculate_mate_attraction(g2)

        # Because g1 and g2 have identical colors (color similarity is 1.0):
        # - Assortative (prefer_different_color = 0.0) gets color similarity = 1.0 with weight 1.0.
        # - Disassortative (prefer_different_color = 1.0) gets color similarity = 0.0 with weight 1.0.
        # So score_color_assortative should be strictly greater than score_color_disassortative.
        self.assertGreater(score_color_assortative, score_color_disassortative)

    def test_neutral_preferences_behavior(self):
        """Verify that when preferences are 0.5, their weights are 0.0 (neutral)."""
        from core.genetics.genome import Genome

        g1 = Genome.random()
        g2 = Genome.random()

        # Set physical traits to be identical first
        g2.physical = g1.physical

        # Default preferences are 0.5
        g1.behavioral.mate_preferences.value["prefer_similar_size"] = 0.5
        g1.behavioral.mate_preferences.value["prefer_different_color"] = 0.5

        # Calculate attraction with identical and different size/color
        # Save original size
        orig_size = g2.physical.size_modifier.value
        g2.physical.size_modifier.value = g1.physical.size_modifier.value
        score_similar = g1.calculate_mate_attraction(g2)

        g2.physical.size_modifier.value = orig_size + 0.5  # different size
        score_different = g1.calculate_mate_attraction(g2)

        # Since weight of size modifier is 0.0, changing size should not affect attraction score!
        self.assertAlmostEqual(score_similar, score_different)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
