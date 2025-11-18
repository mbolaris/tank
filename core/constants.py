# Screen dimensions in pixels (must match Canvas size in frontend)
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# The frame rate for the game loop, in frames per second
FRAME_RATE = 30

# The number of schooling fish to create at the start of the game
NUM_SCHOOLING_FISH = 10  # Increased to create resource competition

# Target stable population for ecosystem balance
TARGET_POPULATION = 15

# Default agent size (width and height in pixels)
DEFAULT_AGENT_SIZE = 50.0

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
AUTO_FOOD_SPAWN_RATE = 90  # Spawn food every 3 seconds (90 frames at 30fps) - Base rate
AUTO_FOOD_ENABLED = True  # Enable/disable automatic food spawning

# Dynamic food spawn scaling based on population and energy
AUTO_FOOD_LOW_ENERGY_THRESHOLD = 2000  # Double spawn rate below this total energy
AUTO_FOOD_HIGH_ENERGY_THRESHOLD_1 = 4000  # Reduce spawn rate above this total energy
AUTO_FOOD_HIGH_ENERGY_THRESHOLD_2 = 6000  # Further reduce spawn rate above this total energy
AUTO_FOOD_HIGH_POP_THRESHOLD_1 = 15  # Reduce spawn rate above this fish count
AUTO_FOOD_HIGH_POP_THRESHOLD_2 = 20  # Further reduce spawn rate above this fish count

# Food type definitions with nutrient properties
FOOD_TYPES = {
    'algae': {
        'name': 'Algae Flake',
        'files': ['food_algae1.png', 'food_algae2.png'],
        'energy': 30.0,  # Low energy - basic food source (increased 50%)
        'rarity': 0.35,  # 35% spawn rate
        'sink_multiplier': 0.8,  # Sinks slower (lighter)
        'stationary': False,
    },
    'protein': {
        'name': 'Protein Flake',
        'files': ['food_protein1.png', 'food_protein2.png'],
        'energy': 50.0,  # Good energy - valuable food (increased 50%)
        'rarity': 0.25,  # 25% spawn rate
        'sink_multiplier': 1.2,  # Sinks faster (heavier)
        'stationary': False,
    },
    'vitamin': {
        'name': 'Vitamin Flake',
        'files': ['food_vitamin1.png', 'food_vitamin2.png'],
        'energy': 40.0,  # Moderate energy (increased 50%)
        'rarity': 0.20,  # 20% spawn rate
        'sink_multiplier': 0.9,  # Sinks slightly slower
        'stationary': False,
    },
    'energy': {
        'name': 'Energy Flake',
        'files': ['food_energy1.png', 'food_energy2.png'],
        'energy': 45.0,  # Good energy (increased 50%)
        'rarity': 0.15,  # 15% spawn rate
        'sink_multiplier': 1.0,  # Normal sink rate
        'stationary': False,
    },
    'rare': {
        'name': 'Rainbow Flake',
        'files': ['food_rare1.png', 'food_rare2.png'],
        'energy': 75.0,  # High energy - rare treat (increased 50%)
        'rarity': 0.05,  # 5% spawn rate (rare)
        'sink_multiplier': 1.1,  # Sinks bit faster
        'stationary': False,
    },
    'nectar': {
        'name': 'Plant Nectar',
        'files': ['food_vitamin1.png', 'food_vitamin2.png'],
        'energy': 60.0,  # Rewarding stationary food (increased 50%)
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

# Post-Poker Reproduction Constants
POST_POKER_REPRODUCTION_ENERGY_THRESHOLD = 40.0  # Minimum energy to offer reproduction after poker
POST_POKER_REPRODUCTION_WINNER_PROB = 0.4  # Probability winner offers reproduction (40%)
POST_POKER_REPRODUCTION_LOSER_PROB = 0.2  # Probability loser offers reproduction (20%)
POST_POKER_CROSSOVER_WINNER_WEIGHT = 0.6  # Winner contributes 60% of DNA, loser 40%
POST_POKER_MATING_DISTANCE = 80  # Maximum distance for post-poker mating (pixels)

# Fish Life Stage Age Thresholds (in frames at 30fps)
LIFE_STAGE_BABY_MAX = 300  # 10 seconds
LIFE_STAGE_JUVENILE_MAX = 900  # 30 seconds
LIFE_STAGE_YOUNG_ADULT_MAX = 1800  # 60 seconds (1 minute)
LIFE_STAGE_ADULT_MAX = 3600  # 120 seconds (2 minutes)
LIFE_STAGE_MATURE_MAX = 5400  # 180 seconds (3 minutes)
# After MATURE_MAX = Elder

# Fish Energy System Constants
ENERGY_MAX_DEFAULT = 100.0  # Maximum energy for a fish
ENERGY_IDLE_CONSUMPTION = 1.0  # Energy consumed per frame when idle
ENERGY_LOW_MULTIPLIER = 0.01  # Low energy consumption multiplier
ENERGY_MODERATE_MULTIPLIER = 0.025  # Moderate energy consumption multiplier
ENERGY_HIGH_MULTIPLIER = 0.015  # High energy consumption multiplier
ENERGY_MATE_SEARCH_COST = -0.85  # Energy cost per frame when searching for mate
ENERGY_MOVEMENT_BASE_COST = 0.05  # Base energy cost for movement

# Fish Reproduction Constants
REPRODUCTION_MIN_ENERGY = 35.0  # Minimum energy to initiate reproduction
REPRODUCTION_COOLDOWN = 360  # Frames between reproduction attempts (12 seconds)
REPRODUCTION_GESTATION = 300  # Frames for pregnancy (10 seconds)
REPRODUCTION_ENERGY_COST = 60.0  # Energy cost to give birth
MATING_DISTANCE = 60.0  # Maximum distance for mating (pixels)

# Fish Memory and Learning Constants
FISH_MAX_FOOD_MEMORIES = 5  # Remember up to 5 good food locations
FISH_FOOD_MEMORY_DECAY = 600  # Forget food locations after 20 seconds (600 frames)
FISH_MEMORY_MAX_PER_TYPE = 10  # Max memories per type in enhanced memory system
FISH_MEMORY_DECAY_RATE = 0.001  # Memory decay rate for enhanced system
FISH_MEMORY_LEARNING_RATE = 0.05  # Learning rate for memory system
FISH_LAST_EVENT_INITIAL_AGE = -1000  # Initial age value for tracking last events

# Fish Combat and Predator Tracking
PREDATOR_ENCOUNTER_WINDOW = 150  # Frames (5 seconds) - recent conflict window for death attribution

# Fish Visual Constants
FISH_BABY_SIZE = 0.5  # Size multiplier for baby fish
FISH_ADULT_SIZE = 1.0  # Size multiplier for adult fish
FISH_BASE_WIDTH = 50  # Base width for fish sprite
FISH_BASE_HEIGHT = 50  # Base height for fish sprite

# Crab Constants
CRAB_INITIAL_ENERGY = 150.0  # Starting energy for crabs
CRAB_ATTACK_ENERGY_TRANSFER = 60.0  # Energy stolen from fish when attacked
CRAB_ATTACK_DAMAGE = 20.0  # Damage dealt to fish
CRAB_IDLE_CONSUMPTION = 0.01  # Energy consumed per frame when idle
CRAB_ATTACK_COOLDOWN = 120  # Frames between attacks (4 seconds)

# Plant Constants
PLANT_FOOD_PRODUCTION_INTERVAL = 75  # Frames between food production (2.5 seconds)
PLANT_FOOD_PRODUCTION_ENERGY = 15  # Energy cost to produce food
PLANT_PRODUCTION_CHANCE = 0.35  # 35% chance to produce food each interval

# Ecosystem Constants
TOTAL_ALGORITHM_COUNT = 48  # Total number of behavior algorithms available
TOTAL_SPECIES_COUNT = 4  # Total number of fish species
MAX_ECOSYSTEM_EVENTS = 1000  # Maximum events to track in ecosystem history

# Predator Avoidance Constants (for algorithms)
FLEE_THRESHOLD_CRITICAL = 45  # Flee distance when energy is critical
FLEE_THRESHOLD_LOW = 80  # Flee distance when energy is low
FLEE_THRESHOLD_NORMAL = 120  # Flee distance when energy is normal
FLEE_SPEED_CRITICAL = 1.1  # Flee speed when energy is critical
FLEE_SPEED_NORMAL = 1.3  # Flee speed when energy is normal

# Movement Calculation Constants
MOVEMENT_ESCAPE_DIRECT_WEIGHT = 0.7  # Weight of direct escape direction
MOVEMENT_ESCAPE_PERPENDICULAR_WEIGHT = 0.3  # Weight of perpendicular escape component
MOVEMENT_SLOW_SPEED_MULTIPLIER = 0.3  # Speed when too close or backing away
MOVEMENT_FOV_ANGLE = 1.57  # Field of view angle in radians (~90 degrees)
MOVEMENT_DISTANCE_EPSILON = 0.01  # Minimum distance threshold for movement calculations

# Poker Aggression Factors
POKER_AGGRESSION_LOW = 0.3  # Low aggression factor
POKER_AGGRESSION_MEDIUM = 0.6  # Medium aggression factor
POKER_AGGRESSION_HIGH = 0.9  # High aggression factor

# Spawning Constants
MAX_DIVERSITY_SPAWN_ATTEMPTS = 10  # Maximum attempts to spawn diverse fish
SPAWN_MARGIN_PIXELS = 100  # Margin from screen edges for spawning

# Poker Event Tracking
MAX_POKER_EVENTS = 10  # Maximum number of recent poker events to keep
POKER_EVENT_MAX_AGE_FRAMES = 180  # Maximum age for poker events (6 seconds at 30fps)

# Server Configuration
DEFAULT_API_PORT = 8000  # Default port for FastAPI backend

# UI Display Constants
SEPARATOR_WIDTH = 60  # Width of separator lines in console output
