"""Simulation systems package.

This package contains all systems that operate on the simulation.
Each system has a single responsibility and follows the BaseSystem contract.

Systems vs Components:
- Components store data and state (e.g., EnergyComponent stores energy)
- Systems contain logic and operate on entities (e.g., CollisionSystem detects collisions)

Usage:
    from core.systems import BaseSystem, System

    class MySystem(BaseSystem):
        def _do_update(self, frame: int) -> None:
            # System logic here
            pass

Available Systems:
- FoodSpawningSystem: Handles automatic food spawning based on ecosystem needs
- CollisionSystem: (in collision_system.py) Handles collision detection and response

Future Systems to Extract from SimulationEngine:
- EmergencySpawnSystem: Handle emergency fish spawning
- PlantPropagationSystem: Handle plant reproduction/sprouting
- EntityCleanupSystem: Handle removing dead/expired entities
"""

from core.systems.base import BaseSystem, System
from core.systems.food_spawning import FoodSpawningSystem, SpawnRateConfig

__all__ = ["BaseSystem", "System", "FoodSpawningSystem", "SpawnRateConfig"]
