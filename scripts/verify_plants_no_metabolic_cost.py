import sys
from core.entities.fractal_plant import FractalPlant
from core.root_spots import RootSpot, RootSpotManager
from core.environment import Environment
from core.constants import FRACTAL_PLANT_ROOT_SPOT_COUNT

# Create environment and root spots
env = Environment(agents=[], width=800, height=600)
manager = RootSpotManager(screen_width=800, screen_height=600)

# Create a genome and plant at spot 10
from core.entities.fractal_plant import FractalPlant
from core.plant_genetics import PlantGenome

spot = manager.get_spot_by_id(10)
if spot is None:
    print('No spot 10')
    sys.exit(1)

genome = PlantGenome.create_random()
plant = FractalPlant(environment=env, genome=genome, root_spot=spot, initial_energy=50.0)
spot.claim(plant)

print('Initial energy:', plant.energy)
for frame in range(1, 101):
    plant.update(elapsed_time=frame, time_modifier=1.0, time_of_day=1.0)
    if frame % 10 == 0:
        print(f'Frame {frame}: energy={plant.energy:.4f}')

print('Final energy after 100 frames:', plant.energy)
