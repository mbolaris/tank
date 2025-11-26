"""Food system configuration constants."""

# Food physics
FOOD_SINK_ACCELERATION = 0.01

# Automatic food spawning
AUTO_FOOD_SPAWN_RATE = 90  # Spawn food every 3 seconds (90 frames at 30fps) - Base rate
AUTO_FOOD_ENABLED = True  # Enable/disable automatic food spawning

# Dynamic food spawn scaling based on population and energy
AUTO_FOOD_ULTRA_LOW_ENERGY_THRESHOLD = 1500  # Quadruple spawn rate below this total energy (critical)
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
