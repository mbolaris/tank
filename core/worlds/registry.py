"""World registry for creating multi-agent world backends.

This module provides a central registry for instantiating different world types.
Currently supports:
- "tank": Fish tank ecosystem simulation
- "petri": Petri dish simulation (not yet implemented)
- "soccer": Soccer game simulation (not yet implemented)
"""

from typing import Any, Dict, Optional

from core.worlds.interfaces import MultiAgentWorldBackend


class WorldRegistry:
    """Registry for creating multi-agent world backends.

    This class provides a factory method for instantiating different world types
    by name. Each world type is implemented as a separate backend adapter.

    Example:
        >>> registry = WorldRegistry()
        >>> world = registry.create_world("tank", seed=42, max_population=100)
        >>> result = world.reset(seed=42)
        >>> result = world.step()
    """

    @staticmethod
    def create_world(world_type: str, **kwargs) -> MultiAgentWorldBackend:
        """Create a world backend of the specified type.

        Args:
            world_type: Type of world to create ("tank", "petri", "soccer")
            **kwargs: World-specific configuration parameters

        Returns:
            Initialized world backend instance

        Raises:
            ValueError: If world_type is unknown
            NotImplementedError: If world_type is not yet implemented
        """
        if world_type == "tank":
            from core.worlds.tank.backend import TankWorldBackendAdapter

            return TankWorldBackendAdapter(**kwargs)

        elif world_type == "petri":
            raise NotImplementedError(
                "Petri world backend not yet implemented. "
                "This will be added in a future agent's work."
            )

        elif world_type == "soccer":
            raise NotImplementedError(
                "Soccer world backend not yet implemented. "
                "This will be added in a future agent's work."
            )

        else:
            raise ValueError(
                f"Unknown world type: {world_type}. "
                f"Supported types: 'tank', 'petri' (not implemented), 'soccer' (not implemented)"
            )

    @staticmethod
    def list_world_types() -> Dict[str, str]:
        """List all available world types and their status.

        Returns:
            Dictionary mapping world type name to implementation status
        """
        return {
            "tank": "implemented",
            "petri": "not_implemented",
            "soccer": "not_implemented",
        }
