from unittest.mock import MagicMock
from core.entities import Fish
from core.reproduction.niche_cost import get_niche_cost_multiplier


def test_niche_cost_multiplier_low_population():
    # Setup parent fish
    fish = MagicMock(spec=Fish)
    fish.environment = MagicMock()

    # 5 fish total in the environment (under the 10 threshold)
    mock_fish_list = [MagicMock(spec=Fish) for _ in range(5)]
    fish.environment.agents = mock_fish_list

    # Assert cost is 1.0 (no scaling under 10 fish)
    assert get_niche_cost_multiplier(fish) == 1.0


def test_niche_cost_multiplier_scaling():
    fish = MagicMock(spec=Fish)
    env = MagicMock()
    fish.environment = env

    # Create mock fish list
    fish_list = []

    def create_mock_fish(threat, food, social, poker):
        f = MagicMock(spec=Fish)
        f.environment = env
        behavior = MagicMock()
        behavior.threat_response = threat
        behavior.food_approach = food
        behavior.social_mode = social
        behavior.poker_engagement = poker

        f.genome = MagicMock()
        f.genome.behavioral = MagicMock()
        f.genome.behavioral.behavior = MagicMock()
        f.genome.behavioral.behavior.value = behavior
        return f

    # Parent fish behavior: (0, 1, 2, 3)
    parent_fish = create_mock_fish(0, 1, 2, 3)
    fish_list.append(parent_fish)

    # Add 9 other fish
    # 3 other fish have the same behavior (0, 1, 2, 3) -> Total 4 same behavior
    for _ in range(3):
        fish_list.append(create_mock_fish(0, 1, 2, 3))
    # 6 other fish have different behavior (9, 9, 9, 9) -> Total 6
    for _ in range(6):
        fish_list.append(create_mock_fish(9, 9, 9, 9))

    env.agents = fish_list

    # 4/10 = 0.4.
    # Cost = 0.6 + 1.2 * 0.4 = 1.08
    multiplier = get_niche_cost_multiplier(parent_fish)
    assert abs(multiplier - 1.08) < 0.001

    # Add unique strategy (1/11 = 0.0909)
    unique_fish = create_mock_fish(5, 5, 5, 5)
    fish_list.append(unique_fish)  # total 11 fish

    # For unique fish: 1/11
    multiplier_unique = get_niche_cost_multiplier(unique_fish)
    assert abs(multiplier_unique - (0.6 + 1.2 * (1 / 11))) < 0.001

    # For parent behavior fish: 4/11
    multiplier_parent_group = get_niche_cost_multiplier(parent_fish)
    assert abs(multiplier_parent_group - (0.6 + 1.2 * (4 / 11))) < 0.001

    # For other behavior fish: 6/11 (majority in this environment)
    majority_fish = fish_list[4]  # index 4 is the first of the (9,9,9,9) group
    multiplier_majority = get_niche_cost_multiplier(majority_fish)
    assert abs(multiplier_majority - (0.6 + 1.2 * (6 / 11))) < 0.001
