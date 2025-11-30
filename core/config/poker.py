"""Poker game configuration constants."""

# Poker Game Limits
POKER_MAX_PLAYERS = 6  # Maximum players (fish + plants) in a single poker game

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

# Poker Preflop Decision Constants
POKER_PREFLOP_STRENGTH_THRESHOLD = 0.8  # Multiplier for pot odds to determine call vs fold
POKER_PREFLOP_MAX_ENERGY_FRACTION = 0.3  # Maximum fraction of energy to bet preflop
POKER_PREFLOP_MIN_RAISE_MULTIPLIER = 1.5  # Minimum raise as multiplier of call amount
POKER_LAG_ENERGY_FRACTION = 0.35  # Energy fraction for loose-aggressive strategy raises

# Poker Event Tracking
MAX_POKER_EVENTS = 10  # Maximum number of recent poker events to keep
POKER_EVENT_MAX_AGE_FRAMES = 180  # Maximum age for poker events (6 seconds at 30fps)
