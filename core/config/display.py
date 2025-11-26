"""Display and UI configuration constants."""

# Screen dimensions in pixels (must match Canvas size in frontend)
SCREEN_WIDTH = 1088
SCREEN_HEIGHT = 612

# The frame rate for the game loop, in frames per second
FRAME_RATE = 30

# Default agent size (width and height in pixels)
DEFAULT_AGENT_SIZE = 50.0

# The rate at which the sprite images change, in milliseconds
IMAGE_CHANGE_RATE = 500

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
    "plant3": (500, 510),
    "plant4": (700, 510),
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

# UI Display Constants
SEPARATOR_WIDTH = 60  # Width of separator lines in console output
