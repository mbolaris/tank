"""No-op world hooks implementation.

This module provides a default no-op hooks class for worlds that don't
need special features.
"""

from typing import Any, Optional


class NoOpWorldHooks:
    """Default no-op hooks for worlds that don't need special features.

    This is the fallback hooks implementation used when a world type
    doesn't have specific hooks defined.
    """

    def supports_command(self, command: str) -> bool:
        """No world-specific commands supported."""
        return False

    def handle_command(self, runner: Any, command: str, data: dict) -> Optional[dict]:
        """No command handling."""
        return None

    def build_world_extras(self, runner: Any) -> dict:
        """No extra state to add."""
        return {}

    def warmup(self, runner: Any) -> None:
        """No warmup needed."""
        pass

    def cleanup(self, runner: Any) -> None:
        """No cleanup needed."""
        pass

    def apply_physics_constraints(self, runner: Any) -> None:
        """No constraints."""
        pass

    def cleanup_physics(self, runner: Any) -> None:
        """No cleanup."""
        pass

    def on_world_type_switch(self, runner: Any, old_type: str, new_type: str) -> None:
        """No action."""
        pass
