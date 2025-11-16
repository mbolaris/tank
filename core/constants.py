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
AUTO_FOOD_SPAWN_RATE = 60  # Spawn food every 2 seconds (60 frames at 30fps) - REDUCED for increased difficulty
AUTO_FOOD_ENABLED = True  # Enable/disable automatic food spawning

# Food type definitions with nutrient properties
FOOD_TYPES = {
    'algae': {
        'name': 'Algae Flake',
        'files': ['food_algae1.png', 'food_algae2.png'],
        'energy': 30.0,  # Moderate energy - increased 50% for sustainability
        'rarity': 0.35,  # 35% spawn rate
        'sink_multiplier': 0.8,  # Sinks slower (lighter)
        'stationary': False,
    },
    'protein': {
        'name': 'Protein Flake',
        'files': ['food_protein1.png', 'food_protein2.png'],
        'energy': 52.5,  # High energy - increased 50% for sustainability
        'rarity': 0.25,  # 25% spawn rate
        'sink_multiplier': 1.2,  # Sinks faster (heavier)
        'stationary': False,
    },
    'vitamin': {
        'name': 'Vitamin Flake',
        'files': ['food_vitamin1.png', 'food_vitamin2.png'],
        'energy': 37.5,  # Moderate energy - increased 50% for sustainability
        'rarity': 0.20,  # 20% spawn rate
        'sink_multiplier': 0.9,  # Sinks slightly slower
        'stationary': False,
    },
    'energy': {
        'name': 'Energy Flake',
        'files': ['food_energy1.png', 'food_energy2.png'],
        'energy': 45.0,  # High energy - increased 50% for sustainability
        'rarity': 0.15,  # 15% spawn rate
        'sink_multiplier': 1.0,  # Normal sink rate
        'stationary': False,
    },
    'rare': {
        'name': 'Rainbow Flake',
        'files': ['food_rare1.png', 'food_rare2.png'],
        'energy': 75.0,  # Very high energy - increased 50% for sustainability
        'rarity': 0.05,  # 5% spawn rate (rare)
        'sink_multiplier': 1.1,  # Sinks bit faster
        'stationary': False,
    },
    'nectar': {
        'name': 'Plant Nectar',
        'files': ['food_vitamin1.png', 'food_vitamin2.png'],
        'energy': 60.0,  # Rewarding snack - increased 50% for sustainability
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
    'food': ['food1.png', 'food2.png'],  # Kept for backward compatibility
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
