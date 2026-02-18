"""Safety infrastructure for code pool execution.

This module provides safety mechanisms to prevent:
1. Overly complex code (AST size limits, source length limits)
2. Unbounded resource consumption (recursion depth, allocation guards)
3. Invalid output values (action magnitude clamping)
4. Non-determinism (explicit RNG requirements)
"""

from __future__ import annotations

import ast
import math
import random as pyrandom
import sys
from dataclasses import dataclass
from typing import Any
from collections.abc import Callable

from .models import ValidationError

# =============================================================================
# Safety Configuration
# =============================================================================


@dataclass
class SafetyConfig:
    """Configuration for code pool safety checks.

    All limits have sensible defaults that balance expressiveness with safety.
    """

    # Source code limits
    max_source_length: int = 10_000  # Maximum source code length in characters
    max_ast_nodes: int = 500  # Maximum number of AST nodes
    max_function_depth: int = 5  # Maximum nesting depth of functions

    # Execution limits
    max_recursion_depth: int = 50  # Maximum recursion depth during execution
    max_output_size: int = 1000  # Maximum size of output data structures

    # Output clamping
    clamp_movement_output: bool = True  # Clamp movement vectors to [-1, 1]
    clamp_value_range: tuple[float, float] = (-1.0, 1.0)  # Range for clamping

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "max_source_length": self.max_source_length,
            "max_ast_nodes": self.max_ast_nodes,
            "max_function_depth": self.max_function_depth,
            "max_recursion_depth": self.max_recursion_depth,
            "max_output_size": self.max_output_size,
            "clamp_movement_output": self.clamp_movement_output,
            "clamp_value_range": list(self.clamp_value_range),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SafetyConfig:
        """Deserialize from dictionary."""
        clamp_range = data.get("clamp_value_range", [-1.0, 1.0])
        return cls(
            max_source_length=data.get("max_source_length", 10_000),
            max_ast_nodes=data.get("max_ast_nodes", 500),
            max_function_depth=data.get("max_function_depth", 5),
            max_recursion_depth=data.get("max_recursion_depth", 50),
            max_output_size=data.get("max_output_size", 1000),
            clamp_movement_output=data.get("clamp_movement_output", True),
            clamp_value_range=tuple(clamp_range[:2]),
        )


# =============================================================================
# Exceptions
# =============================================================================


class SafetyViolationError(Exception):
    """Raised when a safety check fails."""

    pass


class SourceTooLongError(SafetyViolationError):
    """Raised when source code exceeds maximum length."""

    pass


class ASTTooComplexError(SafetyViolationError):
    """Raised when AST exceeds maximum node count."""

    pass


class NestingTooDeepError(SafetyViolationError):
    """Raised when function nesting exceeds maximum depth."""

    pass


class RecursionLimitError(SafetyViolationError):
    """Raised when recursion depth is exceeded during execution."""

    pass


class OutputTooLargeError(SafetyViolationError):
    """Raised when output data structure is too large."""

    pass


# =============================================================================
# AST Complexity Checker
# =============================================================================


class ASTComplexityChecker(ast.NodeVisitor):
    """Check AST complexity against safety limits."""

    def __init__(self, config: SafetyConfig) -> None:
        self.config = config
        self.node_count = 0
        self.max_depth = 0
        self._current_depth = 0

    def check(self, tree: ast.AST) -> None:
        """Check the AST against complexity limits.

        Raises:
            ASTTooComplexError: If AST has too many nodes
            NestingTooDeepError: If function nesting is too deep
        """
        self.node_count = 0
        self.max_depth = 0
        self._current_depth = 0
        self.visit(tree)

        if self.node_count > self.config.max_ast_nodes:
            raise ASTTooComplexError(
                f"AST has {self.node_count} nodes, maximum is {self.config.max_ast_nodes}"
            )

        if self.max_depth > self.config.max_function_depth:
            raise NestingTooDeepError(
                f"Function nesting depth is {self.max_depth}, maximum is {self.config.max_function_depth}"
            )

    def generic_visit(self, node: ast.AST) -> None:
        self.node_count += 1
        super().generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._current_depth += 1
        self.max_depth = max(self.max_depth, self._current_depth)
        self.node_count += 1
        self.generic_visit(node)
        self._current_depth -= 1


def validate_source_safety(source: str, config: SafetyConfig) -> None:
    """Validate source code against safety limits.

    Args:
        source: Python source code to validate
        config: Safety configuration

    Raises:
        SourceTooLongError: If source is too long
        ASTTooComplexError: If AST is too complex
        NestingTooDeepError: If nesting is too deep
        ValidationError: If source has syntax errors or disallowed constructs
    """
    # Import here to avoid circular imports
    from .sandbox import ASTValidator

    # Check source length
    if len(source) > config.max_source_length:
        raise SourceTooLongError(
            f"Source code is {len(source)} characters, maximum is {config.max_source_length}"
        )

    # Parse and check AST complexity
    try:
        tree = ast.parse(source, mode="exec")
    except SyntaxError as exc:
        raise ValidationError(f"Syntax error: {exc.msg}") from exc

    # Validate AST against safety rules (imports, loops, etc.)
    ASTValidator().validate(tree)

    # Check complexity limits
    checker = ASTComplexityChecker(config)
    checker.check(tree)


# =============================================================================
# Safe Executor
# =============================================================================


@dataclass
class ExecutionResult:
    """Result of safe policy execution."""

    output: Any
    success: bool
    error_message: str | None = None
    was_clamped: bool = False


class SafeExecutor:
    """Execute policies with safety guards.

    Safety mechanisms:
    1. Recursion limit enforcement
    2. Output size checking
    3. Output value clamping
    4. Determinism enforcement (explicit RNG)
    """

    def __init__(self, config: SafetyConfig) -> None:
        self.config = config

    def execute(
        self,
        func: Callable[..., Any],
        observation: dict[str, Any],
        rng: pyrandom.Random,
    ) -> ExecutionResult:
        """Execute a policy function with safety guards.

        Args:
            func: The policy function to execute
            observation: Observation data (includes dt for determinism)
            rng: Seeded random number generator

        Returns:
            ExecutionResult with output and status

        Raises:
            SafetyViolationError: If any safety check fails
        """
        # Set recursion limit for this execution
        old_limit = sys.getrecursionlimit()
        try:
            # Use a reduced recursion limit for safety
            # Add buffer for Python internals
            safe_limit = min(self.config.max_recursion_depth + 100, old_limit)
            sys.setrecursionlimit(safe_limit)

            # Execute the policy
            try:
                output = func(observation, rng)
            except RecursionError as exc:
                raise RecursionLimitError(
                    f"Recursion limit exceeded: {self.config.max_recursion_depth}"
                ) from exc

        finally:
            sys.setrecursionlimit(old_limit)

        # Check output size
        self._check_output_size(output)

        # Clamp output if configured
        was_clamped = False
        if self.config.clamp_movement_output:
            output, was_clamped = self._clamp_output(output)

        return ExecutionResult(
            output=output,
            success=True,
            was_clamped=was_clamped,
        )

    def _check_output_size(self, output: Any) -> None:
        """Check that output doesn't exceed size limits."""
        size = self._estimate_size(output, depth=0)
        if size > self.config.max_output_size:
            raise OutputTooLargeError(
                f"Output size {size} exceeds maximum {self.config.max_output_size}"
            )

    def _estimate_size(self, obj: Any, depth: int) -> int:
        """Estimate the size of an object for safety checking."""
        if depth > 10:
            return 1  # Prevent deep recursion in size check

        if obj is None or isinstance(obj, (bool, int, float, str)):
            return 1

        if isinstance(obj, (tuple, list)):
            return 1 + sum(self._estimate_size(item, depth + 1) for item in obj)

        if isinstance(obj, dict):
            size = 1
            for k, v in obj.items():
                size += self._estimate_size(k, depth + 1)
                size += self._estimate_size(v, depth + 1)
            return size

        # Unknown type - count as 1
        return 1

    def _clamp_output(self, output: Any) -> tuple[Any, bool]:
        """Clamp output values to valid range.

        Returns:
            Tuple of (clamped_output, was_clamped)
        """
        min_val, max_val = self.config.clamp_value_range
        was_clamped = False

        if isinstance(output, (tuple, list)):
            clamped_values: list[Any] = []
            for val in output:
                if isinstance(val, (int, float)):
                    if not math.isfinite(val):
                        clamped_values.append(0.0)
                        was_clamped = True
                    elif val < min_val or val > max_val:
                        clamped_values.append(max(min_val, min(max_val, val)))
                        was_clamped = True
                    else:
                        clamped_values.append(val)
                else:
                    clamped_values.append(val)
            return type(output)(clamped_values), was_clamped

        if isinstance(output, dict):
            clamped_map: dict[Any, Any] = {}
            for key, val in output.items():
                if isinstance(val, (int, float)):
                    if not math.isfinite(val):
                        clamped_map[key] = 0.0
                        was_clamped = True
                    elif val < min_val or val > max_val:
                        clamped_map[key] = max(min_val, min(max_val, val))
                        was_clamped = True
                    else:
                        clamped_map[key] = val
                else:
                    clamped_map[key] = val
            return clamped_map, was_clamped

        return output, False


# =============================================================================
# Determinism Utilities
# =============================================================================


def create_deterministic_rng(seed: int) -> pyrandom.Random:
    """Create a deterministic random number generator.

    Args:
        seed: Integer seed for reproducibility

    Returns:
        A seeded Random instance
    """
    return pyrandom.Random(seed)


def fork_rng(rng: pyrandom.Random) -> pyrandom.Random:
    """Fork an RNG to create an independent but deterministic child.

    This is useful when you need to pass an RNG to a sub-computation
    without affecting the parent RNG's state.

    Args:
        rng: Parent RNG

    Returns:
        A new RNG seeded from the parent
    """
    # Generate a seed from the parent RNG
    seed = rng.getrandbits(64)
    return pyrandom.Random(seed)


def validate_rng_determinism(
    func: Callable[..., Any],
    observation: dict[str, Any],
    seed: int,
    num_trials: int = 3,
) -> bool:
    """Validate that a policy function is deterministic with seeded RNG.

    Args:
        func: The policy function to test
        observation: Test observation data
        seed: Seed to use for testing
        num_trials: Number of trials to run

    Returns:
        True if the function produces identical output for identical inputs
    """
    results = []
    for _ in range(num_trials):
        rng = pyrandom.Random(seed)
        try:
            output = func(observation, rng)
            results.append(output)
        except Exception:
            return False

    # Check all results are identical
    if not results:
        return False

    first = results[0]
    return all(result == first for result in results[1:])
