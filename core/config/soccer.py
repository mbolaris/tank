"""Soccer evaluator configuration constants."""

# Soccer evaluator feature flag.
SOCCER_EVALUATOR_ENABLED = False

# Scheduling (in simulation frames; 30 fps).
SOCCER_EVALUATOR_INTERVAL_FRAMES = 900

# Participant thresholds.
SOCCER_EVALUATOR_MIN_PLAYERS = 6
SOCCER_EVALUATOR_NUM_PLAYERS = 22

# Match duration (RCSS cycles at 10Hz).
SOCCER_EVALUATOR_DURATION_FRAMES = 600

# Event tracking.
SOCCER_MAX_EVENTS = 10
SOCCER_EVENT_MAX_AGE_FRAMES = 180
