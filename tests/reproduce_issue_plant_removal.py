from core.constants import SCREEN_HEIGHT
from core.entities import Plant
from core.simulation_engine import SimulationEngine


def test_plant_removal_repro():
    simulator = SimulationEngine(headless=True)
    simulator.setup()

    # Clear existing agents and add just one plant
    simulator.entities_list.clear()
    plant = Plant(simulator.environment, 1, x=100, y=SCREEN_HEIGHT - 100)
    simulator.add_entity(plant)

    print(f"Initial agents: {len(simulator.entities_list)}")
    print(f"Plant pos: {plant.pos}")

    # Run simulation
    for i in range(50):
        simulator.update()
        if plant not in simulator.entities_list:
            print(f"Plant removed at frame {i}")
            break

    assert plant in simulator.entities_list, "Plant was removed!"


if __name__ == "__main__":
    try:
        test_plant_removal_repro()
        print("Test passed!")
    except AssertionError as e:
        print(f"Test failed: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
