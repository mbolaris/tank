"""Food system configuration constants.

This module defines constants for food physics, spawning, and fish food-seeking behavior.
The values here directly affect ecosystem balance and evolutionary pressure.

Design Philosophy:
    Food scarcity drives natural selection. Too much food = weak selection pressure.
    Too little = population collapse. The constants below are tuned to create
    moderate scarcity that rewards efficient foraging algorithms.
"""

# =============================================================================
# FOOD PHYSICS
# =============================================================================
# Sinking creates vertical food distribution, rewarding surface-skimmer and
# bottom-feeder strategies differently. Faster sink = more bottom food.
FOOD_SINK_ACCELERATION = 0.01  # Pixels/frame². Slow sink gives fish time to intercept.

# =============================================================================
# AUTOMATIC FOOD SPAWNING
# =============================================================================
# The spawn system maintains ecosystem balance by adjusting food availability
# based on population health. This prevents both starvation collapse and
# overpopulation from unlimited resources.
#
# Trade-off: Faster spawning = easier survival but weaker selection pressure.
#            Slower spawning = stronger selection but risk of extinction.
AUTO_FOOD_SPAWN_RATE = 18  # Faster spawns (~1.7 food/sec) to reduce starvation and keep poker active
AUTO_FOOD_ENABLED = True

# Dynamic Spawn Scaling
# ---------------------
# These thresholds create a feedback loop: struggling populations get more food,
# thriving populations get less. This stabilizes population around TARGET_POPULATION.
#
# Energy thresholds are based on total ecosystem energy (sum of all fish energy).
# A healthy ecosystem of 80 fish at 50 energy each = 4000 total energy.
AUTO_FOOD_ULTRA_LOW_ENERGY_THRESHOLD = 2200  # Crisis: 4x spawn rate (population near collapse)
AUTO_FOOD_LOW_ENERGY_THRESHOLD = 4200       # Struggling: 3x spawn rate
AUTO_FOOD_HIGH_ENERGY_THRESHOLD_1 = 5200    # Comfortable: reduce spawn rate
AUTO_FOOD_HIGH_ENERGY_THRESHOLD_2 = 7500    # Thriving: further reduce (prevent overpopulation)
AUTO_FOOD_HIGH_POP_THRESHOLD_1 = 80         # 80 fish: reduce spawning
AUTO_FOOD_HIGH_POP_THRESHOLD_2 = 90         # 90 fish: further reduce (approaching MAX_POPULATION)

# Live food moves unpredictably, rewarding prediction_skill and pursuit_aggression traits.
# Higher values create more dynamic hunting scenarios but increase CPU load.
LIVE_FOOD_SPAWN_CHANCE = 0.4  # 40% live food creates variety without overwhelming complexity

# =============================================================================
# FOOD TYPES
# =============================================================================
# Different food types create foraging trade-offs:
# - Common low-energy food (algae) vs rare high-energy food (rainbow)
# - Fast-sinking (protein) vs slow-sinking (algae) affects vertical strategies
# - Stationary (nectar) vs moving (live) rewards different hunting algorithms
#
# The rarity values must sum to ~1.0 (excluding nectar/live which spawn separately).
# Current distribution: algae(35%) + protein(25%) + vitamin(20%) + energy(15%) + rare(5%) = 100%
FOOD_TYPES = {
    "algae": {
        "name": "Algae Flake",
        "files": ["food_algae1.png", "food_algae2.png"],
        "energy": 50.0,   # Low energy: common but inefficient food source
        "rarity": 0.35,   # Most common: baseline food, available even to weak foragers
        "sink_multiplier": 0.5,  # Slow sink: stays in upper water longer
        "stationary": False,
    },
    "protein": {
        "name": "Protein Flake",
        "files": ["food_protein1.png", "food_protein2.png"],
        "energy": 100.0,  # Good energy: worth chasing
        "rarity": 0.25,   # Common: reliable food source for capable hunters
        "sink_multiplier": 1.2,  # Fast sink: rewards bottom-feeders
        "stationary": False,
    },
    "vitamin": {
        "name": "Vitamin Flake",
        "files": ["food_vitamin1.png", "food_vitamin2.png"],
        "energy": 120.0,  # High energy: valuable target
        "rarity": 0.20,   # Moderate: competition creates selection pressure
        "sink_multiplier": 0.9,  # Slightly slow: more time to intercept
        "stationary": False,
    },
    "energy": {
        "name": "Energy Flake",
        "files": ["food_energy1.png", "food_energy2.png"],
        "energy": 100.0,  # Good energy: standard nutritious food
        "rarity": 0.15,   # Less common: rewards active searching
        "sink_multiplier": 1.0,  # Normal sink: baseline physics
        "stationary": False,
    },
    "rare": {
        "name": "Rainbow Flake",
        "files": ["food_rare1.png", "food_rare2.png"],
        "energy": 150.0,  # Highest energy: jackpot food
        "rarity": 0.05,   # Very rare: creates high-value targets worth competing for
        "sink_multiplier": 1.1,  # Slightly fast: time pressure to catch
        "stationary": False,
    },
    "nectar": {
        "name": "Plant Nectar",
        "files": ["food_vitamin1.png", "food_vitamin2.png"],
        "energy": 100.0,  # Good reward for plant interaction
        "rarity": 0.15,   # Weight for plant-only spawning (not in regular food pool)
        "sink_multiplier": 0.0,  # Stationary: attached to plant
        "stationary": True,
    },
    "live": {
        "name": "Live Treat",
        "files": ["food_energy1.png", "food_energy2.png"],
        "energy": 100.0,  # Worth the chase
        "rarity": 0.12,   # Occasional: adds variety without dominating
        "sink_multiplier": 0.0,  # Self-propelled: uses its own movement
        "stationary": False,
    },
}

# =============================================================================
# CHASE DISTANCE THRESHOLDS
# =============================================================================
# These create energy-dependent foraging behavior. Desperate fish chase farther
# (burning more energy) while comfortable fish are more selective.
#
# Trade-off: Longer chase = higher catch rate but more energy burned.
#            Tuned so desperate fish can recover, but wasteful chasing is punished.
CHASE_DISTANCE_CRITICAL = 400  # Desperate: will chase almost anything
CHASE_DISTANCE_LOW = 250       # Hungry: extends range moderately
CHASE_DISTANCE_SAFE_BASE = 150 # Comfortable: only chases nearby food (efficient)

# Speed boost mechanics when closing on food
PROXIMITY_BOOST_DIVISOR = 100   # Normalizes distance for boost calculation
PROXIMITY_BOOST_MULTIPLIER = 0.5  # Max 50% speed boost when very close
URGENCY_BOOST_CRITICAL = 0.3    # 30% speed boost when starving
URGENCY_BOOST_LOW = 0.15        # 15% speed boost when hungry

# =============================================================================
# FOOD DETECTION RANGE
# =============================================================================
# Vision range creates day/night gameplay difference.
# Night hunting is harder, rewarding memory-based foraging and schooling.
BASE_FOOD_DETECTION_RANGE = 450.0  # Daytime: full visibility (pixels)
# Actual range = BASE * time_modifier:
#   Night (25%):     100px - forces close-range hunting, rewards memory
#   Dawn/Dusk (75%): 300px - transitional
#   Day (100%):      400px - full range, rewards speed and pursuit

# =============================================================================
# PREDATOR AVOIDANCE vs FOOD PURSUIT
# =============================================================================
# These constants define the risk/reward trade-off between eating and surviving.
# Fish must balance "get food" against "avoid being food".
#
# The flee distances create a spectrum from reckless (low) to paranoid (high).
# Starving fish accept more risk; well-fed fish are more cautious.

# Predator Detection
PREDATOR_DEFAULT_FAR_DISTANCE = 999  # Sentinel: "no predator nearby"
PREDATOR_PROXIMITY_THRESHOLD = 100   # Within 100px = "predator is close"
PREDATOR_GUARDING_FOOD_DISTANCE = 80 # Predator within 80px of food = "food is guarded"
PREDATOR_DANGER_ZONE_RADIUS = 120    # Food within 120px of predator = risky
PREDATOR_DANGER_ZONE_DIVISOR = 1.2   # Scales danger score (higher = less scared)

# Flee Distance Spectrum (higher = more cautious)
# Desperate fish get close before fleeing, comfortable fish flee early.
PREDATOR_FLEE_DISTANCE_DESPERATE = 50     # Starving: risks getting very close
PREDATOR_FLEE_DISTANCE_CAUTIOUS = 75      # Hungry but careful
PREDATOR_FLEE_DISTANCE_NORMAL = 80        # Standard caution
PREDATOR_FLEE_DISTANCE_SAFE = 85          # Well-fed: slightly cautious
PREDATOR_FLEE_DISTANCE_CONSERVATIVE = 90  # Conservative personality
PREDATOR_FLEE_DISTANCE_VERY_SAFE = 110    # Paranoid: flees early

# =============================================================================
# FOOD PURSUIT BEHAVIOR
# =============================================================================
# Fine-grained control over hunting mechanics.
FOOD_MEMORY_RECORD_DISTANCE = 50   # Remember food locations from 50px away
FOOD_VELOCITY_THRESHOLD = 0.1      # Food moving <0.1 px/frame = "stationary"
FOOD_SPEED_BOOST_DISTANCE = 100    # Sprint when within 100px of food
FOOD_STRIKE_DISTANCE = 80          # Final lunge distance
FOOD_CIRCLING_APPROACH_DISTANCE = 200  # CircularHunter starts orbiting at 200px
FOOD_PURSUIT_RANGE_DESPERATE = 200 # Starving: detect food from 200px
FOOD_PURSUIT_RANGE_NORMAL = 150    # Normal: 150px detection
FOOD_PURSUIT_RANGE_CLOSE = 80      # Close range: guaranteed detection
FOOD_PURSUIT_RANGE_EXTENDED = 250  # Extended range for special algorithms

# =============================================================================
# FOOD QUALITY SCORING
# =============================================================================
# FoodQualityOptimizer algorithm uses these to score food targets.
# Score = (energy_value - distance_cost - danger_cost)
# Negative thresholds allow pursuing risky food when desperate.
FOOD_SAFETY_BONUS = 20             # +20 score if food is far from predators
FOOD_SAFETY_DISTANCE_RATIO = 0.7   # Food is "safe" if predator is 1.4x farther
FOOD_SCORE_THRESHOLD_CRITICAL = -80  # Starving: pursue even terrible options
FOOD_SCORE_THRESHOLD_LOW = -60       # Hungry: accept poor options
FOOD_SCORE_THRESHOLD_NORMAL = -50    # Normal: moderately selective

# =============================================================================
# DANGER ASSESSMENT WEIGHTS
# =============================================================================
# How much predator proximity affects food pursuit decisions.
# 0.0 = ignore danger completely, 1.0 = maximum caution.
#
# Starving fish ignore danger (must eat or die anyway).
# Well-fed fish are cautious (survival > small energy gain).
DANGER_WEIGHT_CRITICAL = 0.1  # Nearly ignore danger when starving
DANGER_WEIGHT_LOW = 0.4       # Moderate risk tolerance when hungry
DANGER_WEIGHT_NORMAL = 0.7    # Prioritize safety when comfortable

# =============================================================================
# SOCIAL FORAGING
# =============================================================================
# CooperativeForager algorithm uses these to follow successful foragers.
# Creates emergent schooling around food sources.
SOCIAL_FOLLOW_MAX_DISTANCE = 200      # Follow fish up to 200px away
SOCIAL_FOOD_PROXIMITY_THRESHOLD = 80  # Fish within 80px of food = "found food"
SOCIAL_SIGNAL_DETECTION_RANGE = 250   # Detect feeding behavior from 250px
