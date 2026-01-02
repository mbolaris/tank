"""Mode pack definitions and interfaces."""

from core.modes.interfaces import (
    CANONICAL_MODE_CONFIG_KEYS,
    ModeConfig,
    ModePack,
    ModePackDefinition,
)
from core.modes.petri import create_petri_mode_pack
from core.modes.rulesets import (
    ActionSpace,
    EnergyModel,
    ModeRuleSet,
    PetriRuleSet,
    ScoringModel,
    SoccerRuleSet,
    SoccerTrainingRuleSet,
    TankRuleSet,
    get_ruleset,
    list_rulesets,
    register_ruleset,
)
from core.modes.tank import create_tank_mode_pack, normalize_tank_config

__all__ = [
    # Interfaces
    "CANONICAL_MODE_CONFIG_KEYS",
    "ModeConfig",
    "ModePack",
    "ModePackDefinition",
    # Mode pack factories
    "create_petri_mode_pack",
    "create_tank_mode_pack",
    "normalize_tank_config",
    # Rulesets
    "ActionSpace",
    "EnergyModel",
    "ModeRuleSet",
    "PetriRuleSet",
    "ScoringModel",
    "SoccerRuleSet",
    "SoccerTrainingRuleSet",
    "TankRuleSet",
    "get_ruleset",
    "list_rulesets",
    "register_ruleset",
]

