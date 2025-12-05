"""Entity-specific configuration constants (Crab, ID offsets, etc)."""

# Crab Constants
CRAB_INITIAL_ENERGY = 150.0  # Starting energy for crabs
CRAB_ATTACK_ENERGY_TRANSFER = 60.0  # Energy stolen from fish when attacked
CRAB_ATTACK_DAMAGE = 20.0  # Damage dealt to fish
CRAB_IDLE_CONSUMPTION = 0.01  # Energy consumed per frame when idle
CRAB_ATTACK_COOLDOWN = 15  # Frames between attacks (0.5 seconds)

# Entity ID Offsets (For Stable Identification)
# These offsets are added to internal monotonic IDs to generate globally unique
# stable IDs for the frontend. This prevents ID reuse issues with Python's id().
FISH_ID_OFFSET = 0
PLANT_ID_OFFSET = 1_000_000
FOOD_ID_OFFSET = 3_000_000
NECTAR_ID_OFFSET = 4_000_000
