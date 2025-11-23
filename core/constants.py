# Screen dimensions in pixels (must match Canvas size in frontend)
SCREEN_WIDTH = 1088
SCREEN_HEIGHT = 612

# The frame rate for the game loop, in frames per second
FRAME_RATE = 30

# The number of schooling fish to create at the start of the game
NUM_SCHOOLING_FISH = 10  # Start with 10 fish

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
AUTO_FOOD_ULTRA_LOW_ENERGY_THRESHOLD = (
    1500  # Quadruple spawn rate below this total energy (critical)
)
AUTO_FOOD_LOW_ENERGY_THRESHOLD = 3500  # Triple spawn rate below this total energy
AUTO_FOOD_HIGH_ENERGY_THRESHOLD_1 = 4500  # Reduce spawn rate above this total energy
AUTO_FOOD_HIGH_ENERGY_THRESHOLD_2 = 6500  # Further reduce spawn rate above this total energy
AUTO_FOOD_HIGH_POP_THRESHOLD_1 = 15  # Reduce spawn rate above this fish count
AUTO_FOOD_HIGH_POP_THRESHOLD_2 = 20  # Further reduce spawn rate above this fish count
LIVE_FOOD_SPAWN_CHANCE = 0.4  # 40% of auto-spawned food will be live/active

# Food type definitions with nutrient properties
FOOD_TYPES = {
    "algae": {
        "name": "Algae Flake",
        "files": ["food_algae1.png", "food_algae2.png"],
        "energy": 45.0,  # Low energy - basic food source
        "rarity": 0.35,  # 35% spawn rate
        "sink_multiplier": 0.8,  # Sinks slower (lighter)
        "stationary": False,
    },
    "protein": {
        "name": "Protein Flake",
        "files": ["food_protein1.png", "food_protein2.png"],
        "energy": 75.0,  # Good energy - valuable food
        "rarity": 0.25,  # 25% spawn rate
        "sink_multiplier": 1.2,  # Sinks faster (heavier)
        "stationary": False,
    },
    "vitamin": {
        "name": "Vitamin Flake",
        "files": ["food_vitamin1.png", "food_vitamin2.png"],
        "energy": 60.0,  # Moderate energy
        "rarity": 0.20,  # 20% spawn rate
        "sink_multiplier": 0.9,  # Sinks slightly slower
        "stationary": False,
    },
    "energy": {
        "name": "Energy Flake",
        "files": ["food_energy1.png", "food_energy2.png"],
        "energy": 70.0,  # Good energy
        "rarity": 0.15,  # 15% spawn rate
        "sink_multiplier": 1.0,  # Normal sink rate
        "stationary": False,
    },
    "rare": {
        "name": "Rainbow Flake",
        "files": ["food_rare1.png", "food_rare2.png"],
        "energy": 115.0,  # High energy - rare treat
        "rarity": 0.05,  # 5% spawn rate (rare)
        "sink_multiplier": 1.1,  # Sinks bit faster
        "stationary": False,
    },
    "nectar": {
        "name": "Plant Nectar",
        "files": ["food_vitamin1.png", "food_vitamin2.png"],
        "energy": 90.0,  # Rewarding stationary food
        "rarity": 0.15,  # Used for plant-only spawn weighting
        "sink_multiplier": 0.0,  # Remains in place
        "stationary": True,
    },
    "live": {
        "name": "Live Treat",
        "files": ["food_energy1.png", "food_energy2.png"],
        "energy": 110.0,  # High energy density - small but nutritious zooplankton
        "rarity": 0.12,  # Appears occasionally
        "sink_multiplier": 0.0,  # Self-propelled, so no sinking
        "stationary": False,
    },
}

# Filenames for the animation frames of each type of sprite
FILES = {
    "solo_fish": ["george1.png", "george2.png"],
    "crab": ["crab1.png", "crab2.png"],
    "schooling_fish": ["school.png"],
    "plant": ["plant1-improved.png", "plant2.png"],
    "castle": ["castle-improved.png"],
}

# The initial positions of the sprites in the game
INIT_POS = {
    "fish": (275, 80),
    "crab": (250, 542),
    "school": (300, 200),
    "plant1": (250, 510),
    "plant2": (10, 510),
    "plant3": (500, 510),  # Add third plant
    "plant4": (700, 510),  # Add fourth plant
    "castle": (100, 420),
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
HEALTH_LOW_COLOR = (200, 200, 50)  # Yellow (30-60%)
HEALTH_GOOD_COLOR = (50, 200, 50)  # Green (above 60%)

# Fish movement constraints
FISH_TOP_MARGIN = 20  # Minimum pixels from top to keep energy bar visible

# Fish Energy and Metabolism Constants
INITIAL_ENERGY_RATIO = 0.5  # Start with 50% energy
BABY_METABOLISM_MULTIPLIER = 0.7  # Babies need less energy
ELDER_METABOLISM_MULTIPLIER = 1.2  # Elders need more energy

# Energy Consumption Constants
EXISTENCE_ENERGY_COST = 0.02  # Cost just for being alive per frame
MOVEMENT_ENERGY_COST = 0.015  # Movement-based energy consumption multiplier
SHARP_TURN_ENERGY_COST = 0.05  # Additional cost for sharp turns
SHARP_TURN_DOT_THRESHOLD = -0.85  # Dot product threshold for detecting sharp turns

# Direction Change Energy Constants
DIRECTION_CHANGE_ENERGY_BASE = 0.03  # Base energy cost for direction changes
DIRECTION_CHANGE_SIZE_MULTIPLIER = 1.5  # Larger fish use more energy to turn (multiplied by size)
MOVEMENT_SIZE_MULTIPLIER = 1.2  # Additional size-based movement cost multiplier

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
FISH_TEMPLATE_COUNT = 6  # Number of parametric fish templates (0-5)
FISH_PATTERN_COUNT = 4  # Number of pattern types (0-3)

# Crab Constants
CRAB_INITIAL_ENERGY = 150.0  # Starting energy for crabs
CRAB_ATTACK_ENERGY_TRANSFER = 60.0  # Energy stolen from fish when attacked
CRAB_ATTACK_DAMAGE = 20.0  # Damage dealt to fish
CRAB_IDLE_CONSUMPTION = 0.01  # Energy consumed per frame when idle
CRAB_ATTACK_COOLDOWN = 120  # Frames between attacks (4 seconds)

# Plant Constants
PLANT_FOOD_PRODUCTION_INTERVAL = 50  # Frames between food production (1.67 seconds)
PLANT_FOOD_PRODUCTION_ENERGY = 15  # Energy cost to produce food
PLANT_PRODUCTION_CHANCE = 0.50  # 50% chance to produce food each interval

# Ecosystem Constants
TOTAL_ALGORITHM_COUNT = (
    50  # Total number of behavior algorithms available (updated with 2 new algorithms)
)
TOTAL_SPECIES_COUNT = 4  # Total number of fish species
MAX_ECOSYSTEM_EVENTS = 1000  # Maximum events to track in ecosystem history
MAX_POPULATION = 100  # Maximum population capacity for ecosystem
CRITICAL_POPULATION_THRESHOLD = 10  # Minimum population before emergency spawning
EMERGENCY_SPAWN_COOLDOWN = 180  # Frames between emergency spawns (6 seconds at 30fps)

# Predator Avoidance Constants (for algorithms)
FLEE_THRESHOLD_CRITICAL = 45  # Flee distance when energy is critical
FLEE_THRESHOLD_LOW = 80  # Flee distance when energy is low
FLEE_THRESHOLD_NORMAL = 120  # Flee distance when energy is normal
FLEE_SPEED_CRITICAL = 1.1  # Flee speed when energy is critical
FLEE_SPEED_NORMAL = 1.3  # Flee speed when energy is normal

# Food Seeking Constants
CHASE_DISTANCE_CRITICAL = 400  # Maximum chase distance when energy is critical
CHASE_DISTANCE_LOW = 250  # Maximum chase distance when energy is low
CHASE_DISTANCE_SAFE_BASE = 150  # Base chase distance when energy is safe
PROXIMITY_BOOST_DIVISOR = 100  # Divisor for proximity boost calculation
PROXIMITY_BOOST_MULTIPLIER = 0.5  # Multiplier for proximity boost
URGENCY_BOOST_CRITICAL = 0.3  # Speed boost when energy is critical
URGENCY_BOOST_LOW = 0.15  # Speed boost when energy is low

# Food Detection Range (affected by time of day)
BASE_FOOD_DETECTION_RANGE = 400.0  # Base detection range during daytime (pixels)
# Actual range = BASE_FOOD_DETECTION_RANGE * time_system.get_detection_range_modifier()
# Night: 100 pixels (25%), Dawn/Dusk: 300 pixels (75%), Day: 400 pixels (100%)

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

# Poker Game Mechanics
POKER_MAX_ACTIONS_PER_ROUND = 10  # Maximum betting actions per round (prevents infinite loops)

# Poker Betting Constants
POKER_BET_MIN_SIZE = 0.35  # Minimum fish size for bet percentage calculation
POKER_BET_MIN_PERCENTAGE = 0.15  # Minimum bet percentage (15% at size 0.35)
POKER_BET_SIZE_MULTIPLIER = 0.158  # Bet percentage increase per size unit (15-30% range)

# Poker Action Decision Constants
# Strong hand betting (high card or better)
POKER_STRONG_RAISE_PROBABILITY = 0.8  # Probability of raising with strong hand when no bet
POKER_STRONG_POT_MULTIPLIER = 0.5  # Pot multiplier for strong hand raise
POKER_STRONG_ENERGY_FRACTION = 0.3  # Energy fraction for strong hand raise (no bet)
POKER_STRONG_ENERGY_FRACTION_RERAISE = 0.4  # Energy fraction for strong hand reraise
POKER_STRONG_CALL_MULTIPLIER = 2.0  # Call amount multiplier for strong hand raise

# Medium hand betting (pair through straight)
POKER_MEDIUM_AGGRESSION_MULTIPLIER = 0.6  # Aggression multiplier for medium hand raise
POKER_MEDIUM_POT_MULTIPLIER = 0.3  # Pot multiplier for medium hand raise
POKER_MEDIUM_ENERGY_FRACTION = 0.2  # Energy fraction for medium hand raise
POKER_MEDIUM_ENERGY_FRACTION_RERAISE = 0.25  # Energy fraction for medium hand reraise
POKER_MEDIUM_CALL_MULTIPLIER = 1.5  # Call amount multiplier for medium hand raise
POKER_MEDIUM_RAISE_PROBABILITY = 0.4  # Aggression multiplier for reraise probability
POKER_MEDIUM_POT_ODDS_FOLD_THRESHOLD = 0.5  # Pot odds threshold for folding

# Weak hand betting (high card)
POKER_WEAK_BLUFF_PROBABILITY = 0.2  # Aggression multiplier for bluff probability (no bet)
POKER_WEAK_POT_MULTIPLIER = 0.4  # Pot multiplier for weak hand bluff
POKER_WEAK_ENERGY_FRACTION = 0.15  # Energy fraction for weak hand bluff
POKER_WEAK_CALL_PROBABILITY = 0.15  # Aggression multiplier for bluff call probability

# Poker House Cut Constants
POKER_HOUSE_CUT_MIN_PERCENTAGE = 0.08  # Minimum house cut (8% at size 0.35)
POKER_HOUSE_CUT_SIZE_MULTIPLIER = 0.18  # House cut increase per size unit (8-25% range)

# Poker Hand Evaluation
POKER_MAX_HAND_RANK = 9.0  # Maximum hand rank value for normalization
POKER_WEAK_HAND_THRESHOLD = 0.3  # Threshold for considering a hand weak (for bluff detection)

# Post-Poker Reproduction Energy Constants
POST_POKER_PARENT_ENERGY_CONTRIBUTION = 0.15  # Energy contribution from each parent (15%)
POST_POKER_MUTATION_RATE = 0.1  # Mutation rate for post-poker offspring
POST_POKER_MUTATION_STRENGTH = 0.1  # Mutation strength for post-poker offspring

# Population Stress Constants
POPULATION_STRESS_MAX_MULTIPLIER = 0.8  # Maximum population stress from low population
POPULATION_STRESS_DEATH_RATE_MAX = 0.4  # Maximum stress contribution from death rate
POPULATION_STRESS_MAX_TOTAL = 1.0  # Maximum total population stress

# Baby Fish Spawning Constants
BABY_POSITION_RANDOM_RANGE = 20  # Random offset range for baby position (pixels)
BABY_SPAWN_MARGIN = 50  # Margin from screen edges for baby spawning (pixels)

# Spawning Constants
MAX_DIVERSITY_SPAWN_ATTEMPTS = 10  # Maximum attempts to spawn diverse fish
SPAWN_MARGIN_PIXELS = 100  # Margin from screen edges for spawning

# Spatial Query Constants (for collision detection and mating)
COLLISION_QUERY_RADIUS = 100  # Radius for nearby entity queries during collision detection (pixels)
MATING_QUERY_RADIUS = 150  # Radius for finding potential mates (pixels)

# Poker Event Tracking
MAX_POKER_EVENTS = 10  # Maximum number of recent poker events to keep
POKER_EVENT_MAX_AGE_FRAMES = 180  # Maximum age for poker events (6 seconds at 30fps)

# Server Configuration
DEFAULT_API_PORT = 8000  # Default port for FastAPI backend

# UI Display Constants
SEPARATOR_WIDTH = 60  # Width of separator lines in console output

# Feature Flags
POKER_ACTIVITY_ENABLED = True  # Enable poker activity
FRACTAL_PLANTS_ENABLED = True  # Enable fractal plant system

# =============================================================================
# FRACTAL PLANT CONSTANTS
# =============================================================================

# Root Spot Configuration
FRACTAL_PLANT_ROOT_SPOT_COUNT = 25  # Number of positions where plants can grow
FRACTAL_PLANT_ROOT_Y_BASE = SCREEN_HEIGHT - 15  # Y position near tank bottom
FRACTAL_PLANT_ROOT_Y_VARIANCE = 8  # Slight Y variation for natural look

# Plant Energy System
FRACTAL_PLANT_INITIAL_ENERGY = 20.0  # Starting energy for new plants
FRACTAL_PLANT_MAX_ENERGY = 120.0  # Maximum energy capacity - Reduced for smaller plants
FRACTAL_PLANT_MIN_SIZE = 0.3  # Minimum size multiplier
FRACTAL_PLANT_MAX_SIZE = 1.0  # Maximum size multiplier - Reduced from 1.2
FRACTAL_PLANT_DEATH_ENERGY = 5.0  # Energy threshold for death

# Plant Dimensions
FRACTAL_PLANT_BASE_WIDTH = 60  # Base width in pixels
FRACTAL_PLANT_BASE_HEIGHT = 65  # Base height in pixels

# Plant Poker Configuration
FRACTAL_PLANT_POKER_COOLDOWN = 90  # 3 seconds at 30fps
FRACTAL_PLANT_MIN_POKER_ENERGY = 0.0  # Plants can always play poker (no min energy)
FRACTAL_PLANT_POKER_BET_RATIO = 0.15  # Max bet as ratio of energy

# Plant Reproduction
FRACTAL_PLANT_NECTAR_COOLDOWN = 600  # 20 seconds between nectar production - Increased from 300
FRACTAL_PLANT_NECTAR_ENERGY = 50.0  # Energy provided by nectar
FRACTAL_PLANT_SPROUTING_CHANCE = 0.5  # Chance to sprout when nectar consumed - Reduced from 0.8
FRACTAL_PLANT_INITIAL_COUNT = 5  # Number of plants to start with

# Plant Energy Collection (Passive Growth)
FRACTAL_PLANT_BASE_ENERGY_RATE = 0.002  # Base energy gain per frame - Reduced for slower growth
FRACTAL_PLANT_GROWTH_FACTOR = 0.3  # Compound growth rate modifier
FRACTAL_PLANT_DAY_MODIFIER = 1.0  # Energy collection during day
FRACTAL_PLANT_DAWN_DUSK_MODIFIER = 0.7  # Energy collection at dawn/dusk
FRACTAL_PLANT_NIGHT_MODIFIER = 0.3  # Energy collection at night

# L-System Fractal Rendering
FRACTAL_PLANT_MIN_ITERATIONS = 1  # Minimum L-system iterations (small plants)
FRACTAL_PLANT_MAX_ITERATIONS = 3  # Maximum L-system iterations (large plants)
FRACTAL_PLANT_DEFAULT_ANGLE = 25.0  # Default branching angle (degrees)
FRACTAL_PLANT_DEFAULT_LENGTH_RATIO = 0.7  # Default length reduction per iteration

# Plant Collision Detection
FRACTAL_PLANT_POKER_COLLISION_DISTANCE = 100.0  # Distance for poker collision - Increased for center-to-center check
