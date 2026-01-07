"""Legacy tank_world module - deprecated.

This package provides migration support for code that directly imports
from core.tank_world. New code should use core.worlds.WorldRegistry instead.
"""

import warnings

warnings.warn(
    "core.legacy.tank_world is deprecated. Use core.worlds.WorldRegistry instead. "
    "This module will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export for backward compatibility
from core.legacy.tank_world import TankWorld

__all__ = ["TankWorld"]
