"""World loop contracts for multi-world simulation support.

This module defines canonical types and protocols for the world loop contract.
All world backends (Tank, Petri, Soccer) implement these contracts to share
one engine core while maintaining distinct behavior.

Design Principles:
    - Extend existing MultiAgentWorldBackend, don't replace
    - Keep interfaces minimal and testable
    - Use Literal for type-safe world identification
    - RenderHint enables frontend-agnostic rendering

See docs/WORLDS.md for contract documentation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Literal, Protocol

if TYPE_CHECKING:
    from core.worlds.interfaces import StepResult

# =============================================================================
# World Type Definition
# =============================================================================

WorldType = Literal["tank", "petri", "soccer", "soccer_training"]
"""Canonical world type identifier.

This is the single source of truth for valid world types.
Use this instead of string literals throughout the codebase.
"""

ALL_WORLD_TYPES: tuple[str, ...] = ("tank", "petri", "soccer", "soccer_training")
"""Tuple of all valid world types for iteration and validation."""


def is_valid_world_type(world_type: str) -> bool:
    """Check if a string is a valid world type."""
    return world_type in ALL_WORLD_TYPES


# =============================================================================
# Render Hint
# =============================================================================


@dataclass
class RenderHint:
    """Frontend-agnostic rendering metadata.

    This dataclass provides hints to the frontend about how to render
    a world without coupling the backend to specific rendering code.

    Attributes:
        style: View style ("side" for aquarium view, "topdown" for petri/soccer)
        entity_style: Entity visual style hint (e.g., "fish", "microbe", "player")
        camera: Optional camera configuration (zoom, center, etc.)
        extra: Extension point for world-specific rendering hints
    """

    style: Literal["side", "topdown"] = "side"
    entity_style: str | None = None
    camera: Dict[str, Any] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "style": self.style,
            "entity_style": self.entity_style,
            "camera": self.camera,
            **self.extra,
        }


# Pre-defined render hints for built-in world types
TANK_RENDER_HINT = RenderHint(style="side", entity_style="fish")
PETRI_RENDER_HINT = RenderHint(style="topdown", entity_style="microbe")
SOCCER_RENDER_HINT = RenderHint(style="topdown", entity_style="player")
SOCCER_TRAINING_RENDER_HINT = RenderHint(style="topdown", entity_style="player")


def get_default_render_hint(world_type: str) -> RenderHint:
    """Get the default render hint for a world type."""
    hints = {
        "tank": TANK_RENDER_HINT,
        "petri": PETRI_RENDER_HINT,
        "soccer": SOCCER_RENDER_HINT,
        "soccer_training": SOCCER_TRAINING_RENDER_HINT,
    }
    return hints.get(world_type, TANK_RENDER_HINT)


# =============================================================================
# World Loop Protocol
# =============================================================================


class WorldLoop(Protocol):
    """Minimal protocol for world loop implementations.

    This protocol defines the core contract that all world backends must
    implement. It's intentionally minimal to support diverse world types.

    Note: This extends the existing MultiAgentWorldBackend ABC conceptually.
    Backends should inherit from MultiAgentWorldBackend and also satisfy
    this protocol through duck typing.
    """

    @property
    def world_type(self) -> WorldType:
        """The world type identifier for this backend."""
        ...

    def reset(
        self,
        seed: int | None = None,
        config: Dict[str, Any] | None = None,
    ) -> "StepResult":
        """Reset the world to initial state.

        Args:
            seed: Random seed for deterministic initialization
            config: World-specific configuration

        Returns:
            StepResult with initial observations, snapshot, and metrics
        """
        ...

    def step(
        self,
        actions: Dict[str, Any] | None = None,
    ) -> "StepResult":
        """Advance the world by one time step.

        Args:
            actions: Actions for each agent (agent_id -> action)

        Returns:
            StepResult with observations, snapshot, events, metrics
        """
        ...


# =============================================================================
# Extended Step Result Fields (Type Definitions)
# =============================================================================

# These type aliases document the expected structure for extended StepResult fields


@dataclass
class SpawnRequest:
    """Record of an entity spawn request.

    Used to track spawns that occurred during a step for debugging/logging.
    """

    entity_type: str
    entity_id: str | None = None
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RemovalRequest:
    """Record of an entity removal request.

    Used to track removals that occurred during a step for debugging/logging.
    """

    entity_type: str
    entity_id: str
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EnergyDeltaRecord:
    """Record of an energy transfer for the ledger.

    Used to track energy changes that occurred during a step.
    """

    entity_id: str
    stable_id: str | None = None
    entity_type: str | None = None
    delta: float = 0.0
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
