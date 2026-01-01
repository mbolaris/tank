"""Adapter wrapping existing ComposableBehavior as a MovementPolicy.

This module provides adapters that bridge the existing behavior algorithm stack
to the MovementPolicy interface, enabling gradual migration to code-pool-based
policies while maintaining backward compatibility.
"""

from __future__ import annotations

import random as pyrandom
from typing import TYPE_CHECKING, Any, Callable, Optional, Tuple

from core.policies.interfaces import build_movement_observation

if TYPE_CHECKING:
    from core.algorithms.composable.behavior import ComposableBehavior
    from core.entities import Fish


class BehaviorToMovementPolicyAdapter:
    """Wraps an existing ComposableBehavior as a MovementPolicy.
    
    This adapter allows the existing behavior algorithm stack to be used
    through the MovementPolicy interface, enabling a gradual migration
    to code-pool-based policies.
    
    Example:
        >>> behavior = fish.genome.behavioral.behavior.value
        >>> adapter = BehaviorToMovementPolicyAdapter(behavior, fish)
        >>> vx, vy = adapter(observation, rng)
    """
    
    def __init__(
        self,
        behavior: "ComposableBehavior",
        fish: "Fish",
    ):
        """Initialize the adapter.
        
        Args:
            behavior: The composable behavior to wrap
            fish: The fish whose behavior this adapts (needed for execute)
        """
        self._behavior = behavior
        self._fish = fish
    
    @property
    def policy_id(self) -> str:
        """Return a stable identifier for this policy."""
        return f"behavior_adapter:{self._behavior.__class__.__name__}"
    
    def __call__(
        self, observation: dict[str, Any], rng: pyrandom.Random
    ) -> Tuple[float, float]:
        """Execute the wrapped behavior as a MovementPolicy.
        
        Note: The wrapped behavior still uses its internal fish reference,
        but the observation could be used for a future pure-function approach.
        
        Args:
            observation: Observation dict (currently unused, for future compatibility)
            rng: Random number generator (currently unused, behavior uses fish.environment.rng)
            
        Returns:
            Tuple of (vx, vy) velocity components
        """
        return self._behavior.execute(self._fish)


class SimplePolicy:
    """A simple policy that can be defined inline for testing or quick experiments.
    
    This provides an easy way to create policies without subclassing:
    
    Example:
        >>> def chase_food(obs, rng):
        ...     food = obs.get("nearest_food_vector", {"x": 0, "y": 0})
        ...     return (food["x"] * 0.01, food["y"] * 0.01)
        >>> policy = SimplePolicy(chase_food, policy_id="chase_food")
        >>> fish.movement_policy = policy
    """
    
    def __init__(
        self,
        policy_fn: Callable[[dict[str, Any], pyrandom.Random], Tuple[float, float]],
        policy_id: str = "simple_policy",
    ):
        """Initialize the simple policy.
        
        Args:
            policy_fn: A callable that takes (observation, rng) and returns (vx, vy)
            policy_id: A stable identifier for serialization/debugging
        """
        self._policy_fn = policy_fn
        self.policy_id = policy_id
    
    def __call__(
        self, observation: dict[str, Any], rng: pyrandom.Random
    ) -> Tuple[float, float]:
        """Execute the policy function.
        
        Args:
            observation: Observation dict with sensory inputs
            rng: Seeded random number generator
            
        Returns:
            Tuple of (vx, vy) velocity components
        """
        return self._policy_fn(observation, rng)
