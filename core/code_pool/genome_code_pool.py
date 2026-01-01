"""GenomeCodePool: Genome-centric code pool for evolving agent policies.

This module provides the foundation for "genome = python code pool" where:
- Genomes carry component IDs by policy kind (movement_policy, poker_policy, etc.)
- Mutation can swap to another component of the same kind
- Crossover combines parent component selections
- Safety and determinism are enforced at execution time

The GenomeCodePool wraps a CodePool and provides:
1. Component registration and lookup by kind
2. Safe execution with determinism guarantees
3. Mutation and crossover support for genetic inheritance
4. Default policies for required kinds
"""

from __future__ import annotations

import math
import random as pyrandom
from dataclasses import dataclass, field
from typing import Any, Callable

from .models import ComponentNotFoundError
from .pool import CodePool
from .safety import SafeExecutor, SafetyConfig, SafetyViolationError

# Policy kinds that are considered "required" - genomes should have valid defaults
REQUIRED_POLICY_KINDS: frozenset[str] = frozenset({"movement_policy"})

# Policy kinds that are optional but supported
OPTIONAL_POLICY_KINDS: frozenset[str] = frozenset({"poker_policy", "soccer_policy"})

# All supported policy kinds
ALL_POLICY_KINDS: frozenset[str] = REQUIRED_POLICY_KINDS | OPTIONAL_POLICY_KINDS


@dataclass
class PolicyExecutionResult:
    """Result of executing a policy with safety checks."""

    output: Any
    success: bool
    error_message: str | None = None
    was_clamped: bool = False


@dataclass
class GenomePolicySet:
    """A genome's set of policy component IDs, organized by kind.

    This replaces the old single code_policy_kind/code_policy_component_id/code_policy_params
    approach with a more structured multi-policy system.

    Each policy kind maps to:
    - component_id: The CodePool component ID (or None for no policy)
    - params: Optional tuning parameters for the policy

    Example:
        policies = GenomePolicySet(
            component_ids={"movement_policy": "uuid-123", "poker_policy": "uuid-456"},
            params={"movement_policy": {"aggression": 0.8}}
        )
    """

    component_ids: dict[str, str | None] = field(default_factory=dict)
    params: dict[str, dict[str, float]] = field(default_factory=dict)

    def get_component_id(self, kind: str) -> str | None:
        """Get the component ID for a policy kind."""
        return self.component_ids.get(kind)

    def get_params(self, kind: str) -> dict[str, float]:
        """Get the parameters for a policy kind."""
        return self.params.get(kind, {})

    def set_policy(
        self,
        kind: str,
        component_id: str | None,
        params: dict[str, float] | None = None,
    ) -> None:
        """Set the policy for a given kind."""
        if kind not in ALL_POLICY_KINDS:
            raise ValueError(f"Unknown policy kind: {kind}")
        self.component_ids[kind] = component_id
        if params is not None:
            self.params[kind] = dict(params)
        elif kind in self.params and component_id is None:
            del self.params[kind]

    def has_policy(self, kind: str) -> bool:
        """Check if a policy is set for a kind."""
        return self.component_ids.get(kind) is not None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary."""
        return {
            "component_ids": dict(self.component_ids),
            "params": {k: dict(v) for k, v in self.params.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GenomePolicySet:
        """Deserialize from a dictionary."""
        component_ids = dict(data.get("component_ids", {}))
        params = {k: dict(v) for k, v in data.get("params", {}).items()}
        return cls(component_ids=component_ids, params=params)

    def clone(self) -> GenomePolicySet:
        """Create a deep copy."""
        return GenomePolicySet(
            component_ids=dict(self.component_ids),
            params={k: dict(v) for k, v in self.params.items()},
        )


class GenomeCodePool:
    """A genome-centric wrapper around CodePool for evolving agent policies.

    This class provides:
    1. Component management organized by policy kind
    2. Safe execution with determinism guarantees
    3. Mutation and crossover operations for genetic inheritance
    4. Default policies for required kinds
    """

    def __init__(
        self,
        code_pool: CodePool | None = None,
        safety_config: SafetyConfig | None = None,
    ) -> None:
        """Initialize the GenomeCodePool.

        Args:
            code_pool: Underlying CodePool for component storage (created if None)
            safety_config: Safety configuration for execution (uses defaults if None)
        """
        self._pool = code_pool or CodePool()
        self._safety_config = safety_config or SafetyConfig()
        self._executor = SafeExecutor(self._safety_config)

        # Index: kind -> list of component_ids
        self._components_by_kind: dict[str, list[str]] = {}

        # Default component IDs for required kinds (set via register_default)
        self._defaults: dict[str, str] = {}

        # Rebuild index from existing pool
        self._rebuild_kind_index()

    def _rebuild_kind_index(self) -> None:
        """Rebuild the kind -> component_ids index from the pool."""
        self._components_by_kind.clear()
        for component in self._pool.list_components():
            kind = component.kind
            if kind not in self._components_by_kind:
                self._components_by_kind[kind] = []
            self._components_by_kind[kind].append(component.component_id)

    @property
    def pool(self) -> CodePool:
        """Access the underlying CodePool."""
        return self._pool

    # =========================================================================
    # Component Management
    # =========================================================================

    def add_component(
        self,
        *,
        kind: str,
        name: str,
        source: str,
        entrypoint: str = "policy",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Add a new component to the pool.

        Args:
            kind: Policy kind (e.g., "movement_policy", "poker_policy")
            name: Human-readable name
            source: Python source code
            entrypoint: Function name to call (default: "policy")
            metadata: Optional metadata

        Returns:
            The new component ID
        """
        component_id = self._pool.add_component(
            kind=kind,
            name=name,
            source=source,
            entrypoint=entrypoint,
            metadata=metadata,
        )
        if kind not in self._components_by_kind:
            self._components_by_kind[kind] = []
        self._components_by_kind[kind].append(component_id)
        return component_id

    def register_builtin(
        self,
        component_id: str,
        kind: str,
        func: Callable[..., Any],
    ) -> None:
        """Register a pre-compiled builtin policy.

        Args:
            component_id: Unique identifier for this component
            kind: Policy kind (e.g., "movement_policy")
            func: The callable to register
        """
        self._pool.register(component_id, func)
        if kind not in self._components_by_kind:
            self._components_by_kind[kind] = []
        if component_id not in self._components_by_kind[kind]:
            self._components_by_kind[kind].append(component_id)

    def register_default(self, kind: str, component_id: str) -> None:
        """Register a default component for a policy kind.

        This is used when a genome doesn't have a policy for a required kind.

        Args:
            kind: Policy kind
            component_id: Component ID to use as default
        """
        if kind not in ALL_POLICY_KINDS:
            raise ValueError(f"Unknown policy kind: {kind}")
        # Verify component exists
        if not self.has_component(component_id):
            raise ComponentNotFoundError(f"Component not found: {component_id}")
        self._defaults[kind] = component_id

    def get_default(self, kind: str) -> str | None:
        """Get the default component ID for a policy kind."""
        return self._defaults.get(kind)

    def has_component(self, component_id: str) -> bool:
        """Check if a component exists in the pool."""
        try:
            self._pool.get_component(component_id)
            return True
        except ComponentNotFoundError:
            # Also check registered builtins
            return self._pool.get_callable(component_id) is not None

    def get_components_by_kind(self, kind: str) -> list[str]:
        """Get all component IDs for a given policy kind."""
        return list(self._components_by_kind.get(kind, []))

    def remove_component(self, component_id: str) -> None:
        """Remove a component from the pool."""
        # Find and remove from kind index
        for kind, ids in self._components_by_kind.items():
            if component_id in ids:
                ids.remove(component_id)
                break
        # Remove default if it was this component
        for kind, default_id in list(self._defaults.items()):
            if default_id == component_id:
                del self._defaults[kind]
        try:
            self._pool.remove_component(component_id)
        except ComponentNotFoundError:
            pass  # Already removed or was a builtin

    # =========================================================================
    # Safe Execution
    # =========================================================================

    def execute_policy(
        self,
        component_id: str,
        observation: dict[str, Any],
        rng: pyrandom.Random,
        dt: float = 1.0,
        params: dict[str, float] | None = None,
    ) -> PolicyExecutionResult:
        """Execute a policy with safety checks and determinism guarantees.

        Args:
            component_id: The component to execute
            observation: Observation data for the policy
            rng: Seeded random number generator (for determinism)
            dt: Delta time since last update (for determinism)
            params: Optional policy parameters

        Returns:
            PolicyExecutionResult with output and status
        """
        func = self._pool.get_callable(component_id)
        if func is None:
            return PolicyExecutionResult(
                output=None,
                success=False,
                error_message=f"Component not found: {component_id}",
            )

        # Build execution context with determinism guarantees
        enriched_obs = dict(observation)
        enriched_obs["dt"] = dt
        if params:
            enriched_obs["params"] = dict(params)

        try:
            result = self._executor.execute(func, enriched_obs, rng)
        except SafetyViolationError as exc:
            return PolicyExecutionResult(
                output=None,
                success=False,
                error_message=str(exc),
            )
        except Exception as exc:
            return PolicyExecutionResult(
                output=None,
                success=False,
                error_message=f"Execution error: {exc}",
            )

        return PolicyExecutionResult(
            output=result.output,
            success=result.success,
            error_message=result.error_message,
            was_clamped=result.was_clamped,
        )

    def execute_movement_policy(
        self,
        policy_set: GenomePolicySet,
        observation: dict[str, Any],
        rng: pyrandom.Random,
        dt: float = 1.0,
    ) -> tuple[float, float]:
        """Execute a movement policy and return clamped (vx, vy).

        Args:
            policy_set: The genome's policy set
            observation: Movement observation data
            rng: Seeded RNG for determinism
            dt: Delta time

        Returns:
            Tuple of (vx, vy) normalized and clamped to [-1, 1]
        """
        component_id = policy_set.get_component_id("movement_policy")
        if component_id is None:
            component_id = self._defaults.get("movement_policy")
        if component_id is None:
            return (0.0, 0.0)

        params = policy_set.get_params("movement_policy")
        result = self.execute_policy(component_id, observation, rng, dt, params)

        if not result.success:
            return (0.0, 0.0)

        return self._parse_and_clamp_movement(result.output)

    def _parse_and_clamp_movement(self, output: Any) -> tuple[float, float]:
        """Parse policy output and clamp to valid movement range."""
        # Parse various output formats
        if isinstance(output, (tuple, list)) and len(output) >= 2:
            vx, vy = output[0], output[1]
        elif isinstance(output, dict):
            vx = output.get("vx", output.get("x", 0.0))
            vy = output.get("vy", output.get("y", 0.0))
        elif hasattr(output, "vx") and hasattr(output, "vy"):
            vx, vy = output.vx, output.vy
        elif hasattr(output, "x") and hasattr(output, "y"):
            vx, vy = output.x, output.y
        else:
            return (0.0, 0.0)

        try:
            vx = float(vx)
            vy = float(vy)
        except (TypeError, ValueError):
            return (0.0, 0.0)

        # Check for non-finite values
        if not math.isfinite(vx) or not math.isfinite(vy):
            return (0.0, 0.0)

        # Hard clamp to [-1, 1]
        vx = max(-1.0, min(1.0, vx))
        vy = max(-1.0, min(1.0, vy))

        return (vx, vy)

    # =========================================================================
    # Genetic Operations
    # =========================================================================

    def mutate_policy_set(
        self,
        policy_set: GenomePolicySet,
        rng: pyrandom.Random,
        mutation_rate: float = 0.1,
        param_mutation_strength: float = 0.1,
    ) -> GenomePolicySet:
        """Mutate a genome's policy set.

        Mutation can:
        1. Swap to a different component of the same kind
        2. Drop a policy (set to None)
        3. Mutate policy parameters

        Args:
            policy_set: The policy set to mutate
            rng: Random number generator
            mutation_rate: Probability of mutation per policy
            param_mutation_strength: Gaussian sigma for parameter mutation

        Returns:
            A new mutated GenomePolicySet
        """
        result = policy_set.clone()

        for kind in ALL_POLICY_KINDS:
            if rng.random() >= mutation_rate:
                continue

            current_id = result.get_component_id(kind)
            available = self.get_components_by_kind(kind)

            # Mutation choice: swap, drop, or mutate params
            mutation_choice = rng.random()

            if mutation_choice < 0.05:
                # 5% chance to drop the policy
                result.set_policy(kind, None)
            elif mutation_choice < 0.3 and available:
                # 25% chance to swap to a different component
                new_id = rng.choice(available)
                if new_id != current_id:
                    result.set_policy(kind, new_id, result.get_params(kind))
            else:
                # 70% chance to mutate parameters
                current_params = result.get_params(kind)
                if current_params:
                    mutated_params = self._mutate_params(
                        current_params, rng, param_mutation_strength
                    )
                    result.params[kind] = mutated_params

        return result

    def crossover_policy_sets(
        self,
        parent1: GenomePolicySet,
        parent2: GenomePolicySet,
        rng: pyrandom.Random,
        weight1: float = 0.5,
    ) -> GenomePolicySet:
        """Crossover two parent policy sets to create offspring.

        For each policy kind:
        1. Choose which parent's component to inherit based on weight1
        2. Blend parameters from both parents

        Args:
            parent1: First parent's policy set (typically winner/dominant)
            parent2: Second parent's policy set
            rng: Random number generator
            weight1: Probability of inheriting from parent1

        Returns:
            A new GenomePolicySet combining both parents
        """
        result = GenomePolicySet()

        for kind in ALL_POLICY_KINDS:
            p1_id = parent1.get_component_id(kind)
            p2_id = parent2.get_component_id(kind)

            # Choose which parent's component to inherit
            if p1_id is None and p2_id is None:
                continue
            elif p1_id is None:
                chosen_id = p2_id
            elif p2_id is None:
                chosen_id = p1_id
            else:
                chosen_id = p1_id if rng.random() < weight1 else p2_id

            # Blend parameters from both parents
            p1_params = parent1.get_params(kind)
            p2_params = parent2.get_params(kind)
            blended_params = self._blend_params(p1_params, p2_params, weight1, rng)

            result.set_policy(kind, chosen_id, blended_params)

        return result

    def ensure_valid_policies(
        self,
        policy_set: GenomePolicySet,
        rng: pyrandom.Random,
    ) -> GenomePolicySet:
        """Ensure a policy set has valid policies for all required kinds.

        If a required policy is missing or invalid, uses the default.

        Args:
            policy_set: The policy set to validate
            rng: Random number generator (for default param initialization)

        Returns:
            A validated GenomePolicySet (may be the same object if valid)
        """
        result = policy_set.clone()

        for kind in REQUIRED_POLICY_KINDS:
            component_id = result.get_component_id(kind)

            # Check if current policy is valid
            if component_id is not None and self.has_component(component_id):
                continue

            # Use default if available
            default_id = self._defaults.get(kind)
            if default_id is not None:
                result.set_policy(kind, default_id)
            else:
                # Pick any available component of this kind
                available = self.get_components_by_kind(kind)
                if available:
                    result.set_policy(kind, rng.choice(available))

        return result

    def _mutate_params(
        self,
        params: dict[str, float],
        rng: pyrandom.Random,
        strength: float,
    ) -> dict[str, float]:
        """Mutate policy parameters with Gaussian noise."""
        result = {}
        for key, value in params.items():
            if rng.random() < 0.15:  # 15% chance per parameter
                delta = rng.gauss(0, strength)
                new_value = value + delta
                # Clamp to [-10, 10]
                new_value = max(-10.0, min(10.0, new_value))
                result[key] = new_value
            else:
                result[key] = value
        return result

    def _blend_params(
        self,
        params1: dict[str, float],
        params2: dict[str, float],
        weight1: float,
        rng: pyrandom.Random,
    ) -> dict[str, float]:
        """Blend parameters from two parents."""
        all_keys = set(params1.keys()) | set(params2.keys())
        result = {}
        for key in all_keys:
            v1 = params1.get(key, 0.0)
            v2 = params2.get(key, 0.0)
            # Weighted blend
            blended = weight1 * v1 + (1 - weight1) * v2
            result[key] = blended
        return result

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_dict(self) -> dict[str, Any]:
        """Serialize the GenomeCodePool to a dictionary."""
        return {
            "pool": self._pool.to_dict(),
            "defaults": dict(self._defaults),
            "safety_config": self._safety_config.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GenomeCodePool:
        """Deserialize a GenomeCodePool from a dictionary."""
        pool = CodePool.from_dict(data.get("pool", {}))
        safety_config = SafetyConfig.from_dict(data.get("safety_config", {}))
        instance = cls(code_pool=pool, safety_config=safety_config)
        instance._defaults = dict(data.get("defaults", {}))
        return instance
