"""Simulation package - Core orchestration components.

This package contains the refactored simulation engine, split into focused modules:

- engine.py: The slim SimulationEngine orchestrator
- entity_manager.py: Entity CRUD and caching
- system_registry.py: System registration and management

The original monolithic SimulationEngine has been decomposed following
the Single Responsibility Principle.

Usage:
    from core.simulation import SimulationEngine

    engine = SimulationEngine(config)
    engine.setup()
    engine.run_headless(max_frames=1000)
"""

from core.simulation.engine import SimulationEngine, HeadlessSimulator
from core.simulation.entity_manager import EntityManager
from core.simulation.system_registry import SystemRegistry

__all__ = [
    "SimulationEngine",
    "HeadlessSimulator",
    "EntityManager",
    "SystemRegistry",
]
