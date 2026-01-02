"""Utilities for working with enums."""


def coerce_enum(enum_cls, value, default: int = 0):
    """Coerce a value to an enum instance.

    Handles multiple input types:
    - Enum instances are returned as-is
    - Integers are treated as enum indices
    - String values are parsed as integers
    - Out-of-range values wrap around using modulo
    - Invalid values fall back to the default

    Args:
        enum_cls: The Enum class to coerce to
        value: The value to coerce
        default: The default index to use if coercion fails (default: 0)

    Returns:
        An instance of enum_cls
    """
    try:
        return enum_cls(value)
    except (TypeError, ValueError):
        try:
            index = int(value)
        except (TypeError, ValueError):
            index = default
        size = len(enum_cls)
        if size <= 0:
            return enum_cls(default)
        return enum_cls(index % size)
