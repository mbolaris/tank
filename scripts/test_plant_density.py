from core.plant_genetics import PlantGenome
from core.simulation_engine import SimulationEngine

sim = SimulationEngine(headless=True)
sim.setup()

# Find three adjacent spots
manager = sim.root_spot_manager
spots = manager.spots
# Pick a middle index away from edges
mid = len(spots)//2
left = spots[mid-1]
center = spots[mid]
right = spots[mid+1]

from core.entities.fractal_plant import FractalPlant

# Create genomes
g1 = PlantGenome.create_random()
g2 = PlantGenome.create_random()
g3 = PlantGenome.create_random()

p1 = FractalPlant(sim.environment, g1, left)
p2 = FractalPlant(sim.environment, g2, center)
p3 = FractalPlant(sim.environment, g3, right)

# Claim spots
left.claim(p1)
center.claim(p2)
right.claim(p3)

sim.add_entity(p1)
sim.add_entity(p2)
sim.add_entity(p3)

print('Before:', p1.energy, p2.energy, p3.energy)
sim.update()
print('After 1 frame:', p1.energy, p2.energy, p3.energy)
sim.update()
print('After 2 frames:', p1.energy, p2.energy, p3.energy)
