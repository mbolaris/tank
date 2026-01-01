Soccer Training World
=====================

This world is a fast, in-process 2D soccer simulator for policy training and
evolution. It is separate from the rcssserver adapter (evaluation target).

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

- `ball_relative_pos`: vector from player to ball.
- `ball_relative_vel`: ball velocity relative to player velocity.
- `nearest_teammate`: relative position/velocity and distance to closest teammate.
- `nearest_opponent`: relative position/velocity and distance to closest opponent.
- `goal_direction`: normalized vector pointing to the opponent goal center.
- `stamina`: energy ratio (0.0 to 1.0).
- `energy`: current energy value.

Reward Shaping and Energy
-------------------------
Energy is tracked using the shared energy model:

- Dashing applies an energy cost (`dash_energy_cost`).
- Base metabolism and movement energy are consumed every tick.
- Scoring a goal grants `goal_reward` energy to the scorer.
- Assists grant `assist_reward` energy.
- Possession within `possession_radius` grants `possession_reward` energy per tick.

Fitness metrics are reported per agent and per team, with current energy as the
primary fitness signal (plus raw goal/assist/possession counts for analysis).
