"""Domain-agnostic world interface definitions.

This module defines the core abstractions for multi-agent simulation worlds.
These interfaces are implemented by specific world backends (Tank, Petri, Soccer).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


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
    """

    obs_by_agent: Dict[str, Any] = field(default_factory=dict)
    snapshot: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    done: bool = False
    info: Dict[str, Any] = field(default_factory=dict)


class MultiAgentWorldBackend(ABC):
    """Abstract interface for multi-agent simulation worlds.

    This interface is implemented by specific world backends (Tank, Petri, Soccer).
    It provides a consistent API for:
    - Resetting the world with a seed and scenario
    - Stepping the simulation with agent actions
    - Accessing observations, snapshots, events, and metrics

    The interface is intentionally minimal to support diverse world types.
    """

    @abstractmethod
    def reset(
        self, seed: Optional[int] = None, scenario: Optional[Dict[str, Any]] = None
    ) -> StepResult:
        """Reset the world to initial state.

        Args:
            seed: Random seed for deterministic initialization
            scenario: World-specific configuration (e.g., initial population, map layout)

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
