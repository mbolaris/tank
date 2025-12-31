from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from typing import Any, Callable

from .models import (
    CodeComponent,
    CompilationError,
    ComponentNotFoundError,
)
from .sandbox import build_restricted_globals, parse_and_validate

# Builtin component ID for backward compatibility
BUILTIN_SEEK_NEAREST_FOOD_ID = "builtin_seek_nearest_food"


@dataclass(frozen=True)
class CompiledComponent:
    component_id: str
    version: int
    kind: str
    entrypoint: str
    func: Callable[..., Any]


class CodePool:
    def __init__(self, components: dict[str, CodeComponent] | None = None) -> None:
        self._components: dict[str, CodeComponent] = dict(components or {})
        self._compiled: dict[tuple[str, int], CompiledComponent] = {}

    def register(self, component_id: str, func: Callable[..., Any]) -> None:
        """Register a pre-compiled callable directly (for builtins).

        This bypasses validation and compilation since the function is already
        a trusted Python callable. Useful for builtin policies like
        seek_nearest_food that don't need sandboxing.

        Args:
            component_id: Unique identifier for this component
            func: The callable to register
        """
        compiled = CompiledComponent(
            component_id=component_id,
            version=1,
            kind="builtin",
            entrypoint="policy",
            func=func,
        )
        self._compiled[(component_id, 1)] = compiled

    def add_component(
        self,
        *,
        kind: str,
        name: str,
        source: str,
        entrypoint: str = "policy",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        component_id = str(uuid.uuid4())
        component = CodeComponent(
            component_id=component_id,
            kind=kind,
            name=name,
            source=source,
            entrypoint=entrypoint,
            version=1,
            metadata=dict(metadata or {}),
        )
        self._components[component_id] = component
        return component_id

    def remove_component(self, component_id: str) -> None:
        if component_id not in self._components:
            raise ComponentNotFoundError(f"Component not found: {component_id}")
        del self._components[component_id]
        self._compiled = {
            key: value for key, value in self._compiled.items() if key[0] != component_id
        }

    def list_components(self) -> list[CodeComponent]:
        return list(self._components.values())

    def get_component(self, component_id: str) -> CodeComponent:
        try:
            return self._components[component_id]
        except KeyError as exc:
            raise ComponentNotFoundError(f"Component not found: {component_id}") from exc

    def _compile_component(self, component: CodeComponent) -> CompiledComponent:
        tree = parse_and_validate(component.source)
        code = compile(tree, f"code_pool:{component.component_id}", "exec")
        exec_globals = build_restricted_globals()
        exec_locals: dict[str, Any] = {}
        try:
            exec(code, exec_globals, exec_locals)
        except Exception as exc:
            raise CompilationError(f"Execution failed: {exc}") from exc

        func = exec_locals.get(component.entrypoint) or exec_globals.get(component.entrypoint)
        if not callable(func):
            raise CompilationError(f"Entrypoint '{component.entrypoint}' not found or not callable")

        return CompiledComponent(
            component_id=component.component_id,
            version=component.version,
            kind=component.kind,
            entrypoint=component.entrypoint,
            func=func,
        )

    def compile(self, component_id: str) -> CompiledComponent:
        component = self.get_component(component_id)
        cache_key = (component_id, component.version)
        cached = self._compiled.get(cache_key)
        if cached is not None:
            return cached
        compiled = self._compile_component(component)
        self._compiled[cache_key] = compiled
        return compiled

    def get_callable(self, component_id: str) -> Callable[..., Any] | None:
        """Get the callable for a component by ID.

        This handles both registered builtins (which are cached directly)
        and source-based components (which require compilation).

        Args:
            component_id: The component ID to look up

        Returns:
            The callable function, or None if not found
        """
        # Check for registered builtin first
        cached = self._compiled.get((component_id, 1))
        if cached is not None:
            return cached.func

        # Try to compile from source
        if component_id in self._components:
            return self.compile(component_id).func

        return None

    def to_dict(self) -> dict[str, Any]:
        components = [component.to_dict() for component in self._components.values()]
        components.sort(key=lambda item: item["component_id"])
        return {"components": components}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CodePool:
        components_data = data.get("components", [])
        components = {
            entry["component_id"]: CodeComponent.from_dict(entry) for entry in components_data
        }
        return cls(components=components)


# =============================================================================
# Builtin Policies
# =============================================================================


def seek_nearest_food_policy(observation: dict[str, Any], rng: Any) -> tuple[float, float]:
    """Simple built-in movement policy that heads toward the nearest food vector.

    Args:
        observation: Dictionary containing fish sensor data including 'nearest_food_vector'
        rng: Random number generator (unused but required for policy signature)

    Returns:
        Tuple of (vx, vy) normalized direction toward nearest food, or (0, 0) if no food
    """
    _ = rng
    food_vector = observation.get("nearest_food_vector")
    if isinstance(food_vector, dict):
        try:
            dx = float(food_vector.get("x", 0.0))
            dy = float(food_vector.get("y", 0.0))
        except (TypeError, ValueError):
            dx = 0.0
            dy = 0.0
        length_sq = dx * dx + dy * dy
        if length_sq > 0:
            length = math.sqrt(length_sq)
            return (dx / length, dy / length)
    return (0.0, 0.0)

