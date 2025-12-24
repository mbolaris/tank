"""Entity statistics calculation.

This module calculates statistics about simulation entities:
- Fish counts and energy
- Food counts and energy  
- Plant counts and energy
- Fish health distribution
"""

import time
from statistics import median
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from core.simulation import SimulationEngine


def get_simulation_state(engine: "SimulationEngine") -> Dict[str, Any]:
    """Get simulation state statistics.

    Returns:
        Dictionary with frame count, time, and speed stats
    """
    from core.config.display import FRAME_RATE

    elapsed = time.time() - engine.start_time
    return {
        "frame_count": engine.frame_count,
        "time_string": engine.time_system.get_time_string(),
        "elapsed_real_time": elapsed,
        "simulation_speed": (
            engine.frame_count / (FRAME_RATE * elapsed)
            if elapsed > 0
            else 0
        ),
    }


def get_entity_stats(engine: "SimulationEngine") -> Dict[str, Any]:
    """Get entity count and energy statistics.

    Returns:
        Dictionary with entity counts and energy totals
    """
    from core import entities
    from core.entities.plant import Plant

    fish_list = engine.get_fish_list()
    all_food_list = engine.get_food_list()

    # Separate food types
    live_food_list = [
        e for e in all_food_list if isinstance(e, entities.LiveFood)
    ]
    regular_food_list = [
        e for e in all_food_list if not isinstance(e, entities.LiveFood)
    ]

    # Plant lists
    plants = [
        e for e in engine.entities_list if isinstance(e, Plant)
    ]

    return {
        "fish_count": len(fish_list),
        "fish_energy": sum(
            fish.energy + fish._reproduction_component.overflow_energy_bank
            for fish in fish_list
        ),
        "food_count": len(regular_food_list),
        "food_energy": sum(food.energy for food in regular_food_list),
        "live_food_count": len(live_food_list),
        "live_food_energy": sum(food.energy for food in live_food_list),
        "plant_count": len(plants),
        "plant_energy": sum(plant.energy for plant in plants),
    }


def get_fish_health_stats(engine: "SimulationEngine") -> Dict[str, Any]:
    """Get fish health and energy distribution statistics.

    Returns:
        Dictionary with fish health stats (critical, low, healthy, full)
    """
    fish_list = engine.get_fish_list()

    if not fish_list:
        return {
            "avg_fish_energy": 0.0,
            "min_fish_energy": 0.0,
            "max_fish_energy": 0.0,
            "min_max_energy_capacity": 0.0,
            "max_max_energy_capacity": 0.0,
            "median_max_energy_capacity": 0.0,
            "fish_health_critical": 0,
            "fish_health_low": 0,
            "fish_health_healthy": 0,
            "fish_health_full": 0,
        }

    fish_energies = [fish.energy for fish in fish_list]
    max_energies = [fish.max_energy for fish in fish_list]

    # Count fish in different energy health states
    critical_count = 0
    low_count = 0
    healthy_count = 0
    full_count = 0

    for fish in fish_list:
        ratio = fish.energy / fish.max_energy if fish.max_energy > 0 else 0
        if ratio < 0.15:
            critical_count += 1
        elif ratio < 0.30:
            low_count += 1
        elif ratio < 0.80:
            healthy_count += 1
        else:
            full_count += 1

    return {
        "avg_fish_energy": sum(fish_energies) / len(fish_list),
        "min_fish_energy": min(fish_energies),
        "max_fish_energy": max(fish_energies),
        "min_max_energy_capacity": min(max_energies),
        "max_max_energy_capacity": max(max_energies),
        "median_max_energy_capacity": median(max_energies),
        "fish_health_critical": critical_count,
        "fish_health_low": low_count,
        "fish_health_healthy": healthy_count,
        "fish_health_full": full_count,
    }
