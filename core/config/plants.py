"""Fractal plant system configuration constants."""

from .display import SCREEN_HEIGHT  # Import for root Y calculation

# Plant animation parameters
PLANT_SWAY_RANGE = 5
PLANT_SWAY_SPEED = 0.0005

# Plant Constants (basic)
PLANT_FOOD_PRODUCTION_INTERVAL = 50  # Frames between food production (1.67 seconds)
PLANT_FOOD_PRODUCTION_ENERGY = 15  # Energy cost to produce food
PLANT_PRODUCTION_CHANCE = 0.50  # 50% chance to produce food each interval

# Root Spot Configuration
PLANT_ROOT_SPOT_COUNT = 25  # Number of positions where plants can grow
PLANT_ROOT_Y_BASE = SCREEN_HEIGHT - 15  # Y position near tank bottom
PLANT_ROOT_Y_VARIANCE = 8  # Slight Y variation for natural look

# Maintenance / safety
# Periodically reconcile plants vs root spots to enforce "<= 1 plant per spot".
PLANT_CULL_INTERVAL = 120

# Plant Energy System
PLANT_INITIAL_ENERGY = 20.0  # Starting energy for new sprouted plants
PLANT_MATURE_ENERGY = 200.0  # Starting energy for initial/respawned plants
PLANT_MAX_ENERGY = 200.0  # Maximum energy capacity
PLANT_MIN_SIZE = 0.3  # Minimum size multiplier
PLANT_MAX_SIZE = 1.0  # Maximum size multiplier - Reduced from 1.2
PLANT_DEATH_ENERGY = 5.0  # Energy threshold for death
PLANT_ENERGY_GAIN_MULTIPLIER = 2.5  # Global boost to energy collection

# Plant Emergency Respawn
PLANT_CRITICAL_POPULATION = 2  # Respawn if below this count
PLANT_EMERGENCY_RESPAWN_COOLDOWN = 300  # 5 seconds between respawns

# Plant Dimensions
PLANT_BASE_WIDTH = 60  # Base width in pixels
PLANT_BASE_HEIGHT = 65  # Base height in pixels

# Plant Poker Configuration
PLANT_POKER_COOLDOWN = 60  # 3 seconds at 60fps (increased to prevent rapid energy loss)
PLANT_MIN_POKER_ENERGY = 0.0  # Plants can always play poker (no min energy)
PLANT_POKER_BET_RATIO = 0.15  # Max bet as ratio of energy

# Plant Reproduction
PLANT_NECTAR_COOLDOWN = 600  # 20 seconds between nectar production - Increased from 300
PLANT_NECTAR_ENERGY = 50.0  # Energy provided by nectar
PLANT_SPROUTING_CHANCE = 0.5  # Chance to sprout when nectar consumed - Reduced from 0.8
PLANT_INITIAL_COUNT = 3  # Number of plants to start with

# Plant Energy Collection (Passive Growth)
PLANT_BASE_ENERGY_RATE = 0.02  # Base energy gain per frame - Increased to prevent starvation
PLANT_GROWTH_FACTOR = 0.3  # Compound growth rate modifier
PLANT_DAY_MODIFIER = 1.0  # Energy collection during day
PLANT_DAWN_DUSK_MODIFIER = 0.7  # Energy collection at dawn/dusk
PLANT_NIGHT_MODIFIER = 0.3  # Energy collection at night

# L-System Fractal Rendering
PLANT_MIN_ITERATIONS = 1  # Minimum L-system iterations (small plants)
PLANT_MAX_ITERATIONS = 3  # Maximum L-system iterations (large plants)
PLANT_DEFAULT_ANGLE = 25.0  # Default branching angle (degrees)
PLANT_DEFAULT_LENGTH_RATIO = 0.7  # Default length reduction per iteration

# Plant Poker Proximity Detection (close but not touching)
# Plants are stationary at root spots - poker should only trigger when reasonably close
# Fish swim to plants, so fish-plant games use fish proximity settings
# Plant-plant games are rare and only happen between adjacent plants
PLANT_POKER_MIN_DISTANCE = 10.0  # Minimum center-to-center distance (allows close contact)
PLANT_POKER_MAX_DISTANCE = 80.0  # Maximum distance - tighter for closer interactions
