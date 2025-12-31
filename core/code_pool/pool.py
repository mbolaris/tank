from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Callable

from .models import (
    CodeComponent,
    CompilationError,
    ComponentNotFoundError,
)
from .sandbox import build_restricted_globals, parse_and_validate


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

    def get_callable(self, component_id: str) -> Callable[..., Any]:
        return self.compile(component_id).func

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
