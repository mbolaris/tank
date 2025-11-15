# Screen dimensions in pixels
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# The frame rate for the game loop, in frames per second
FRAME_RATE = 30

# The number of schooling fish to create at the start of the game
NUM_SCHOOLING_FISH = 6  # Reduced to ease food pressure

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

# Filenames for the animation frames of each type of sprite
FILES = {
    'solo_fish': ['george1.png', 'george2.png'],
    'crab': ['crab1.png', 'crab2.png'],
    'schooling_fish': ['school.png'],
    'plant': ['plant1.png', 'plant2.png'],
    'castle': ['castle.png'],
    'food': ['food1.png', 'food2.png'],    
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
