"""Action/Observation contracts for multi-agent simulation.

This module defines mode-agnostic data structures for the action/observation
pipeline. These contracts are shared across world types (Tank, Soccer, etc.)
and enable external brain integration.

Design Principles:
    - Minimal: Only essential fields, no deep copies of large structures
    - Mode-agnostic: Works for Tank, RCSS, or future world types
    - Extensible: Add fields via Optional or subclassing, not modification
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Observation:
    """Per-agent observation of world state.

    This is a snapshot of what an agent can perceive. In "omniscient" mode,
    this includes full state. Future versions may add noise or FOV limits.

    Attributes:
        entity_id: Unique identifier for this agent (e.g., fish_id as string)
        position: Current (x, y) position in world coordinates
        velocity: Current (vx, vy) velocity
        energy: Current energy level
        max_energy: Maximum energy capacity
        age: Agent age in frames
        nearby_food: List of food observations (position, energy, distance)
        nearby_fish: List of other fish observations
        nearby_threats: List of threat observations (larger fish)
        frame: Current simulation frame
        extra: Mode-specific additional data
    """

    entity_id: str
    position: Tuple[float, float]
    velocity: Tuple[float, float]
    energy: float
    max_energy: float
    age: int
    nearby_food: List[Dict[str, Any]] = field(default_factory=list)
    nearby_fish: List[Dict[str, Any]] = field(default_factory=list)
    nearby_threats: List[Dict[str, Any]] = field(default_factory=list)
    frame: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Action:
    """Per-agent action to apply.

    Actions represent agent decisions that modify world state. The pipeline
    applies these after brain computation and before physics.

    Attributes:
        entity_id: Unique identifier for the agent taking this action
        target_velocity: Desired (vx, vy) velocity for next frame
        extra: Mode-specific additional action data (e.g., dash power for RCSS)
    """

    entity_id: str
    target_velocity: Tuple[float, float] = (0.0, 0.0)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorldTickResult:
    """Result of a single world tick.

    Returned by the action pipeline after processing a step. Contains events,
    metrics, and any additional info for external consumers.

    Attributes:
        events: Significant events that occurred this tick (births, deaths, poker)
        metrics: Aggregate metrics for this tick (entity counts, energy totals)
        info: Additional backend-specific metadata
    """

    events: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    info: Dict[str, Any] = field(default_factory=dict)


# Type aliases for clarity
EntityId = str
ObservationMap = Dict[EntityId, Observation]
ActionMap = Dict[EntityId, Action]
