"""Ecosystem and population management configuration constants."""

# The number of schooling fish to create at the start of the game
NUM_SCHOOLING_FISH = 10  # Start with 10 fish

# Target stable population for ecosystem balance
TARGET_POPULATION = 80

# Ecosystem Constants
TOTAL_ALGORITHM_COUNT = 50  # Total number of behavior algorithms available
TOTAL_SPECIES_COUNT = 4  # Total number of fish species
MAX_ECOSYSTEM_EVENTS = 1000  # Maximum events to track in ecosystem history
MAX_POPULATION = 100  # Maximum population capacity for ecosystem
CRITICAL_POPULATION_THRESHOLD = 10  # Minimum population before emergency spawning
EMERGENCY_SPAWN_COOLDOWN = 180  # Frames between emergency spawns (6 seconds at 30fps)
ENERGY_STATS_WINDOW_FRAMES = 1800  # Frames for energy stats rolling window (60s at 30fps)

# Population Stress Constants
POPULATION_STRESS_MAX_MULTIPLIER = 0.8  # Maximum population stress from low population
POPULATION_STRESS_DEATH_RATE_MAX = 0.4  # Maximum stress contribution from death rate
POPULATION_STRESS_MAX_TOTAL = 1.0  # Maximum total population stress

# Spawning Constants
MAX_DIVERSITY_SPAWN_ATTEMPTS = 10  # Maximum attempts to spawn diverse fish
SPAWN_MARGIN_PIXELS = 100  # Margin from screen edges for spawning

# Spatial Query Constants (for collision detection and mating)
COLLISION_QUERY_RADIUS = 100  # Radius for nearby entity queries during collision detection (pixels)
MATING_QUERY_RADIUS = 150  # Radius for finding potential mates (pixels)

# Poker Proximity Constants (close but not touching)
FISH_POKER_MIN_DISTANCE = 10  # Minimum center-to-center distance (allows close contact)
FISH_POKER_MAX_DISTANCE = 80  # Maximum center-to-center distance for poker trigger
POKER_PROXIMITY_QUERY_RADIUS = 100  # Radius for finding nearby poker candidates (fish and plants)
