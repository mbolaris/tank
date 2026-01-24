"""Runner for executing and validating movement policies from the code pool.

This module provides the specialized logic for running movement policies, checking
their output against the movement contract, and handling failures safely.
"""

from __future__ import annotations

import logging
import math
import random as pyrandom
from typing import TYPE_CHECKING, Any

from core.math_utils import Vector2
from core.policies.interfaces import MovementAction

if TYPE_CHECKING:
    from core.code_pool import GenomeCodePool
    from core.genetics import Genome

logger = logging.getLogger(__name__)

# Output type alias
VelocityComponents = tuple[float, float]

# Deterministic rate limiting for error logs (based on simulation frames, not wall clock)
_ERROR_LOG_INTERVAL_FRAMES = 60
_LAST_ERROR_BUCKET: dict[tuple[int, str, str], int] = {}
_MAX_ERROR_KEYS = 10_000  # Safety cap to prevent unbounded memory growth


def run_movement_policy(
    genome: Genome,
    code_pool: GenomeCodePool,
    observation: dict[str, Any],
    rng: pyrandom.Random,
    fish_id: int | None = None,
) -> VelocityComponents | None:
    """Execute the genome's movement policy and validate output.

    Args:
        genome: The genome containing policy configuration
        code_pool: The code pool system to execute against
        observation: The observation dict (must include 'dt' if needed)
        rng: Random number generator for determinism
        fish_id: Optional ID for logging purposes

    Returns:
        (vx, vy) if successful and valid, None otherwise.
        Values are clamped to [-1.0, 1.0].
    """
    # 1. extract policy config - use per-kind field directly
    movement_id_trait = getattr(genome.behavioral, "movement_policy_id", None)
    movement_params_trait = getattr(genome.behavioral, "movement_policy_params", None)

    # Unwrap values if they are traits
    if movement_id_trait is not None and hasattr(movement_id_trait, "value"):
        component_id = movement_id_trait.value
    else:
        component_id = movement_id_trait

    if movement_params_trait is not None and hasattr(movement_params_trait, "value"):
        params = movement_params_trait.value
    else:
        params = movement_params_trait

    # Identify if we have a valid policy to run
    if not component_id:
        # Not configured for movement code policy
        return None

    # 2. Execute via code pool
    # Note: calculate dt from observation if possible, or default to 1.0
    dt = observation.get("dt", 1.0)

    # We use the generic execute_policy method
    result = code_pool.execute_policy(
        component_id=component_id,
        observation=observation,
        rng=rng,
        dt=dt,
        params=params,
    )

    # Extract frame for rate-limited logging
    frame = _extract_frame(observation)

    if not result.success:
        _log_error(
            fish_id=fish_id,
            component_id=component_id,
            category="execution",
            message=f"Execution failed: {result.error_message}",
            frame=frame,
        )
        return None

    # 3. Validate and Parse Output
    parsed_velocity = _parse_and_validate_output(result.output)

    if parsed_velocity is None:
        _log_error(
            fish_id=fish_id,
            component_id=component_id,
            category="output",
            message=f"Invalid output type: {type(result.output)}",
            frame=frame,
        )
        return None

    return parsed_velocity


def _extract_frame(observation: dict[str, Any]) -> int | None:
    """Extract frame number from observation, if available.

    Uses observation["age"] as the canonical frame counter.
    Returns None if age is not present or not int-coercible.
    """
    age = observation.get("age")
    if age is None:
        return None
    try:
        return int(age)
    except (TypeError, ValueError):
        return None


def _parse_and_validate_output(output: Any) -> VelocityComponents | None:
    """Parse policy output into (vx, vy) and validate.

    Contract:
    - Input: Any object returned by policy
    - Output: (vx, vy) tuple of floats, clamped to [-1.0, 1.0], or None if invalid

    Supported formats:
    - MovementAction(vx, vy)
    - Vector2(x, y)
    - tuple/list [vx, vy]
    - dict {"vx": vx, "vy": vy} or {"x": vx, "y": vy} or {"target_velocity": [vx, vy]}
    """
    vx, vy = 0.0, 0.0

    # Extract raw values
    if isinstance(output, MovementAction):
        vx, vy = output.vx, output.vy
    elif isinstance(output, Vector2):
        vx, vy = output.x, output.y
    elif isinstance(output, (tuple, list)) and len(output) == 2:
        vx, vy = output[0], output[1]
    elif isinstance(output, dict):
        if "vx" in output and "vy" in output:
            vx, vy = output["vx"], output["vy"]
        elif "x" in output and "y" in output:
            vx, vy = output["x"], output["y"]
        elif "target_velocity" in output:
            val = output["target_velocity"]
            if isinstance(val, (list, tuple)) and len(val) == 2:
                vx, vy = val[0], val[1]
            else:
                return None
        else:
            return None
    else:
        return None

    # Convert to float and check for finiteness
    try:
        vx = float(vx)
        vy = float(vy)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(vx) or not math.isfinite(vy):
        return None

    # Clamp to [-1.0, 1.0]
    # We enforce strict clamping for safety
    vx = max(-1.0, min(1.0, vx))
    vy = max(-1.0, min(1.0, vy))

    return vx, vy


def _log_error(
    *,
    fish_id: int | None,
    component_id: str,
    category: str,
    message: str,
    frame: int | None,
) -> None:
    """Log error with deterministic, frame-based rate limiting.

    Rate limits per (fish_id, component_id, category) tuple. Only logs once per
    60-frame bucket when frame is available. If frame is missing, logs every time
    (makes missing metadata obvious).

    Args:
        fish_id: The fish ID (None logs without rate limiting)
        component_id: The policy component ID
        category: Error category (e.g., "execution", "output")
        message: The error message
        frame: Current simulation frame (from observation["age"]), or None
    """
    # If no fish_id, just log it (probably test or debug context)
    if fish_id is None:
        logger.warning(f"Policy {component_id} error: {message}")
        return

    # If no frame available, log every time (makes missing metadata obvious)
    if frame is None:
        logger.warning(f"Movement policy {component_id} error for fish {fish_id}: {message}")
        return

    # Deterministic rate limiting based on frame buckets
    bucket = frame // _ERROR_LOG_INTERVAL_FRAMES
    key = (fish_id, component_id, category)

    # Check if we've already logged in this bucket
    if _LAST_ERROR_BUCKET.get(key) == bucket:
        return  # Already logged this bucket, skip

    # Safety: clear state if it grows too large (simple eviction)
    if len(_LAST_ERROR_BUCKET) >= _MAX_ERROR_KEYS:
        _LAST_ERROR_BUCKET.clear()

    # Record this bucket and log
    _LAST_ERROR_BUCKET[key] = bucket
    logger.warning(f"Movement policy {component_id} error for fish {fish_id}: {message}")


def _reset_error_log_state_for_tests() -> None:
    """Reset module-level error log state. For tests only."""
    _LAST_ERROR_BUCKET.clear()
