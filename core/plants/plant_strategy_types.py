"""Plant strategy type enum and visual configuration.

This module defines the baseline poker strategy types that plants can use,
along with their visual appearances (L-system parameters, colors).

Plants using these strategies serve as fixed "sparring partners" for fish,
forcing fish to evolve strategies to beat them. Successful plants
(those that win poker and accumulate energy) reproduce as exact clones.
"""

import random
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple


class PlantStrategyType(Enum):
    """Baseline poker strategy types for plants.

    Each type maps to a poker strategy implementation and has a distinct
    visual appearance (L-system parameters, color palette).
    """

    ALWAYS_FOLD = "always_fold"
    RANDOM = "random"
    LOOSE_PASSIVE = "loose_passive"
    TIGHT_PASSIVE = "tight_passive"
    TIGHT_AGGRESSIVE = "tight_aggressive"
    LOOSE_AGGRESSIVE = "loose_aggressive"
    BALANCED = "balanced"
    MANIAC = "maniac"
    GTO_EXPERT = "gto_expert"
    # Advanced strategies
    ADAPTIVE = "adaptive"
    POSITIONAL_EXPLOITER = "positional_exploiter"
    TRAP_SETTER = "trap_setter"
    MATHEMATICAL = "mathematical"


@dataclass
class PlantVisualConfig:
    """Visual configuration for a plant strategy type.

    Defines the L-system parameters and color palette that give each
    strategy type a distinctive appearance.
    """

    # L-system structure
    axiom: str
    angle_range: Tuple[float, float]  # (min, max) angle in degrees
    length_ratio_range: Tuple[float, float]
    branch_probability_range: Tuple[float, float]
    curve_factor_range: Tuple[float, float]

    # Color palette
    color_hue_range: Tuple[float, float]  # HSL hue (0-1)
    color_saturation_range: Tuple[float, float]

    # Physical traits
    stem_thickness_range: Tuple[float, float]
    leaf_density_range: Tuple[float, float]

    # Production rules template (optional override)
    production_rules: Optional[List[Tuple[str, str, float]]] = None

    # Display name for UI
    display_name: str = ""

    # Description for UI
    description: str = ""

    # Nectar/Floral visual configuration
    floral_type: str = "vortex"  # "vortex", "starburst", "hypno", "mandala"
    floral_petals: int = 5
    floral_layers: int = 3
    floral_spin: float = 1.0


# Visual configurations for each strategy type
# IMPORTANT: Each strategy has a VERY DISTINCT color to be easily identifiable
PLANT_STRATEGY_VISUALS: Dict[PlantStrategyType, PlantVisualConfig] = {
    PlantStrategyType.ALWAYS_FOLD: PlantVisualConfig(
        axiom="F",
        angle_range=(45.0, 60.0),  # Very droopy
        length_ratio_range=(0.45, 0.55),
        branch_probability_range=(0.3, 0.4),
        curve_factor_range=(0.25, 0.4),
        color_hue_range=(0.08, 0.10),  # BROWN/TAN - dead/wilted look
        color_saturation_range=(0.25, 0.4),
        stem_thickness_range=(0.3, 0.5),
        leaf_density_range=(0.15, 0.25),
        production_rules=[
            ("F", "F[-F]", 0.7),  # Sparse, droopy
            ("F", "F[--F]", 0.3),
        ],
        display_name="Wilted Fern",
        description="A droopy plant that folds under pressure",
        floral_type="hypno",
        floral_petals=3,
        floral_layers=2,
        floral_spin=0.5,
    ),
    PlantStrategyType.RANDOM: PlantVisualConfig(
        axiom="X",
        angle_range=(20.0, 70.0),  # VERY wide range for chaotic look
        length_ratio_range=(0.4, 0.9),
        branch_probability_range=(0.8, 1.0),
        curve_factor_range=(0.0, 0.5),
        color_hue_range=(0.85, 0.95),  # PINK/MAGENTA - stands out as "random"
        color_saturation_range=(0.9, 1.0),
        stem_thickness_range=(0.6, 1.4),
        leaf_density_range=(0.4, 0.9),
        production_rules=[
            ("X", "F[+X][-X]FX", 0.3),
            ("X", "F[-X][+X]", 0.3),
            ("X", "FF[++X][--X]", 0.2),
            ("X", "F[+FX][-FX]F", 0.2),
            ("F", "FF", 1.0),
        ],
        display_name="Chaos Fern",
        description="Unpredictable chaotic growth pattern",
        floral_type="starburst",
        floral_petals=7,
        floral_layers=4,
        floral_spin=5.0,
    ),
    PlantStrategyType.LOOSE_PASSIVE: PlantVisualConfig(
        axiom="X",
        angle_range=(18.0, 25.0),  # Wide, bushy
        length_ratio_range=(0.6, 0.72),
        branch_probability_range=(0.92, 1.0),
        curve_factor_range=(0.12, 0.22),
        color_hue_range=(0.58, 0.62),  # LIGHT BLUE/CYAN - passive, calm
        color_saturation_range=(0.65, 0.85),
        stem_thickness_range=(1.2, 1.5),
        leaf_density_range=(0.9, 1.0),
        production_rules=[
            ("X", "F[+X][-X]FX", 0.5),
            ("X", "F[-X]F[+X]F", 0.5),
            ("F", "FF", 1.0),
        ],
        display_name="Leafy Bush",
        description="A passive, leafy bush that calls everything",
        floral_type="vortex",
        floral_petals=4,
        floral_layers=3,
        floral_spin=1.0,
    ),
    PlantStrategyType.TIGHT_PASSIVE: PlantVisualConfig(
        axiom="F",
        angle_range=(12.0, 18.0),  # Tight, compact
        length_ratio_range=(0.72, 0.82),
        branch_probability_range=(0.45, 0.55),
        curve_factor_range=(0.03, 0.08),
        color_hue_range=(0.68, 0.72),  # PURPLE - compact rock
        color_saturation_range=(0.5, 0.7),
        stem_thickness_range=(1.5, 2.0),
        leaf_density_range=(0.35, 0.45),
        production_rules=[
            ("F", "FF[-F][+F]", 0.6),
            ("F", "F[-F]F", 0.4),
        ],
        display_name="Stone Shrub",
        description="A compact, rock-like shrub that rarely raises",
        floral_type="hypno",
        floral_petals=4,
        floral_layers=2,
        floral_spin=0.2,
    ),
    PlantStrategyType.TIGHT_AGGRESSIVE: PlantVisualConfig(
        axiom="X",
        angle_range=(35.0, 50.0),  # Sharp angles
        length_ratio_range=(0.52, 0.65),
        branch_probability_range=(0.7, 0.85),
        curve_factor_range=(0.0, 0.05),
        color_hue_range=(0.0, 0.03),  # BRIGHT RED - aggressive danger
        color_saturation_range=(0.9, 1.0),
        stem_thickness_range=(0.7, 1.0),
        leaf_density_range=(0.4, 0.6),
        production_rules=[
            ("X", "F[-X][++X]F[--X][+X]", 0.5),
            ("X", "F[+X][-X]", 0.5),
            ("F", "F[-F]+F", 0.6),
            ("F", "FF", 0.4),
        ],
        display_name="Thorny Spike",
        description="Sharp angular thorns - plays few hands aggressively",
        floral_type="starburst",
        floral_petals=3,
        floral_layers=3,
        floral_spin=3.0,
    ),
    PlantStrategyType.LOOSE_AGGRESSIVE: PlantVisualConfig(
        axiom="X",
        angle_range=(20.0, 32.0),
        length_ratio_range=(0.58, 0.72),
        branch_probability_range=(0.92, 1.0),
        curve_factor_range=(0.2, 0.35),
        color_hue_range=(0.10, 0.14),  # ORANGE - aggressive energy
        color_saturation_range=(0.95, 1.0),
        stem_thickness_range=(0.85, 1.1),
        leaf_density_range=(0.75, 0.9),
        production_rules=[
            ("X", "F[+X]F[-X]FX", 0.4),
            ("X", "F[-X]+F[+X]-X", 0.3),
            ("X", "FF[+X][-X]", 0.3),
            ("F", "FF", 1.0),
        ],
        display_name="Sprawling Vine",
        description="Aggressive sprawling vines - plays many hands",
        floral_type="vortex",
        floral_petals=6,
        floral_layers=4,
        floral_spin=2.5,
    ),
    PlantStrategyType.BALANCED: PlantVisualConfig(
        axiom="X",
        angle_range=(22.0, 28.0),
        length_ratio_range=(0.68, 0.76),
        branch_probability_range=(0.88, 0.96),
        curve_factor_range=(0.08, 0.14),
        color_hue_range=(0.32, 0.36),  # EMERALD GREEN - balanced, natural
        color_saturation_range=(0.75, 0.9),
        stem_thickness_range=(1.0, 1.25),
        leaf_density_range=(0.72, 0.85),
        production_rules=[
            ("X", "F[+X][-X]FX", 0.5),
            ("X", "F[-X]F[+X]F", 0.5),
            ("F", "FF", 1.0),
        ],
        display_name="Jade Tree",
        description="Perfectly symmetric tree - balanced play",
        floral_type="dahlia",
        floral_petals=5,
        floral_layers=5,
        floral_spin=1.0,
    ),
    PlantStrategyType.MANIAC: PlantVisualConfig(
        axiom="X",
        angle_range=(50.0, 75.0),  # EXTREME angles
        length_ratio_range=(0.45, 0.65),
        branch_probability_range=(0.95, 1.0),
        curve_factor_range=(0.3, 0.5),
        color_hue_range=(0.78, 0.82),  # VIOLET/NEON PURPLE - crazy
        color_saturation_range=(1.0, 1.0),
        stem_thickness_range=(0.5, 0.8),
        leaf_density_range=(0.7, 0.9),
        production_rules=[
            ("X", "F[++X][--X]F[+X][-X]X", 0.4),
            ("X", "F[-X][+X]FF", 0.3),
            ("X", "F[+++X][---X]", 0.3),
            ("F", "F[-F][+F]F", 0.5),
            ("F", "FF", 0.5),
        ],
        display_name="Chaos Spike",
        description="Explosive spiky growth - ultra-aggressive maniac",
        floral_type="starburst",
        floral_petals=9,
        floral_layers=5,
        floral_spin=8.0,
    ),
    PlantStrategyType.GTO_EXPERT: PlantVisualConfig(
        axiom="X",
        angle_range=(20.0, 26.0),
        length_ratio_range=(0.7, 0.78),
        branch_probability_range=(0.9, 0.98),
        curve_factor_range=(0.04, 0.1),
        color_hue_range=(0.48, 0.52),  # CYAN/TEAL - high-tech expert
        color_saturation_range=(0.95, 1.0),
        stem_thickness_range=(1.15, 1.4),
        leaf_density_range=(0.85, 0.98),
        production_rules=[
            ("X", "F[+X][-X]FX", 0.4),
            ("X", "F[-X]F[+X]F", 0.4),
            ("X", "FF[+X][-X]", 0.2),
            ("F", "FF", 1.0),
        ],
        display_name="Crystal Fern",
        description="Crystalline geometric fractal - optimal play",
        floral_type="mandelbrot",
        floral_petals=8,
        floral_layers=6,
        floral_spin=0.5,
    ),
    # Advanced strategies
    PlantStrategyType.ADAPTIVE: PlantVisualConfig(
        axiom="X",
        angle_range=(22.0, 35.0),  # Variable angles for adaptive look
        length_ratio_range=(0.6, 0.75),
        branch_probability_range=(0.8, 0.95),
        curve_factor_range=(0.1, 0.25),
        color_hue_range=(0.15, 0.18),  # GOLD/AMBER - adaptable, flexible
        color_saturation_range=(0.85, 1.0),
        stem_thickness_range=(0.9, 1.2),
        leaf_density_range=(0.7, 0.85),
        production_rules=[
            ("X", "F[+X][-X]FX", 0.35),
            ("X", "F[-X]F[+X]F", 0.35),
            ("X", "FF[++X][--X]", 0.3),
            ("F", "FF", 1.0),
        ],
        display_name="Golden Reed",
        description="Flexible golden plant that adapts to any situation",
        floral_type="vortex",
        floral_petals=6,
        floral_layers=4,
        floral_spin=1.5,
    ),
    PlantStrategyType.POSITIONAL_EXPLOITER: PlantVisualConfig(
        axiom="X",
        angle_range=(30.0, 45.0),  # Asymmetric angles for position awareness
        length_ratio_range=(0.55, 0.68),
        branch_probability_range=(0.75, 0.88),
        curve_factor_range=(0.05, 0.15),
        color_hue_range=(0.55, 0.58),  # DARK BLUE - strategic, calculating
        color_saturation_range=(0.8, 0.95),
        stem_thickness_range=(0.8, 1.1),
        leaf_density_range=(0.5, 0.7),
        production_rules=[
            ("X", "F[++X][-X]FX", 0.4),  # Asymmetric branching
            ("X", "F[+X][--X]F", 0.4),
            ("X", "FF[+X]", 0.2),
            ("F", "F[-F]+F", 0.6),
            ("F", "FF", 0.4),
        ],
        display_name="Shadow Fern",
        description="Strategic plant that exploits positional advantage",
        floral_type="starburst",
        floral_petals=5,
        floral_layers=4,
        floral_spin=2.0,
    ),
    PlantStrategyType.TRAP_SETTER: PlantVisualConfig(
        axiom="X",
        angle_range=(15.0, 22.0),  # Tight, deceptive angles
        length_ratio_range=(0.72, 0.82),
        branch_probability_range=(0.6, 0.75),
        curve_factor_range=(0.15, 0.28),
        color_hue_range=(0.75, 0.78),  # DEEP PURPLE - mysterious, trapping
        color_saturation_range=(0.7, 0.85),
        stem_thickness_range=(1.3, 1.6),
        leaf_density_range=(0.4, 0.55),
        production_rules=[
            ("X", "F[-X]F[+X]", 0.5),
            ("X", "FF[-X][+X]F", 0.3),
            ("X", "F[+X]F", 0.2),
            ("F", "FF", 1.0),
        ],
        display_name="Venus Trap",
        description="Deceptive plant that slowplays to trap opponents",
        floral_type="hypno",
        floral_petals=5,
        floral_layers=5,
        floral_spin=0.3,
    ),
    PlantStrategyType.MATHEMATICAL: PlantVisualConfig(
        axiom="X",
        angle_range=(25.0, 30.0),  # Precise, geometric angles
        length_ratio_range=(0.68, 0.72),  # Consistent ratios
        branch_probability_range=(0.85, 0.92),
        curve_factor_range=(0.0, 0.03),  # Nearly straight - precise
        color_hue_range=(0.42, 0.45),  # TEAL/GREEN-BLUE - analytical, precise
        color_saturation_range=(0.9, 1.0),
        stem_thickness_range=(1.0, 1.2),
        leaf_density_range=(0.8, 0.9),
        production_rules=[
            ("X", "F[+X][-X]FX", 0.5),
            ("X", "F[-X]F[+X]F", 0.5),
            ("F", "FF", 1.0),
        ],
        display_name="Fibonacci Spiral",
        description="Mathematically perfect fractal using pure pot odds",
        floral_type="mandala",
        floral_petals=8,
        floral_layers=5,
        floral_spin=0.8,
    ),
}


def get_strategy_visual_config(strategy_type: PlantStrategyType) -> PlantVisualConfig:
    """Get the visual configuration for a strategy type."""
    return PLANT_STRATEGY_VISUALS[strategy_type]


def get_random_strategy_type(rng: Optional[random.Random] = None) -> PlantStrategyType:
    """Get a random strategy type for spawning new plants."""
    from core.util.rng import require_rng_param

    _rng = require_rng_param(rng, "__init__")
    return _rng.choice(list(PlantStrategyType))


def get_all_strategy_types() -> List[PlantStrategyType]:
    """Get all available strategy types."""
    return list(PlantStrategyType)


def get_poker_strategy_for_type(
    strategy_type: PlantStrategyType, rng: Optional[random.Random] = None
):
    """Get the corresponding poker strategy implementation for a plant strategy type.

    Returns:
        PokerStrategyAlgorithm instance for the given strategy type
    """
    from core.poker.strategy.implementations import (
        AlwaysFoldStrategy,
        BalancedStrategy,
        LooseAggressiveStrategy,
        LoosePassiveStrategy,
        ManiacStrategy,
        RandomStrategy,
        TightAggressiveStrategy,
        TightPassiveStrategy,
    )
    from core.poker.strategy.implementations.advanced import (
        AdaptiveStrategy,
        MathematicalStrategy,
        PositionalExploiter,
        TrapSetterStrategy,
    )
    from core.poker.strategy.implementations.expert import GTOExpertStrategy

    strategy_map = {
        PlantStrategyType.ALWAYS_FOLD: AlwaysFoldStrategy,
        PlantStrategyType.RANDOM: RandomStrategy,
        PlantStrategyType.LOOSE_PASSIVE: LoosePassiveStrategy,
        PlantStrategyType.TIGHT_PASSIVE: TightPassiveStrategy,
        PlantStrategyType.TIGHT_AGGRESSIVE: TightAggressiveStrategy,
        PlantStrategyType.LOOSE_AGGRESSIVE: LooseAggressiveStrategy,
        PlantStrategyType.BALANCED: BalancedStrategy,
        PlantStrategyType.MANIAC: ManiacStrategy,
        PlantStrategyType.GTO_EXPERT: GTOExpertStrategy,
        # Advanced strategies
        PlantStrategyType.ADAPTIVE: AdaptiveStrategy,
        PlantStrategyType.POSITIONAL_EXPLOITER: PositionalExploiter,
        PlantStrategyType.TRAP_SETTER: TrapSetterStrategy,
        PlantStrategyType.MATHEMATICAL: MathematicalStrategy,
    }

    strategy_class = strategy_map[strategy_type]
    return strategy_class.random_instance(rng=rng)
