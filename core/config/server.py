"""Server and feature flag configuration constants."""

# Server Configuration
DEFAULT_API_PORT = 8000  # Default port for FastAPI backend

# Feature Flags
POKER_ACTIVITY_ENABLED = True  # Enable poker activity
PLANTS_ENABLED = True  # Enable unified plant system
SOCCER_LADDER_EVAL_ENABLED = True  # Enable periodic live soccer ladder evaluation
SOCCER_LADDER_EVAL_INTERVAL_FRAMES = 20_000  # Default evaluation cadence (frames)
POKER_SKILL_EVAL_ENABLED = True  # Enable periodic per-fish frozen poker ladder evaluation
POKER_SKILL_EVAL_INTERVAL_FRAMES = 20_000  # Poker cadence; runtime applies a staggered offset
