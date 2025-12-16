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
FRACTAL_PLANT_ROOT_SPOT_COUNT = 25  # Number of positions where plants can grow
FRACTAL_PLANT_ROOT_Y_BASE = SCREEN_HEIGHT - 15  # Y position near tank bottom
FRACTAL_PLANT_ROOT_Y_VARIANCE = 8  # Slight Y variation for natural look

# Maintenance / safety
# Periodically reconcile plants vs root spots to enforce "<= 1 plant per spot".
FRACTAL_PLANT_CULL_INTERVAL = 120

# Plant Energy System
FRACTAL_PLANT_INITIAL_ENERGY = 20.0  # Starting energy for new sprouted plants
FRACTAL_PLANT_MATURE_ENERGY = 120.0  # Starting energy for initial mature plants (100% of max)
FRACTAL_PLANT_MAX_ENERGY = 120.0  # Maximum energy capacity - Reduced for smaller plants
FRACTAL_PLANT_MIN_SIZE = 0.3  # Minimum size multiplier
FRACTAL_PLANT_MAX_SIZE = 1.0  # Maximum size multiplier - Reduced from 1.2
FRACTAL_PLANT_DEATH_ENERGY = 5.0  # Energy threshold for death

# Plant Dimensions
FRACTAL_PLANT_BASE_WIDTH = 60  # Base width in pixels
FRACTAL_PLANT_BASE_HEIGHT = 65  # Base height in pixels

# Plant Poker Configuration
FRACTAL_PLANT_POKER_COOLDOWN = 60  # 3 seconds at 60fps (increased to prevent rapid energy loss)
FRACTAL_PLANT_MIN_POKER_ENERGY = 0.0  # Plants can always play poker (no min energy)
FRACTAL_PLANT_POKER_BET_RATIO = 0.15  # Max bet as ratio of energy

# Plant Reproduction
FRACTAL_PLANT_NECTAR_COOLDOWN = 600  # 20 seconds between nectar production - Increased from 300
FRACTAL_PLANT_NECTAR_ENERGY = 50.0  # Energy provided by nectar
FRACTAL_PLANT_SPROUTING_CHANCE = 0.5  # Chance to sprout when nectar consumed - Reduced from 0.8
FRACTAL_PLANT_INITIAL_COUNT = 3  # Number of plants to start with

# Plant Energy Collection (Passive Growth)
FRACTAL_PLANT_BASE_ENERGY_RATE = 0.01  # Base energy gain per frame - Increased to prevent starvation
FRACTAL_PLANT_GROWTH_FACTOR = 0.3  # Compound growth rate modifier
FRACTAL_PLANT_DAY_MODIFIER = 1.0  # Energy collection during day
FRACTAL_PLANT_DAWN_DUSK_MODIFIER = 0.7  # Energy collection at dawn/dusk
FRACTAL_PLANT_NIGHT_MODIFIER = 0.3  # Energy collection at night

# L-System Fractal Rendering
FRACTAL_PLANT_MIN_ITERATIONS = 1  # Minimum L-system iterations (small plants)
FRACTAL_PLANT_MAX_ITERATIONS = 3  # Maximum L-system iterations (large plants)
FRACTAL_PLANT_DEFAULT_ANGLE = 25.0  # Default branching angle (degrees)
FRACTAL_PLANT_DEFAULT_LENGTH_RATIO = 0.7  # Default length reduction per iteration

# Plant Poker Proximity Detection (close but not touching)
# Plants are stationary at root spots - poker should only trigger when reasonably close
# Fish swim to plants, so fish-plant games use fish proximity settings
# Plant-plant games are rare and only happen between adjacent plants
FRACTAL_PLANT_POKER_MIN_DISTANCE = 10.0  # Minimum center-to-center distance (allows close contact)
FRACTAL_PLANT_POKER_MAX_DISTANCE = 80.0  # Maximum distance - tighter for closer interactions
