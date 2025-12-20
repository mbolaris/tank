import logging
import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from core.genetics.genome import Genome
from core.genetics.physical import PhysicalTraits
from core.genetics import expression

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
            self.genome.physical, 
            self.genome.speed_modifier
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

    def test_mate_compatibility_delegation(self):
        """Verify calculate_mate_compatibility delegates correctly."""
        other = Genome.random()
        score = self.genome.calculate_mate_compatibility(other)
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)
        
        expected = expression.calculate_mate_compatibility(
            self.genome.physical,
            self.genome.behavioral,
            other.physical
        )
        self.assertAlmostEqual(score, expected)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
