Soccer Training Minigame
========================

This minigame is a fast, in-process 2D soccer simulator for policy training and
evolution. It is separate from the rcssserver adapter (evaluation target) and
runs as a league inside tank/petri worlds.

Action Space
------------
Policies return a SoccerAction or an equivalent dict with:

- `turn` (float): normalized turn command in [-1, 1]. Scaled by `player_turn_rate`.
- `dash` (float): normalized dash command in [-1, 1]. Scaled by `player_acceleration`.
- `kick_power` (float): [0, 1]. Kicks only apply when within `kick_range`.
- `kick_angle` (float): radians offset from facing direction.

Policy signature:

```
def policy(obs, rng) -> SoccerAction | dict:
    return {"turn": 0.0, "dash": 1.0, "kick_power": 0.0, "kick_angle": 0.0}
```

Use CodePool with `kind="soccer_policy"` to attach policies to players.

Observation Space
-----------------
Each agent receives a dict with:

- `position`: `{"x": float, "y": float}`
- `velocity`: `{"x": float, "y": float}`
- `stamina`: float [0, 1]
- `facing_angle`: float (radians)
- `ball_position`: `{"x": float, "y": float}`
- `ball_velocity`: `{"x": float, "y": float}`
- `ball_relative_pos`: `{"x": float, "y": float}` from player to ball.
- `ball_relative_vel`: `{"x": float, "y": float}` ball velocity relative to player.
- `goal_direction`: `{"x": float, "y": float}` vector pointing to opponent goal center.
- `teammates`: list of player states (id, position, velocity, stamina).
- `opponents`: list of player states (id, position, velocity, stamina).
- `game_time`: current frame / frame_rate.
- `play_mode`: current match mode (e.g. "play", "kick_off_left").
- `field_width`/`field_height`: dimensions.

Reward Shaping and Energy
-------------------------
Energy is tracked using the shared energy model:

- Dashing applies an energy cost (`dash_energy_cost`).
- Base metabolism and movement energy are consumed every tick.
- Scoring a goal grants `goal_reward` energy to the scorer.
- Assists grant `assist_reward` energy.
- Possession within `possession_radius` grants `possession_reward` energy per tick.
- Draws refund entry fees to avoid silent energy sinks.

Fitness metrics are reported per agent and per team, with current energy as the
primary fitness signal (plus raw goal/assist/possession counts for analysis).

League Configuration Overrides
------------------------------
Enable the soccer league via world config overrides (CreateWorldRequest.config):

- `soccer_enabled`: bool
- `soccer_match_every_frames`: int (match cadence)
- `soccer_matches_per_tick`: int
- `soccer_entry_fee_energy`: float
- `soccer_reward_mode`: "pot_payout" or "refill_to_max"
- `soccer_reward_multiplier`: float
- `soccer_repro_reward_mode`: "credits" or "none"
- `soccer_repro_credit_award`: float
- `soccer_repro_credit_required`: float
