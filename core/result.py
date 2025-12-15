"""Result type for explicit success/failure handling.

This module provides a Result type that makes operation outcomes explicit.
Instead of returning None or raising exceptions, operations return a Result
that must be explicitly checked.

Note: Uses `from __future__ import annotations` for Python 3.7+ compatibility
with generic type aliases.

Why Result Types?
-----------------
Before (implicit failure):
    def find_food(self) -> Optional[Food]:
        food = self.environment.nearby_food(self, 100)
        return food[0] if food else None  # Caller might forget to check!

After (explicit failure):
    def find_food(self) -> Result[Food, str]:
        food = self.environment.nearby_food(self, 100)
        if not food:
            return Err("No food within range")
        return Ok(food[0])

Benefits:
- Compiler/IDE catches unhandled failures
- Error messages are explicit, not hidden
- Code documents what can go wrong
- Easier debugging - errors have context

Usage:
------
    # Creating results
    result = Ok(42)           # Success with value
    result = Err("Not found") # Failure with error message

    # Checking results
    if result.is_ok():
        value = result.unwrap()
    else:
        error = result.error

    # Pattern matching style
    match result:
        case Ok(value):
            print(f"Got {value}")
        case Err(error):
            print(f"Failed: {error}")

    # Chaining operations
    result.map(lambda x: x * 2)  # Transform success value
    result.map_err(lambda e: f"Error: {e}")  # Transform error

    # Safe unwrap with default
    value = result.unwrap_or(default_value)

Design Note:
This is inspired by Rust's Result type, adapted for Python's idioms.
It's not meant to replace all error handling, just make critical
operations more explicit and debuggable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, List, TypeVar, Union, overload

# Type variables for Result
T = TypeVar("T")  # Success value type
E = TypeVar("E")  # Error type
U = TypeVar("U")  # Transformed value type
F = TypeVar("F")  # Transformed error type


@dataclass(frozen=True)
class Ok(Generic[T]):
    """Represents a successful operation result.

    Use this when an operation succeeds and you want to return a value.

    Example:
        def divide(a: int, b: int) -> Result[float, str]:
            if b == 0:
                return Err("Division by zero")
            return Ok(a / b)
    """

    value: T

    def is_ok(self) -> bool:
        """Always returns True for Ok."""
        return True

    def is_err(self) -> bool:
        """Always returns False for Ok."""
        return False

    def unwrap(self) -> T:
        """Get the success value.

        Safe to call on Ok - will always return the value.
        """
        return self.value

    def unwrap_or(self, default: T) -> T:
        """Get the value or a default (always returns value for Ok)."""
        return self.value

    def unwrap_or_else(self, f: Callable[[], T]) -> T:
        """Get the value or compute a default (always returns value for Ok)."""
        return self.value

    @property
    def error(self) -> None:
        """Ok has no error, returns None."""
        return None

    def map(self, f: Callable[[T], U]) -> "Ok[U]":
        """Transform the success value.

        Example:
            Ok(5).map(lambda x: x * 2)  # Ok(10)
        """
        return Ok(f(self.value))

    def map_err(self, f: Callable[[E], F]) -> "Ok[T]":
        """Transform error (no-op for Ok, returns self)."""
        return self

    def and_then(self, f: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        """Chain another Result-returning operation.

        Example:
            Ok(5).and_then(lambda x: Ok(x * 2) if x > 0 else Err("negative"))
        """
        return f(self.value)

    def __repr__(self) -> str:
        return f"Ok({self.value!r})"


@dataclass(frozen=True)
class Err(Generic[E]):
    """Represents a failed operation result.

    Use this when an operation fails and you want to return an error.

    Example:
        def find_entity(id: int) -> Result[Entity, str]:
            if id not in entities:
                return Err(f"Entity {id} not found")
            return Ok(entities[id])
    """

    error: E

    def is_ok(self) -> bool:
        """Always returns False for Err."""
        return False

    def is_err(self) -> bool:
        """Always returns True for Err."""
        return True

    def unwrap(self) -> T:
        """Raises ValueError since Err has no success value.

        Don't call this without checking is_ok() first!
        """
        raise ValueError(f"Called unwrap on Err: {self.error}")

    def unwrap_or(self, default: T) -> T:
        """Get the default value since this is an error."""
        return default

    def unwrap_or_else(self, f: Callable[[], T]) -> T:
        """Compute and return the default value since this is an error."""
        return f()

    @property
    def value(self) -> None:
        """Err has no value, returns None."""
        return None

    def map(self, f: Callable[[T], U]) -> "Err[E]":
        """Transform value (no-op for Err, returns self)."""
        return self

    def map_err(self, f: Callable[[E], F]) -> "Err[F]":
        """Transform the error.

        Example:
            Err("not found").map_err(lambda e: f"Error: {e}")  # Err("Error: not found")
        """
        return Err(f(self.error))

    def and_then(self, f: Callable[[T], "Result[U, E]"]) -> "Err[E]":
        """Chain another operation (no-op for Err, returns self)."""
        return self

    def __repr__(self) -> str:
        return f"Err({self.error!r})"


# Result is a union of Ok and Err
Result = Union[Ok[T], Err[E]]


# ============================================================================
# Helper Functions
# ============================================================================


def try_result(f: Callable[[], T], error_type: type = Exception) -> Result[T, str]:
    """Convert a potentially-raising function to a Result.

    This is useful for wrapping legacy code that uses exceptions.

    Example:
        result = try_result(lambda: int("not a number"))
        # Returns Err("invalid literal for int() with base 10: 'not a number'")

    Args:
        f: A function that might raise an exception
        error_type: The type of exception to catch (default: Exception)

    Returns:
        Ok(value) if f() succeeds, Err(str(exception)) if it raises
    """
    try:
        return Ok(f())
    except error_type as e:
        return Err(str(e))


def collect_results(results: list[Result[T, E]]) -> Result[list[T], E]:
    """Collect a list of Results into a Result of list.

    If all results are Ok, returns Ok with list of values.
    If any result is Err, returns the first Err.

    Example:
        collect_results([Ok(1), Ok(2), Ok(3)])  # Ok([1, 2, 3])
        collect_results([Ok(1), Err("oops"), Ok(3)])  # Err("oops")

    Args:
        results: List of Result objects

    Returns:
        Ok([values]) if all Ok, first Err otherwise
    """
    values: list[T] = []
    for result in results:
        if isinstance(result, Err):
            return result
        values.append(result.value)
    return Ok(values)


# ============================================================================
# Type aliases for common patterns
# ============================================================================

# Operation that might fail with a string message
StringResult = Result[T, str]

# Operation that returns nothing on success but might fail
UnitResult = Result[None, str]


def ok() -> Ok[None]:
    """Create an Ok(None) for operations that succeed with no return value."""
    return Ok(None)


def err(message: str) -> Err[str]:
    """Create an Err with a string message."""
    return Err(message)
