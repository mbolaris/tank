"""Domain-agnostic world abstraction layer.

This package provides a generic multi-agent world interface that can be
implemented by different simulation environments (Tank, Petri, Soccer, etc.).
"""

from core.worlds.interfaces import MultiAgentWorldBackend, StepResult
from core.worlds.registry import WorldRegistry

__all__ = ["MultiAgentWorldBackend", "StepResult", "WorldRegistry"]
