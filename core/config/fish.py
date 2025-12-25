"""Fish-specific configuration constants."""

# Fish movement constraints
FISH_BASE_SPEED = 2.2  # Base speed for all fish (was 1.5)
FISH_TOP_MARGIN = 20  # Minimum pixels from top to keep energy bar visible

# Fish growth rate when eating food
FISH_GROWTH_RATE = 0.1

# Fish Energy and Metabolism Constants
INITIAL_ENERGY_RATIO = 0.5  # Start with 50% energy
BABY_METABOLISM_MULTIPLIER = 0.5  # Babies need less energy
ELDER_METABOLISM_MULTIPLIER = 1.5  # Elders need more energy

# =============================================================================
# SIMPLIFIED ENERGY CONSUMPTION SYSTEM
# =============================================================================
# There are 3 clear energy costs:
# 1. EXISTENCE - just being alive (scales linearly with size)
# 2. MOVEMENT - regular swimming (linear with speed, size^1.5)
# 3. SPRINT - penalty for going above threshold (quadratic)
#
# This replaces the previous complex system with 6+ stacked multipliers.
# =============================================================================

# 1. Existence cost - just being alive each frame
EXISTENCE_ENERGY_COST = 0.06  # Per-frame cost (tuned for balance)
EXISTENCE_SIZE_EXPONENT = 1.0  # Linear with size (bigger fish pay more)

# 2. Movement cost - swimming around
MOVEMENT_ENERGY_COST = 0.10  # Base rate per frame when moving
MOVEMENT_SIZE_EXPONENT = 1.5  # Size^1.5 scaling (moderate penalty for large fish)

# 3. Sprint penalty - going above cruise threshold
SPRINT_THRESHOLD = 0.70  # Above 70% speed incurs sprint penalty
SPRINT_ENERGY_COST = 0.25  # Quadratic penalty rate above threshold
# (uses same size exponent as movement)

# 4. Direction change cost - turning uses energy (applied separately in fish.py)
DIRECTION_CHANGE_ENERGY_BASE = 0.08  # Base cost for direction changes
DIRECTION_CHANGE_SIZE_MULTIPLIER = 1.5  # Uses same exponent as movement

# Energy Thresholds as RATIOS (0.0 to 1.0 of max_energy)
# Using ratios ensures consistent behavior regardless of fish size.
# A large fish at 10% energy is just as desperate as a small fish at 10%.
STARVATION_THRESHOLD_RATIO = 0.10  # Below 10%, fish dies from starvation
CRITICAL_ENERGY_THRESHOLD_RATIO = 0.10  # Emergency survival mode (same as starvation)
LOW_ENERGY_THRESHOLD_RATIO = 0.20  # Below 20%, fish should prioritize finding food
SAFE_ENERGY_THRESHOLD_RATIO = 0.40  # Above 40%, comfortable for exploration and breeding

# Fish Life Stage Age Thresholds (in frames at 30fps)
LIFE_STAGE_BABY_MAX = 600  # 20 seconds (babies grow slower)
LIFE_STAGE_JUVENILE_MAX = 900  # 30 seconds
LIFE_STAGE_YOUNG_ADULT_MAX = 1800  # 60 seconds (1 minute)
LIFE_STAGE_ADULT_MAX = 3600  # 120 seconds (2 minutes)
LIFE_STAGE_MATURE_MAX = 5400  # 180 seconds (3 minutes)
# After MATURE_MAX = Elder

# Fish Energy System Constants
# Fish max energy scales as: ENERGY_MAX_DEFAULT * lifecycle size (size grows with age and genetic size_modifier).
ENERGY_MAX_DEFAULT = 150.0  # Maximum energy for a baseline adult fish (was 100.0)
# When fish would overflow above max_energy, bank that excess for future reproduction instead of dropping it as food.
# The bank is capped to avoid unbounded accumulation on fish that can't reproduce immediately.
OVERFLOW_ENERGY_BANK_MULTIPLIER = 3.0
ENERGY_IDLE_CONSUMPTION = 1.0  # Energy consumed per frame when idle
ENERGY_LOW_MULTIPLIER = 0.01  # Low energy consumption multiplier
ENERGY_MODERATE_MULTIPLIER = 0.035  # Moderate energy consumption multiplier (was 0.025)
ENERGY_HIGH_MULTIPLIER = 0.015  # High energy consumption multiplier
ENERGY_MATE_SEARCH_COST = -0.85  # Energy cost per frame when searching for mate
ENERGY_MOVEMENT_BASE_COST = 0.05  # Base energy cost for movement

# Fish Reproduction Constants
REPRODUCTION_MIN_ENERGY = 35.0  # Minimum energy to initiate reproduction
REPRODUCTION_COOLDOWN = 0  # No cooldown - reproduce whenever bank has enough energy
REPRODUCTION_ENERGY_COST = 60.0  # Energy cost to give birth
MATING_DISTANCE = 60.0  # Maximum distance for mating (pixels)

# Lowered to 0.70 to make reproduction achievable while still requiring healthy fish
POST_POKER_REPRODUCTION_ENERGY_THRESHOLD = 0.70
POST_POKER_REPRODUCTION_WINNER_PROB = 0.4  # Probability winner offers reproduction (40%)
POST_POKER_REPRODUCTION_LOSER_PROB = 0.2  # Probability loser offers reproduction (20%)
POST_POKER_CROSSOVER_WINNER_WEIGHT = 0.7  # Winner contributes 70% of DNA, loser 30%
POST_POKER_MATING_DISTANCE = 80  # Maximum distance for post-poker mating (pixels)
POST_POKER_PARENT_ENERGY_CONTRIBUTION = 0.15  # Energy contribution from each parent (15%)
POST_POKER_MUTATION_RATE = 0.1  # Mutation rate for post-poker offspring
POST_POKER_MUTATION_STRENGTH = 0.1  # Mutation strength for post-poker offspring

# Fish Memory and Learning Constants

FISH_MEMORY_MAX_PER_TYPE = 10  # Max memories per type in enhanced memory system
FISH_MEMORY_DECAY_RATE = 0.001  # Memory decay rate for enhanced system
FISH_MEMORY_LEARNING_RATE = 0.05  # Learning rate for memory system
FISH_LAST_EVENT_INITIAL_AGE = -1000  # Initial age value for tracking last events

# Fish Combat and Predator Tracking
PREDATOR_ENCOUNTER_WINDOW = 150  # Frames (5 seconds) - recent conflict window for death attribution

# Fish Visual Constants
# Babies should start at half size to align with energy and rendering expectations in tests
FISH_BABY_SIZE = 0.5  # Size multiplier for baby fish (smaller babies)
FISH_ADULT_SIZE = 1.0  # Size multiplier for adult fish
FISH_SIZE_MODIFIER_MIN = 0.5  # Genetic size modifier lower bound (was 0.7)
FISH_SIZE_MODIFIER_MAX = 2.0  # Genetic size modifier upper bound (was 1.3)
# Eye size allowed bounds (visual trait)
EYE_SIZE_MIN = 0.5
EYE_SIZE_MAX = 2.0
# Body aspect allowed bounds (visual trait)
BODY_ASPECT_MIN = 0.5
BODY_ASPECT_MAX = 2.0
# Lifespan modifier allowed bounds (genetic trait)
LIFESPAN_MODIFIER_MIN = 0.5
LIFESPAN_MODIFIER_MAX = 2.0
FISH_BASE_WIDTH = 50  # Base width for fish sprite
FISH_BASE_HEIGHT = 50  # Base height for fish sprite
FISH_TEMPLATE_COUNT = 6  # Number of parametric fish templates (0-5)
FISH_PATTERN_COUNT = 6  # Number of pattern types (0-5)

# Baby Fish Spawning Constants
BABY_POSITION_RANDOM_RANGE = 20  # Random offset range for baby position (pixels)
BABY_SPAWN_MARGIN = 50  # Margin from screen edges for baby spawning (pixels)

# Movement algorithm constants
AVOIDANCE_SPEED_CHANGE = 0.1  # Rate at which speed changes when avoiding
ALIGNMENT_SPEED_CHANGE = 0.05  # Rate at which speed changes when aligning
RANDOM_MOVE_PROBABILITIES = [0.05, 0.9, 0.05]  # [left, straight, right]
RANDOM_VELOCITY_DIVISOR = 15.0  # Velocity change divisor for random movements

# Predator Avoidance Constants (for algorithms)
FLEE_THRESHOLD_CRITICAL = 45  # Flee distance when energy is critical
FLEE_THRESHOLD_LOW = 80  # Flee distance when energy is low
FLEE_THRESHOLD_NORMAL = 120  # Flee distance when energy is normal
FLEE_SPEED_CRITICAL = 0.95  # Flee speed when energy is critical
FLEE_SPEED_NORMAL = 0.9  # Flee speed when energy is normal

# Movement Calculation Constants
MOVEMENT_ESCAPE_DIRECT_WEIGHT = 0.7  # Weight of direct escape direction
MOVEMENT_ESCAPE_PERPENDICULAR_WEIGHT = 0.3  # Weight of perpendicular escape component
MOVEMENT_SLOW_SPEED_MULTIPLIER = 0.3  # Speed when too close or backing away
MOVEMENT_FOV_ANGLE = 1.57  # Field of view angle in radians (~90 degrees)
MOVEMENT_DISTANCE_EPSILON = 0.01  # Minimum distance threshold for movement calculations
