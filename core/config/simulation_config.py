"""Aggregate simulation configuration dataclasses.

This module centralizes configuration that was previously scattered across
multiple modules. The ``SimulationConfig`` dataclass groups ecosystem,
display, server, poker, and food parameters so experiments can be reproduced
with a single object.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, replace

from core.config.display import (
    FILES,
    FRAME_RATE,
    INIT_POS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SEPARATOR_WIDTH,
)
from core.config.ecosystem import (
    CRITICAL_POPULATION_THRESHOLD,
    EMERGENCY_SPAWN_COOLDOWN,
    MAX_POPULATION,
    NUM_SCHOOLING_FISH,
    SPAWN_MARGIN_PIXELS,
    TOTAL_ALGORITHM_COUNT,
    TOTAL_SPECIES_COUNT,
)
from core.config.food import (
    AUTO_FOOD_ENABLED,
    AUTO_FOOD_HIGH_ENERGY_THRESHOLD_1,
    AUTO_FOOD_HIGH_ENERGY_THRESHOLD_2,
    AUTO_FOOD_HIGH_POP_THRESHOLD_1,
    AUTO_FOOD_HIGH_POP_THRESHOLD_2,
    AUTO_FOOD_LOW_ENERGY_THRESHOLD,
    AUTO_FOOD_SPAWN_RATE,
    AUTO_FOOD_ULTRA_LOW_ENERGY_THRESHOLD,
    LIVE_FOOD_SPAWN_CHANCE,
)
from core.config.plants import PLANT_MIN_ENERGY_GAIN
from core.config.poker import MAX_POKER_EVENTS, POKER_EVENT_MAX_AGE_FRAMES
from core.config.server import DEFAULT_API_PORT, PLANTS_ENABLED, POKER_ACTIVITY_ENABLED
from core.poker.evaluation.benchmark_eval import BenchmarkEvalConfig


@dataclass
class PlantConfig:
    """Configuration for plant energy and growth."""

    # Minimum energy gain per frame - adjustable at runtime by user
    plant_energy_input_rate: float = PLANT_MIN_ENERGY_GAIN


@dataclass
class EcosystemConfig:
    """Configuration for population dynamics and spawning."""

    max_population: int = MAX_POPULATION
    num_schooling_fish: int = NUM_SCHOOLING_FISH
    critical_population_threshold: int = CRITICAL_POPULATION_THRESHOLD
    emergency_spawn_cooldown: int = EMERGENCY_SPAWN_COOLDOWN
    spawn_margin_pixels: int = SPAWN_MARGIN_PIXELS
    total_algorithm_count: int = TOTAL_ALGORITHM_COUNT
    total_species_count: int = TOTAL_SPECIES_COUNT


@dataclass
class DisplayConfig:
    """Configuration for screen and asset settings."""

    screen_width: int = SCREEN_WIDTH
    screen_height: int = SCREEN_HEIGHT
    frame_rate: int = FRAME_RATE
    separator_width: int = SEPARATOR_WIDTH
    files: dict[str, list[str]] = field(default_factory=lambda: deepcopy(FILES))
    init_pos: dict[str, tuple] = field(default_factory=lambda: deepcopy(INIT_POS))


@dataclass
class ServerConfig:
    """Server and feature flag configuration."""

    default_api_port: int = DEFAULT_API_PORT
    poker_activity_enabled: bool = POKER_ACTIVITY_ENABLED
    plants_enabled: bool = PLANTS_ENABLED


@dataclass
class PokerConfig:
    """Poker-related runtime configuration."""

    max_poker_events: int = MAX_POKER_EVENTS
    poker_event_max_age_frames: int = POKER_EVENT_MAX_AGE_FRAMES
    enable_periodic_benchmarks: bool = False
    benchmark_config: BenchmarkEvalConfig = field(default_factory=BenchmarkEvalConfig)


@dataclass
class FoodConfig:
    """Food spawning configuration."""

    auto_food_enabled: bool = AUTO_FOOD_ENABLED
    spawn_rate: int = AUTO_FOOD_SPAWN_RATE
    ultra_low_energy_threshold: float = AUTO_FOOD_ULTRA_LOW_ENERGY_THRESHOLD
    low_energy_threshold: float = AUTO_FOOD_LOW_ENERGY_THRESHOLD
    high_energy_threshold_1: float = AUTO_FOOD_HIGH_ENERGY_THRESHOLD_1
    high_energy_threshold_2: float = AUTO_FOOD_HIGH_ENERGY_THRESHOLD_2
    high_pop_threshold_1: int = AUTO_FOOD_HIGH_POP_THRESHOLD_1
    high_pop_threshold_2: int = AUTO_FOOD_HIGH_POP_THRESHOLD_2
    live_food_chance: float = LIVE_FOOD_SPAWN_CHANCE


@dataclass
class TankConfig:
    """Tank-specific configuration.

    Attributes:
        brain_mode: Control how fish decisions are made.
            - "legacy": Fish use their built-in movement strategies (default)
            - "external": Fish receive actions from an external brain
    """

    brain_mode: str = "builtin"  # "builtin" | "external"


@dataclass
class SimulationConfig:
    """Aggregate configuration for running a simulation."""

    ecosystem: EcosystemConfig = field(default_factory=EcosystemConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    poker: PokerConfig = field(default_factory=PokerConfig)
    food: FoodConfig = field(default_factory=FoodConfig)
    plant: PlantConfig = field(default_factory=PlantConfig)
    tank: TankConfig = field(default_factory=TankConfig)
    headless: bool = True
    enable_phase_debug: bool = False

    def validate(self) -> None:
        """Validate the configuration for conflicting settings."""
        errors = []

        if not self.server.poker_activity_enabled and self.poker.enable_periodic_benchmarks:
            errors.append("Poker benchmarks require poker activity to be enabled.")

        if errors:
            raise ValueError("; ".join(errors))

    @classmethod
    def production(cls, *, headless: bool = False) -> SimulationConfig:
        """Preset matching production defaults."""
        return cls(headless=headless)

    @classmethod
    def headless_fast(cls) -> SimulationConfig:
        """Preset optimized for fast, deterministic tests."""
        return cls(
            headless=True,
            ecosystem=EcosystemConfig(
                max_population=60,
                critical_population_threshold=5,
                emergency_spawn_cooldown=90,
                spawn_margin_pixels=SPAWN_MARGIN_PIXELS,
                total_algorithm_count=TOTAL_ALGORITHM_COUNT,
                total_species_count=TOTAL_SPECIES_COUNT,
            ),
            server=ServerConfig(
                default_api_port=DEFAULT_API_PORT,
                poker_activity_enabled=False,
                plants_enabled=False,
            ),
            poker=PokerConfig(
                max_poker_events=5,
                poker_event_max_age_frames=POKER_EVENT_MAX_AGE_FRAMES,
                enable_periodic_benchmarks=False,
            ),
            food=FoodConfig(
                auto_food_enabled=True,
                spawn_rate=max(1, AUTO_FOOD_SPAWN_RATE // 2),
                ultra_low_energy_threshold=AUTO_FOOD_ULTRA_LOW_ENERGY_THRESHOLD,
                low_energy_threshold=AUTO_FOOD_LOW_ENERGY_THRESHOLD,
                high_energy_threshold_1=AUTO_FOOD_HIGH_ENERGY_THRESHOLD_1,
                high_energy_threshold_2=AUTO_FOOD_HIGH_ENERGY_THRESHOLD_2,
                high_pop_threshold_1=AUTO_FOOD_HIGH_POP_THRESHOLD_1,
                high_pop_threshold_2=AUTO_FOOD_HIGH_POP_THRESHOLD_2,
                live_food_chance=LIVE_FOOD_SPAWN_CHANCE,
            ),
        )

    @classmethod
    def debug_trace(cls) -> SimulationConfig:
        """Preset for deep debugging and tracing."""
        return cls(
            headless=True,
            enable_phase_debug=True,
            server=ServerConfig(
                default_api_port=DEFAULT_API_PORT,
                poker_activity_enabled=True,
                plants_enabled=True,
            ),
            poker=PokerConfig(
                max_poker_events=MAX_POKER_EVENTS,
                poker_event_max_age_frames=POKER_EVENT_MAX_AGE_FRAMES,
                enable_periodic_benchmarks=True,
                benchmark_config=BenchmarkEvalConfig(),
            ),
        )

    def with_overrides(self, **kwargs) -> SimulationConfig:
        """Return a copy of the config with updated fields."""
        return replace(self, **kwargs)
