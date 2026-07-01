"""Soccer evaluator configuration constants."""

# Soccer evaluator feature flag.
SOCCER_EVALUATOR_ENABLED = True

# Scheduling (in simulation frames; 30 fps).
SOCCER_EVALUATOR_INTERVAL_FRAMES = 1

# Participant thresholds.
SOCCER_EVALUATOR_MIN_PLAYERS = 6
SOCCER_EVALUATOR_NUM_PLAYERS = 6

# Match duration (RCSS cycles at 10Hz).
# 3000 cycles = 300 seconds (5 minutes) of match time.
SOCCER_EVALUATOR_DURATION_FRAMES = 1800

# Event tracking.
SOCCER_MAX_EVENTS = 10
SOCCER_EVENT_MAX_AGE_FRAMES = 600

# League scheduling defaults.
SOCCER_LEAGUE_MATCH_EVERY_FRAMES = 60
SOCCER_LEAGUE_MATCHES_PER_TICK = 1
SOCCER_LEAGUE_CYCLES_PER_FRAME = 1
SOCCER_LEAGUE_TEAM_SIZE = 0  # 0 = derive from num_players
SOCCER_LEAGUE_COOLDOWN_MATCHES = 2
SOCCER_LEAGUE_ALLOW_REPEAT_WITHIN_MATCH = False
SOCCER_LEAGUE_SELECTION_STRATEGY = "stratified"

# ---------------------------------------------------------------------------
# Reward architecture (single source of truth for soccer energy rewards).
#
# Soccer mirrors poker's economy: a competition whose reward is (a) proportional
# to skill and (b) largely self-funded, so it feeds the reproduction economy
# without acting as an unbounded energy faucet. Two surfaces read these:
#   * SoccerSystem   - in-tank "practice" ball: sparse per-event energy.
#   * league rewards - the tournament pot + shaped bonuses (see rewards.py).
# The same shaped-reward function is used by the training benchmark's fitness,
# so Layer-0 (tank selection) and Layer-1 (benchmark) optimize one objective.
# ---------------------------------------------------------------------------

# In-tank practice ball (SoccerSystem). Sparse events only, not per-frame.
SOCCER_KICK_REWARD_ENERGY = 2.0  # Reward for a purposeful kick.
SOCCER_GOAL_REWARD_ENERGY = 50.0  # Reward for scoring (dominant skill signal).

# Shaped-reward weights: dense, per-contribution learning signal derived from
# match telemetry. Keep in sync with the benchmark fitness (match_runner.py uses
# calculate_shaped_bonuses with these same defaults).
SOCCER_SHAPED_PROGRESS_WEIGHT = 0.5  # Energy per meter of ball progress toward goal.
SOCCER_SHAPED_TOUCH_WEIGHT = 0.2  # Energy per ball touch.
SOCCER_SHAPED_SHOT_WEIGHT = 1.0  # Energy per shot on target.
SOCCER_SHAPED_PER_PLAYER_CAP = 10.0  # Cap on any single player's shaped bonus.
SOCCER_SHAPED_TEAM_BONUS_CAP = 20.0  # Cap on shaped bonus summed across a team.

# Reward model defaults.
# Entry fee mirrors the poker ante (POKER_ANTE_AMOUNT): every participant has
# skin in the game, so the pot is real and losing a match costs energy. This
# turns the tournament into a redistribution of energy toward skilled players
# (selection pressure) instead of a flat handout to whoever wins.
SOCCER_LEAGUE_ENTRY_FEE_ENERGY = 5.0
# shaped_pot: winners split the (self-funded) pot AND all players receive
# telemetry-shaped bonuses, so reward tracks contribution and margin rather
# than the mere fact of being on the winning side (the old refill_to_max
# rewarded a 1-0 fluke identically to a 10-0 rout and injected free energy).
SOCCER_LEAGUE_REWARD_MODE = "shaped_pot"
SOCCER_LEAGUE_REWARD_MULTIPLIER = 1.0

# Reproduction reward defaults.
SOCCER_LEAGUE_REPRO_REWARD_MODE = "credits"
SOCCER_LEAGUE_REPRO_CREDIT_AWARD = 2.0
SOCCER_LEAGUE_REPRO_CREDIT_REQUIRED = 0.0
SOCCER_LEAGUE_REPRO_CREDIT_INITIAL = 0.0

# Optional seed override (None -> derive from world seed).
SOCCER_LEAGUE_SEED_BASE = None
