"""RNG utilities for deterministic simulation.

This module provides utilities for accessing RNGs in a way that
fails loudly if a deterministic RNG is not available, rather than
silently creating an unseeded fallback.
"""

import random
from typing import Any, Optional


class MissingRNGError(RuntimeError):
    """Raised when an RNG is required but not available.
    
    This error indicates a bug in the simulation setup - all entities
    should have access to the engine's RNG via their environment.
    """
    pass


def require_rng(environment: Any, context: str = "unknown") -> random.Random:
    """Get the RNG from an environment, failing loudly if unavailable.
    
    Use this instead of `getattr(env, "rng", None) or random.Random()`
    to ensure determinism - we want to know immediately if RNG access
    fails rather than silently creating non-deterministic behavior.
    
    Args:
        environment: The environment object that should have an `rng` property
        context: Description of where this is called from (for error messages)
        
    Returns:
        The environment's RNG
        
    Raises:
        MissingRNGError: If environment is None or doesn't have an RNG
        
    Example:
        rng = require_rng(self.environment, "Fish.reproduce")
        offspring_x = rng.uniform(-10, 10)
    """
    if environment is None:
        raise MissingRNGError(
            f"Cannot get RNG: environment is None (context: {context}). "
            "This entity may not have been properly initialized with an environment."
        )
    
    rng = getattr(environment, "rng", None)
    if rng is None:
        raise MissingRNGError(
            f"Cannot get RNG: environment has no 'rng' attribute (context: {context}). "
            "The environment should be a World with a deterministic RNG."
        )
    
    return rng


def require_rng_param(rng: Optional[random.Random], context: str) -> random.Random:
    """Validate that an RNG parameter was provided, failing loudly if not.
    
    Use this in constructors and methods that require an RNG to be passed in,
    instead of silently creating an unseeded fallback.
    
    Args:
        rng: The RNG that should have been provided
        context: Description of where this is called from (for error messages)
        
    Returns:
        The validated RNG
        
    Raises:
        MissingRNGError: If rng is None
        
    Example:
        def __init__(self, rng: Optional[random.Random] = None):
            _rng = require_rng_param(rng, "AggressiveHunter.__init__")
            self.parameters = {"speed": _rng.uniform(1.0, 2.0)}
    """
    if rng is None:
        raise MissingRNGError(
            f"RNG required: {context}. Pass engine/environment RNG explicitly."
        )
    return rng


def get_rng_or_default(
    environment: Any,
    fallback_rng: Optional[random.Random] = None,
    context: str = "unknown",
) -> random.Random:
    """Get environment RNG, with explicit fallback for non-simulation contexts.
    
    This is for code paths that may run outside of simulation (tests, utilities)
    where an RNG might not be available. Use require_rng() for core simulation code.
    
    Args:
        environment: The environment object (can be None)
        fallback_rng: Explicit fallback RNG to use (must be provided, not created)
        context: Description of where this is called from
        
    Returns:
        The environment's RNG, or the fallback if provided
        
    Raises:
        MissingRNGError: If environment has no RNG and no fallback was provided
    """
    if environment is not None:
        rng = getattr(environment, "rng", None)
        if rng is not None:
            return rng
    
    if fallback_rng is not None:
        return fallback_rng
    
    raise MissingRNGError(
        f"Cannot get RNG: environment is None/has no rng and no fallback provided "
        f"(context: {context}). Pass an explicit fallback_rng for non-simulation code."
    )
