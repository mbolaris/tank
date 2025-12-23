"""Lightweight simulation configuration helpers."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SimulationConfig:
    """Configuration toggles for simulation runtime behavior.

    Attributes:
        headless: Whether to run without UI dependencies.
        trace_mode: Enable detailed tracing via DebugTraceSink.
        trace_output: Optional JSON path for persisted traces.
    """

    headless: bool = True
    trace_mode: bool = False
    trace_output: Optional[str] = None

    def enable_tracing(self, output_path: Optional[str] = None) -> None:
        """Enable trace mode and optionally set an output path."""
        self.trace_mode = True
        if output_path:
            self.trace_output = output_path
