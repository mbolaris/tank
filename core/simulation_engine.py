"""Backward compatibility re-exports for simulation_engine.

This module re-exports SimulationEngine and HeadlessSimulator from
their new location in core.simulation for backward compatibility.

New code should import from core.simulation directly:
    from core.simulation import SimulationEngine

This file exists to support existing imports:
    from core.simulation_engine import SimulationEngine
"""

# Re-export from new location for backward compatibility
from core.simulation.engine import SimulationEngine, HeadlessSimulator

# Also re-export UpdatePhase and PHASE_DESCRIPTIONS for any code that
# imported them from here
from core.update_phases import PHASE_DESCRIPTIONS, UpdatePhase

# Re-export AgentsWrapper for code that imported it from here
from core.agents_wrapper import AgentsWrapper

__all__ = [
    "SimulationEngine",
    "HeadlessSimulator",
    "UpdatePhase",
    "PHASE_DESCRIPTIONS",
    "AgentsWrapper",
]
