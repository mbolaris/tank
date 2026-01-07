from __future__ import annotations

import sys

from core.entities.plant import Plant
from core.environment import Environment
from core.genetics import PlantGenome
from core.root_spots import RootSpot, RootSpotManager


def create_environment() -> tuple[Environment, RootSpotManager]:
    """Set up a minimal environment and root spot manager for plant simulation."""

    return Environment(agents=[], width=800, height=600), RootSpotManager(
        screen_width=800, screen_height=600
    )


def verify_single_plant(spot_id: int = 10, frames: int = 100) -> int:
    """Run a short plant simulation and print energy every 10 frames."""

    environment, manager = create_environment()
    spot: RootSpot | None = manager.get_spot_by_id(spot_id)
    if spot is None:
        print(f"No spot with id {spot_id}")
        return 1

    genome = PlantGenome.create_random()
    plant = Plant(environment=environment, genome=genome, root_spot=spot, initial_energy=50.0)
    spot.claim(plant)

    print("Initial energy:", plant.energy)
    for frame in range(1, frames + 1):
        plant.update(elapsed_time=frame, time_modifier=1.0, time_of_day=1.0)
        if frame % 10 == 0:
            print(f"Frame {frame}: energy={plant.energy:.4f}")

    print(f"Final energy after {frames} frames:", plant.energy)
    return 0


if __name__ == "__main__":
    sys.exit(verify_single_plant())
