"""Observation builder registry for world-agnostic policy observations.

This module provides a registry pattern for building policy observations
that are specific to each world type (Tank, Petri, Soccer, etc.) without
coupling the core policy interface to any single world's entities.

Usage:
    # In world-specific module (e.g., core/worlds/tank/movement_observations.py):
    from core.policies.observation_registry import register_observation_builder

    class TankMovementObservationBuilder:
        def build(self, agent, env) -> dict: ...

    register_observation_builder("tank", "movement", TankMovementObservationBuilder())

    # In policy code:
    from core.policies.observation_registry import build_observation

    obs = build_observation("tank", "movement", fish, env)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Protocol

if TYPE_CHECKING:
    pass

Observation = Dict[str, Any]


class ObservationBuilder(Protocol):
    """Protocol for world-specific observation builders.

    Each world implements this protocol for each policy kind (movement, soccer, etc.)
    to build observations appropriate for that world's entities and mechanics.
    """

    def build(self, agent: Any, env: Any) -> Observation:
        """Build an observation dict for the given agent in the environment.

        Args:
            agent: The agent requesting an observation (e.g., Fish, SoccerPlayer)
            env: The environment/world context

        Returns:
            Observation dict with policy-kind-specific keys
        """
        ...


# Registry storage: {(world_type, policy_kind): builder}
_OBSERVATION_BUILDERS: Dict[tuple[str, str], ObservationBuilder] = {}


def register_observation_builder(
    world_type: str,
    policy_kind: str,
    builder: ObservationBuilder,
) -> None:
    """Register an observation builder for a world type and policy kind.

    Args:
        world_type: World identifier (e.g., "tank", "petri", "soccer")
        policy_kind: Policy kind (e.g., "movement", "soccer", "poker")
        builder: ObservationBuilder instance
    """
    key = (world_type, policy_kind)
    existing = _OBSERVATION_BUILDERS.get(key)
    # Idempotent: skip if same builder type is already registered
    if existing is not None and type(existing).__name__ == type(builder).__name__:
        return
    _OBSERVATION_BUILDERS[key] = builder


def get_observation_builder(
    world_type: str,
    policy_kind: str,
) -> ObservationBuilder | None:
    """Get a registered observation builder.

    Args:
        world_type: World identifier
        policy_kind: Policy kind

    Returns:
        Registered builder or None if not found
    """
    return _OBSERVATION_BUILDERS.get((world_type, policy_kind))


def build_observation(
    world_type: str,
    policy_kind: str,
    agent: Any,
    env: Any,
) -> Observation:
    """Build an observation using the registered builder.

    Args:
        world_type: World identifier (e.g., "tank", "petri", "soccer")
        policy_kind: Policy kind (e.g., "movement")
        agent: The agent requesting observation
        env: The environment context

    Returns:
        Observation dict from the registered builder

    Raises:
        ValueError: If no builder is registered for the world_type/policy_kind
    """
    builder = get_observation_builder(world_type, policy_kind)
    if builder is None:
        raise ValueError(
            f"No observation builder registered for world_type='{world_type}', "
            f"policy_kind='{policy_kind}'. "
            f"Available: {list(_OBSERVATION_BUILDERS.keys())}"
        )
    return builder.build(agent, env)


def list_registered_builders() -> list[tuple[str, str]]:
    """List all registered (world_type, policy_kind) pairs.

    Returns:
        List of (world_type, policy_kind) tuples
    """
    return list(_OBSERVATION_BUILDERS.keys())


def clear_registry() -> None:
    """Clear all registered observation builders.

    WARNING: Use this ONLY in tests to reset state.
    """
    _OBSERVATION_BUILDERS.clear()


def snapshot_registry() -> Dict[tuple[str, str], ObservationBuilder]:
    """Return a shallow copy of the current registry.

    Use this to capture the registry state before tests that clear it.
    """
    return dict(_OBSERVATION_BUILDERS)


def restore_registry(snapshot: Dict[tuple[str, str], ObservationBuilder]) -> None:
    """Restore the registry from a snapshot.

    Clears the current registry and restores all entries from the snapshot.
    Use in tearDown() to prevent test pollution.
    """
    _OBSERVATION_BUILDERS.clear()
    _OBSERVATION_BUILDERS.update(snapshot)
