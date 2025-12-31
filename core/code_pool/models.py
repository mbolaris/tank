"""Data models and error types for the Python code pool."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class CodePoolError(Exception):
    """Base error for code pool failures."""


class ComponentNotFoundError(CodePoolError):
    """Raised when a component ID is missing."""


class ValidationError(CodePoolError):
    """Raised when source code violates sandbox rules."""


class CompilationError(CodePoolError):
    """Raised when compilation or entrypoint resolution fails."""


@dataclass(frozen=True)
class CodeComponent:
    """Immutable description of a compiled Python component."""

    component_id: str
    kind: str
    name: str
    source: str
    entrypoint: str
    version: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "kind": self.kind,
            "name": self.name,
            "source": self.source,
            "entrypoint": self.entrypoint,
            "version": self.version,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CodeComponent":
        metadata = data.get("metadata") or {}
        return cls(
            component_id=data["component_id"],
            kind=data["kind"],
            name=data["name"],
            source=data["source"],
            entrypoint=data["entrypoint"],
            version=data["version"],
            metadata=dict(metadata),
        )
