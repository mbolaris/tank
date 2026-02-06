"""Tank World exception hierarchy.

Centralised base classes so bare ``except Exception`` blocks can be
replaced with narrower catches and failures become easier to diagnose.
"""


class TankError(Exception):
    """Root of all Tank-World domain exceptions."""


class SimulationError(TankError):
    """Errors during simulation execution (engine, systems, entities)."""


class EntityError(SimulationError):
    """An entity-level failure (energy, lifecycle, movement)."""


class GeneticsError(SimulationError):
    """Genome encoding, decoding, or mutation failure."""


class PokerError(TankError):
    """Errors in the poker subsystem."""


class TransferError(TankError):
    """Errors during entity transfer between worlds."""


class PersistenceError(TankError):
    """Errors during save / load / snapshot operations."""


class ConfigurationError(TankError):
    """Invalid or missing configuration."""
