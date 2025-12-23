"""Lightweight simulation configuration helpers."""

from dataclasses import dataclass, field
from typing import Optional

from core.config.display import FRAME_RATE, SCREEN_HEIGHT, SCREEN_WIDTH, SEPARATOR_WIDTH
from core.config.ecosystem import (
    CRITICAL_POPULATION_THRESHOLD,
    EMERGENCY_SPAWN_COOLDOWN,
    MAX_POPULATION,
    SPAWN_MARGIN_PIXELS,
)


@dataclass
class DisplayConfig:
    """Minimal display configuration for headless runs."""

    screen_width: int = SCREEN_WIDTH
    screen_height: int = SCREEN_HEIGHT
    separator_width: int = SEPARATOR_WIDTH
    frame_rate: int = FRAME_RATE


@dataclass
class EcosystemConfig:
    """Population-related ecosystem configuration."""

    max_population: int = MAX_POPULATION
    critical_population_threshold: int = CRITICAL_POPULATION_THRESHOLD
    emergency_spawn_cooldown: int = EMERGENCY_SPAWN_COOLDOWN
    spawn_margin_pixels: int = SPAWN_MARGIN_PIXELS


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
    display: DisplayConfig = field(default_factory=DisplayConfig)
    ecosystem: EcosystemConfig = field(default_factory=EcosystemConfig)

    def enable_tracing(self, output_path: Optional[str] = None) -> None:
        """Enable trace mode and optionally set an output path."""
        self.trace_mode = True
        if output_path:
            self.trace_output = output_path
