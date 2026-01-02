"""Domain-agnostic world interface definitions.

This module defines the core abstractions for multi-agent simulation worlds.
These interfaces are implemented by specific world backends (Tank, Petri, Soccer).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

FAST_STEP_ACTION = "__fast_step__"
# Reserved meta-action key for internal fast stepping (non-gameplay).


@dataclass
class StepResult:
    """Result of a single simulation step.

    This is the canonical output format for all world backends.

    Attributes:
        obs_by_agent: Observations for each agent (agent_id -> observation dict)
        snapshot: Complete world state snapshot for rendering/persistence
        events: List of significant events that occurred this step
        metrics: Aggregate metrics/statistics for this step
        done: Whether the episode/simulation has terminated
        info: Additional backend-specific metadata

    Extended Fields (World Loop Contract):
        spawns: Entity spawn records from this step (optional)
        removals: Entity removal records from this step (optional)
        energy_deltas: Energy transfer records from this step (optional)
        render_hint: Frontend-agnostic rendering metadata (optional)
    """

    obs_by_agent: Dict[str, Any] = field(default_factory=dict)
    snapshot: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    done: bool = False
    info: Dict[str, Any] = field(default_factory=dict)
    # Extended fields for world loop contract (all optional for backward compat)
    spawns: List[Any] = field(default_factory=list)
    removals: List[Any] = field(default_factory=list)
    energy_deltas: List[Any] = field(default_factory=list)
    render_hint: Optional[Dict[str, Any]] = None


class MultiAgentWorldBackend(ABC):
    """Abstract interface for multi-agent simulation worlds.

    This interface is implemented by specific world backends (Tank, Petri, Soccer).
    It provides a consistent API for:
    - Resetting the world with a seed and config
    - Stepping the simulation with agent actions
    - Accessing observations, snapshots, events, and metrics

    The interface is intentionally minimal to support diverse world types.
    """

    @abstractmethod
    def reset(
        self, seed: Optional[int] = None, config: Optional[Dict[str, Any]] = None
    ) -> StepResult:
        """Reset the world to initial state.

        Args:
            seed: Random seed for deterministic initialization
            config: World-specific configuration (e.g., initial population, map layout)

        Returns:
            StepResult with initial observations, snapshot, and metrics
        """
        pass

    @abstractmethod
    def step(self, actions_by_agent: Optional[Dict[str, Any]] = None) -> StepResult:
        """Advance the world by one time step.

        Args:
            actions_by_agent: Actions for each agent (agent_id -> action)
                             May be None/empty for autonomous worlds

        Returns:
            StepResult with observations, snapshot, events, metrics, and done flag
        """
        pass

    @abstractmethod
    def get_current_snapshot(self) -> Dict[str, Any]:
        """Get current world state snapshot without stepping.

        Returns:
            Current world state suitable for rendering/persistence
        """
        pass

    @abstractmethod
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current world metrics/statistics without stepping.

        Returns:
            Current aggregate metrics
        """
        pass

    # =========================================================================
    # Extended protocol methods for world-agnostic backend support
    # =========================================================================

    @property
    @abstractmethod
    def is_paused(self) -> bool:
        """Whether the simulation is paused.

        This provides a world-agnostic way to check pause state without
        the backend needing to know about world.world.paused.
        """
        pass

    @abstractmethod
    def set_paused(self, value: bool) -> None:
        """Set the simulation paused state.

        Args:
            value: True to pause, False to resume
        """
        pass

    @abstractmethod
    def get_entities_for_snapshot(self) -> List[Any]:
        """Get entities for snapshot building.

        This provides a world-agnostic way to access entities without
        the backend needing to know about world.world.entities_list.

        Returns:
            List of entities suitable for snapshot serialization
        """
        pass

    @abstractmethod
    def capture_state_for_save(self) -> Dict[str, Any]:
        """Capture complete world state for persistence.

        Returns:
            Serializable dictionary containing all state needed to restore.
            Returns empty dict if persistence is not supported.
        """
        pass

    @abstractmethod
    def restore_state_from_save(self, state: Dict[str, Any]) -> None:
        """Restore world state from a saved snapshot.

        Args:
            state: Previously captured state dictionary
        """
        pass
