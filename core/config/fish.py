"""Fish-specific configuration constants."""

# Fish movement constraints
FISH_TOP_MARGIN = 20  # Minimum pixels from top to keep energy bar visible

# Fish growth rate when eating food
FISH_GROWTH_RATE = 0.1

# Fish Energy and Metabolism Constants
INITIAL_ENERGY_RATIO = 0.5  # Start with 50% energy
BABY_METABOLISM_MULTIPLIER = 0.7  # Babies need less energy
ELDER_METABOLISM_MULTIPLIER = 1.2  # Elders need more energy

# Energy Consumption Constants
EXISTENCE_ENERGY_COST = 0.02  # Cost just for being alive per frame
MOVEMENT_ENERGY_COST = 0.02  # Movement-based energy consumption multiplier (was 0.015)
HIGH_SPEED_ENERGY_COST = 0.015  # Additional quadratic cost for fast movement
HIGH_SPEED_THRESHOLD = 0.7  # Speed ratio above which high-speed cost applies (70% of max)
SHARP_TURN_ENERGY_COST = 0.05  # Additional cost for sharp turns
SHARP_TURN_DOT_THRESHOLD = -0.85  # Dot product threshold for detecting sharp turns

# Direction Change Energy Constants
DIRECTION_CHANGE_ENERGY_BASE = 0.05  # Base energy cost for direction changes (was 0.03)
DIRECTION_CHANGE_SIZE_MULTIPLIER = 1.5  # Larger fish use more energy to turn (multiplied by size)
MOVEMENT_SIZE_MULTIPLIER = 1.2  # Additional size-based movement cost multiplier

# Energy Thresholds (centralized for consistency across the codebase)
STARVATION_THRESHOLD = 15.0  # Below this, fish dies from starvation
CRITICAL_ENERGY_THRESHOLD = 15.0  # Emergency survival mode (same as starvation threshold)
LOW_ENERGY_THRESHOLD = 30.0  # Fish should prioritize finding food
SAFE_ENERGY_THRESHOLD = 60.0  # Comfortable energy level for exploration and breeding

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

# Post-Poker Reproduction Constants
POST_POKER_REPRODUCTION_ENERGY_THRESHOLD = 40.0  # Minimum energy to offer reproduction after poker
POST_POKER_REPRODUCTION_WINNER_PROB = 0.4  # Probability winner offers reproduction (40%)
POST_POKER_REPRODUCTION_LOSER_PROB = 0.2  # Probability loser offers reproduction (20%)
POST_POKER_CROSSOVER_WINNER_WEIGHT = 0.7  # Winner contributes 70% of DNA, loser 30%
POST_POKER_MATING_DISTANCE = 80  # Maximum distance for post-poker mating (pixels)
POST_POKER_PARENT_ENERGY_CONTRIBUTION = 0.15  # Energy contribution from each parent (15%)
POST_POKER_MUTATION_RATE = 0.1  # Mutation rate for post-poker offspring
POST_POKER_MUTATION_STRENGTH = 0.1  # Mutation strength for post-poker offspring

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

# Baby Fish Spawning Constants
BABY_POSITION_RANDOM_RANGE = 20  # Random offset range for baby position (pixels)
BABY_SPAWN_MARGIN = 50  # Margin from screen edges for baby spawning (pixels)

# Movement algorithm constants
AVOIDANCE_SPEED_CHANGE = 0.2  # Rate at which speed changes when avoiding
ALIGNMENT_SPEED_CHANGE = 0.1  # Rate at which speed changes when aligning
RANDOM_MOVE_PROBABILITIES = [0.05, 0.9, 0.05]  # [left, straight, right]
RANDOM_VELOCITY_DIVISOR = 10.0  # Velocity change divisor for random movements

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
