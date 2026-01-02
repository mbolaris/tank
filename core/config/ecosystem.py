"""Ecosystem and population management configuration constants.

This module defines the parameters that control population dynamics, spawning,
and spatial interactions. These values determine how the ecosystem self-regulates.

Design Philosophy:
    The ecosystem should be self-sustaining without constant intervention.
    Population naturally fluctuates around TARGET_POPULATION through:
    - Food availability (controlled by food.py constants)
    - Reproduction success (controlled by fish.py constants)
    - Emergency spawning (prevents extinction events)
"""

# =============================================================================
# INITIAL POPULATION
# =============================================================================
# Starting population affects early-game dynamics.
# Too few = slow start, risk of extinction before stable population.
# Too many = immediate resource competition, weak initial selection.
NUM_SCHOOLING_FISH = 10  # Small founding population, allows genetic diversity to emerge

# =============================================================================
# POPULATION TARGETS
# =============================================================================
# The ecosystem aims to maintain population near TARGET_POPULATION.
# This creates consistent selection pressure across simulation runs.
#
# Trade-off: Higher target = more fish, more CPU load, weaker per-fish selection.
#            Lower target = stronger selection, but less genetic diversity.
TARGET_POPULATION = 80  # Sweet spot: enough diversity, manageable performance
MAX_POPULATION = 100  # Hard cap: prevents runaway population growth

# Emergency spawning prevents extinction events.
# Below CRITICAL threshold, the ecosystem force-spawns fish to recover.
CRITICAL_POPULATION_THRESHOLD = 10  # Below 10 fish = extinction risk
EMERGENCY_SPAWN_COOLDOWN = 180  # 6 seconds between emergency spawns (prevents flood)

# =============================================================================
# ALGORITHM & SPECIES DIVERSITY
# =============================================================================
# These track the diversity of behavior strategies in the population.
# Used for statistics and diversity-aware spawning.
TOTAL_ALGORITHM_COUNT = 50  # 50 unique behavior algorithms available
TOTAL_SPECIES_COUNT = 4  # Visual species variations (affects appearance only)

# =============================================================================
# EVENT TRACKING
# =============================================================================
# The ecosystem tracks events (births, deaths, poker games) for analysis.
# Capped to prevent unbounded memory growth in long simulations.
MAX_ECOSYSTEM_EVENTS = 1000  # Ring buffer: oldest events discarded when full
ENERGY_STATS_WINDOW_FRAMES = 1800  # 60-second rolling window for energy statistics

# =============================================================================
# SPAWNING BEHAVIOR
# =============================================================================
# Controls how new fish enter the ecosystem (both natural and emergency).

# Diversity spawning tries to maintain algorithm variety.
# If population becomes dominated by one algorithm, spawning prefers others.
MAX_DIVERSITY_SPAWN_ATTEMPTS = 10  # Try up to 10 times to find underrepresented algorithm

# Spawn margin keeps fish away from screen edges at birth.
# Prevents immediate wall collisions and gives newborns space to orient.
SPAWN_MARGIN_PIXELS = 100  # 100px buffer from all edges

# =============================================================================
# SPATIAL QUERY RADII
# =============================================================================
# These control the search radius for different interactions.
# Larger radii = more accurate but slower (O(n) within radius).
# Tuned for performance vs accuracy trade-off.
#
# The SpatialGrid optimization makes these queries fast (~O(k) where k = nearby entities).

# Collision detection: checks for entity overlap
# Larger radius catches fast-moving entities that might tunnel through each other.
COLLISION_QUERY_RADIUS = 100  # 100px catches most collisions without excess checks

# Mating: finding potential partners
# Larger radius gives more mate choices but increases CPU cost.
MATING_QUERY_RADIUS = 150  # 150px allows reasonable mate search range

# =============================================================================
# POKER PROXIMITY
# =============================================================================
# Poker games trigger when fish are close but not overlapping.
# This creates a "social distance" for poker interactions.
#
# Trade-off: Tighter range = fewer games, more intentional poker-seeking.
#            Wider range = more games, more incidental poker encounters.
FISH_POKER_MIN_DISTANCE = 10  # Must be at least 10px apart (not overlapping)
FISH_POKER_MAX_DISTANCE = 160  # Wider range to trigger more poker encounters
POKER_PROXIMITY_QUERY_RADIUS = 140  # Larger search radius for poker partner lookup
