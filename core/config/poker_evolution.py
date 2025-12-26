"""Poker evolution experiment configuration.

These knobs are opt-in and activated via environment variables to avoid
changing default simulation behavior.
"""

from __future__ import annotations

import os


def _env_bool(key: str, default: bool) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(key: str, default: float) -> float:
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


# Master toggle for experiment-only changes.
EXPERIMENT_ENABLED = _env_bool("TANK_POKER_EVOLUTION_EXPERIMENT", False)

# Winner-biased inheritance weight for poker reproduction.
WINNER_WEIGHT = _env_float("TANK_POKER_WINNER_WEIGHT", 0.85) if EXPERIMENT_ENABLED else 0.0

# Mutation dampening for poker strategy inheritance.
MUTATION_RATE_MULTIPLIER = (
    _env_float("TANK_POKER_MUTATION_RATE_MULTIPLIER", 0.6) if EXPERIMENT_ENABLED else 1.0
)
MUTATION_STRENGTH_MULTIPLIER = (
    _env_float("TANK_POKER_MUTATION_STRENGTH_MULTIPLIER", 0.6) if EXPERIMENT_ENABLED else 1.0
)

# Novelty injection rate for poker strategy crossover.
NOVELTY_INJECTION_RATE = (
    _env_float("TANK_POKER_NOVELTY_INJECTION_RATE", 0.002) if EXPERIMENT_ENABLED else 0.0
)

# Poker stake scaling for stronger selection pressure.
STAKE_MULTIPLIER = _env_float("TANK_POKER_STAKE_MULTIPLIER", 1.5) if EXPERIMENT_ENABLED else 1.0
MAX_BET_CAP = _env_float("TANK_POKER_MAX_BET_CAP", 30.0) if EXPERIMENT_ENABLED else 20.0
