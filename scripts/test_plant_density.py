from __future__ import annotations

from typing import cast

from core.entities.plant import Plant
from core.genetics import PlantGenome
from core.simulation.engine import SimulationEngine
from core.world import World

sim = SimulationEngine(headless=True)
sim.setup()

# Find three adjacent spots
manager = sim.root_spot_manager
assert manager is not None
spots = manager.spots
# Pick a middle index away from edges
mid = len(spots) // 2
left = spots[mid - 1]
center = spots[mid]
right = spots[mid + 1]

# Create genomes
g1 = PlantGenome.create_random()
g2 = PlantGenome.create_random()
g3 = PlantGenome.create_random()

assert sim.environment is not None
world = cast(World, sim.environment)

p1 = Plant(world, g1, left, plant_id=1)
p2 = Plant(world, g2, center, plant_id=2)
p3 = Plant(world, g3, right, plant_id=3)

# Claim spots
left.claim(p1)
center.claim(p2)
right.claim(p3)

sim.add_entity(p1)
sim.add_entity(p2)
sim.add_entity(p3)

print("Before:", p1.energy, p2.energy, p3.energy)
sim.update()
print("After 1 frame:", p1.energy, p2.energy, p3.energy)
sim.update()
print("After 2 frames:", p1.energy, p2.energy, p3.energy)
