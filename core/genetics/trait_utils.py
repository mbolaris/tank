"""Utility functions for working with genetic traits.

This module provides helpers for safely extracting values from GeneticTrait
objects, centralizing the null-safety patterns used throughout the genetics
system.

Design Philosophy:
    Trait values are wrapped in GeneticTrait[T] for meta-genetic properties.
    This wrapping means we often need to safely extract the inner value,
    handling cases where the trait or its value might be None.

    Instead of repeating this pattern everywhere:
        if physical.fin_size is None or getattr(physical.fin_size, "value", None) is None:
            return default
        val = physical.fin_size.value

    We provide a clean helper:
        val = get_trait_value(physical.fin_size, default=1.0)
"""

from typing import Any, Optional, TypeVar, overload

T = TypeVar("T")


@overload
def get_trait_value(trait: Any, default: T) -> T:
    ...


@overload
def get_trait_value(trait: Any) -> Optional[Any]:
    ...


def get_trait_value(trait: Any, default: Any = None) -> Any:
    """Safely extract the value from a GeneticTrait, with optional default.

    This handles the common pattern of accessing trait.value while guarding
    against None traits or traits with None values.

    Args:
        trait: A GeneticTrait instance, or None
        default: Value to return if trait or trait.value is None

    Returns:
        The trait's value if available, otherwise the default

    Examples:
        >>> from core.genetics.trait import GeneticTrait
        >>> get_trait_value(GeneticTrait(1.5), default=1.0)
        1.5
        >>> get_trait_value(None, default=1.0)
        1.0
        >>> get_trait_value(GeneticTrait(None), default=1.0)
        1.0
    """
    if trait is None:
        return default

    # Use getattr to gracefully handle objects without .value attribute
    value = getattr(trait, "value", None)

    if value is None:
        return default

    return value


def has_trait_value(trait: Any) -> bool:
    """Check if a trait has a valid (non-None) value.

    Args:
        trait: A GeneticTrait instance, or None

    Returns:
        True if trait exists and has a non-None value

    Example:
        >>> has_trait_value(GeneticTrait(1.5))
        True
        >>> has_trait_value(None)
        False
        >>> has_trait_value(GeneticTrait(None))
        False
    """
    if trait is None:
        return False
    return getattr(trait, "value", None) is not None
