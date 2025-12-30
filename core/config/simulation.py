"""Domain-agnostic simulation configuration constants.

This module defines configuration for the abstract simulation layer.
These constants are environment-independent and can be used by any
simulation environment (fish tank, 3D aquarium, graph habitat, etc.).

For domain-specific constants (fish, plants, etc.), see the respective
config modules (fish.py, plants.py, ecosystem.py).

Design Philosophy:
    The simulation layer should not know about specific entity types.
    It works with abstract concepts like:
    - "skill game proximity" (not "poker distance")
    - "entity interaction radius" (not "fish collision radius")
    - "evolving agents" (not "fish")
"""

# =============================================================================
# SKILL GAME PROXIMITY
# =============================================================================
# Skill games (poker, etc.) trigger when entities are close but not overlapping.
# These define the default interaction zone for skill games.
#
# Trade-off: Tighter range = fewer games, more intentional interaction-seeking.
#            Wider range = more games, more incidental encounters.

# Default skill game interaction distances (can be overridden per entity type)
SKILL_GAME_MIN_DISTANCE = 10.0  # Minimum distance - entities shouldn't overlap
SKILL_GAME_MAX_DISTANCE = 80.0  # Maximum distance - must be "close enough"

# Search radius for finding potential skill game partners
# Should be >= SKILL_GAME_MAX_DISTANCE to catch all candidates
SKILL_GAME_QUERY_RADIUS = 100.0


# =============================================================================
# ENTITY INTERACTION RADII
# =============================================================================
# These control search radii for different interaction types.
# Larger radii = more accurate but slower (O(k) where k = nearby entities).

# Collision detection: checks for entity overlap
COLLISION_QUERY_RADIUS = 100.0

# Reproduction: finding potential mates
MATING_QUERY_RADIUS = 150.0


# =============================================================================
# SIMULATION TIMING
# =============================================================================
# Throttling intervals for performance optimization at high entity counts

# Skill game throttle intervals by population tier
SKILL_GAME_THROTTLE_THRESHOLD_1 = 100  # >= 100 entities: every 2 frames
SKILL_GAME_THROTTLE_THRESHOLD_2 = 200  # >= 200 entities: every 3 frames


# =============================================================================
# SIMULATION FLAGS
# =============================================================================
# Feature toggles for the simulation engine

# Whether skill games are enabled (can be disabled for performance testing)
SKILL_GAMES_ENABLED = True
