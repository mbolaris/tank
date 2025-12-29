"""Core simulation engine and entity systems.

This package contains the pure simulation logic for the fish tank ecosystem,
with no UI dependencies. Key modules include:

- simulation: Main headless simulation runner (core.simulation.engine)
- ecosystem: Population tracking and statistics
- environment: Spatial queries and grid management
- entities: Fish, Food, Plants, and other entities
- genetics: Genome and trait systems
- algorithms: Behavior algorithms for fish AI
- interfaces: Protocol interfaces for type safety
- poker_participant_manager: Centralized poker state management
- food_spawning_system: Dynamic food spawning with rate adjustment

Design note: this module exposes a small, explicit public API via ``__all__``.
Use direct imports from subpackages for internal helpers to avoid coupling to
the package internals.
"""

from . import algorithms as algorithms
from . import entities as entities
from . import genetics as genetics
from . import interfaces as interfaces
from . import simulation as simulation

# Public API of the core package. Keep this list intentionally small.
__all__ = [
	"algorithms",
	"entities",
	"genetics",
	"interfaces",
	"simulation",
]
