# Screen dimensions in pixels
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# The frame rate for the game loop, in frames per second
FRAME_RATE = 30

# The number of schooling fish to create at the start of the game
NUM_SCHOOLING_FISH = 10  # Increased to create resource competition

# The rate at which the sprite images change, in milliseconds
IMAGE_CHANGE_RATE = 500  # change this to your preference

# The rate at which the speed of an agent changes when avoiding, as a fraction of the current speed
AVOIDANCE_SPEED_CHANGE = 0.2  # change this to your preference

# The rate at which the speed of an agent changes when aligning, as a fraction of the current speed
ALIGNMENT_SPEED_CHANGE = 0.1  # change this to your preference

# Random movement probabilities for agents [left, straight, right]
RANDOM_MOVE_PROBABILITIES = [0.05, 0.9, 0.05]

# Velocity change divisor for random movements
RANDOM_VELOCITY_DIVISOR = 10.0

# Fish growth rate when eating food
FISH_GROWTH_RATE = 0.1

# Plant animation parameters
PLANT_SWAY_RANGE = 5
PLANT_SWAY_SPEED = 0.0005

# Food physics
FOOD_SINK_ACCELERATION = 0.01

# Automatic food spawning
AUTO_FOOD_SPAWN_RATE = 90  # Spawn food every 3 seconds (90 frames at 30fps) - Increased for better fish survival
AUTO_FOOD_ENABLED = True  # Enable/disable automatic food spawning

# Food type definitions with nutrient properties
FOOD_TYPES = {
    'algae': {
        'name': 'Algae Flake',
        'files': ['food_algae1.png', 'food_algae2.png'],
        'energy': 20.0,  # Low energy - basic food source
        'rarity': 0.35,  # 35% spawn rate
        'sink_multiplier': 0.8,  # Sinks slower (lighter)
        'stationary': False,
    },
    'protein': {
        'name': 'Protein Flake',
        'files': ['food_protein1.png', 'food_protein2.png'],
        'energy': 35.0,  # Good energy - valuable food
        'rarity': 0.25,  # 25% spawn rate
        'sink_multiplier': 1.2,  # Sinks faster (heavier)
        'stationary': False,
    },
    'vitamin': {
        'name': 'Vitamin Flake',
        'files': ['food_vitamin1.png', 'food_vitamin2.png'],
        'energy': 25.0,  # Moderate energy
        'rarity': 0.20,  # 20% spawn rate
        'sink_multiplier': 0.9,  # Sinks slightly slower
        'stationary': False,
    },
    'energy': {
        'name': 'Energy Flake',
        'files': ['food_energy1.png', 'food_energy2.png'],
        'energy': 30.0,  # Good energy
        'rarity': 0.15,  # 15% spawn rate
        'sink_multiplier': 1.0,  # Normal sink rate
        'stationary': False,
    },
    'rare': {
        'name': 'Rainbow Flake',
        'files': ['food_rare1.png', 'food_rare2.png'],
        'energy': 50.0,  # High energy - rare treat
        'rarity': 0.05,  # 5% spawn rate (rare)
        'sink_multiplier': 1.1,  # Sinks bit faster
        'stationary': False,
    },
    'nectar': {
        'name': 'Plant Nectar',
        'files': ['food_vitamin1.png', 'food_vitamin2.png'],
        'energy': 40.0,  # Rewarding stationary food
        'rarity': 0.15,  # Used for plant-only spawn weighting
        'sink_multiplier': 0.0,  # Remains in place
        'stationary': True,
    },
}

# Filenames for the animation frames of each type of sprite
FILES = {
    'solo_fish': ['george1.png', 'george2.png'],
    'crab': ['crab1.png', 'crab2.png'],
    'schooling_fish': ['school.png'],
    'plant': ['plant1.png', 'plant2.png'],
    'castle': ['castle.png'],
}

# The initial positions of the sprites in the game
INIT_POS = {
    'fish': (275, 80),
    'crab': (250, 542),
    'school': (300, 200),
    'plant1': (250, 510),
    'plant2': (10, 510),
    'plant3': (500, 510),  # Add third plant
    'castle': (100, 500),
}

# UI Constants - Poker Notifications
POKER_NOTIFICATION_DURATION = 180  # 6 seconds at 30fps
POKER_NOTIFICATION_MAX_COUNT = 5
POKER_TIE_COLOR = (255, 255, 100)
POKER_WIN_COLOR = (100, 255, 100)

# UI Constants - Health Bars
HEALTH_BAR_WIDTH = 30
HEALTH_BAR_HEIGHT = 4
HEALTH_CRITICAL_COLOR = (200, 50, 50)  # Red (below 30%)
HEALTH_LOW_COLOR = (200, 200, 50)      # Yellow (30-60%)
HEALTH_GOOD_COLOR = (50, 200, 50)      # Green (above 60%)

# Fish movement constraints
FISH_TOP_MARGIN = 20  # Minimum pixels from top to keep energy bar visible

# Fish Energy and Metabolism Constants
INITIAL_ENERGY_RATIO = 0.5  # Start with 50% energy
BABY_METABOLISM_MULTIPLIER = 0.7  # Babies need less energy
ELDER_METABOLISM_MULTIPLIER = 1.2  # Elders need more energy

# Energy Thresholds (centralized for consistency across the codebase)
STARVATION_THRESHOLD = 15.0  # Below this, fish dies from starvation
CRITICAL_ENERGY_THRESHOLD = 15.0  # Emergency survival mode (same as starvation threshold)
LOW_ENERGY_THRESHOLD = 30.0  # Fish should prioritize finding food
SAFE_ENERGY_THRESHOLD = 60.0  # Comfortable energy level for exploration and breeding
