import unittest
from unittest.mock import MagicMock
from core.entities.fish import Fish
from core.entities.fractal_plant import FractalPlant
from core.serializers import FishSerializer, PlantSerializer

class TestSerializers(unittest.TestCase):
    def setUp(self):
        # Mock objects
        self.mock_genome = MagicMock()
        self.mock_genome.speed_modifier = 1.0
        self.mock_genome.size_modifier = 1.0
        self.mock_genome.color_hue = 0.5
        self.mock_genome.template_id = "test_template"
        self.mock_genome.fin_size = 1.0
        self.mock_genome.tail_size = 1.0
        self.mock_genome.body_aspect = 1.0
        self.mock_genome.eye_size = 1.0
        self.mock_genome.pattern_intensity = 0.5
        self.mock_genome.pattern_type = "striped"
        self.mock_genome.behavior_algorithm.algorithm_id = "test_algo"
        self.mock_genome.aggression = 0.7

        self.mock_fish = MagicMock(spec=Fish)
        self.mock_fish.fish_id = 123
        self.mock_fish.generation = 5
        self.mock_fish.energy = 100.0
        self.mock_fish.genome = self.mock_genome
        self.mock_fish.size = 1.0

        self.mock_plant = MagicMock(spec=FractalPlant)
        self.mock_plant.plant_id = 456
        self.mock_plant.generation = 2
        self.mock_plant.energy = 200.0
        self.mock_plant.genome = self.mock_genome

    def test_fish_serializer_player_data(self):
        data = FishSerializer.to_player_data(self.mock_fish, include_aggression=True)
        self.assertEqual(data["fish_id"], 123)
        self.assertEqual(data["energy"], 100.0)
        self.assertEqual(data["aggression"], 0.7)
        self.assertIn("genome_data", data)
        self.assertEqual(data["genome_data"]["color_hue"], 0.5)

    def test_fish_serializer_genome_data(self):
        data = FishSerializer.to_genome_data(self.mock_fish)
        self.assertEqual(data["speed"], 1.0)
        self.assertEqual(data["size"], 1.0)
        self.assertEqual(data["template_id"], "test_template")

    def test_plant_serializer(self):
        data = PlantSerializer.to_player_data(self.mock_plant)
        self.assertEqual(data["plant_id"], 456)
        self.assertEqual(data["energy"], 200.0)
        self.assertEqual(data["species"], "plant")

if __name__ == "__main__":
    unittest.main()
