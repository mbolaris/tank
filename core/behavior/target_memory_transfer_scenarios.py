"""Scenario generation for the target-memory transfer gym (study v1.2).

Split out of core/behavior/target_memory_transfer_gym.py (which owns episode
evaluation and metrics) to stay under the repo's god-class line-limit ratchet.

Food/ball capability matching
-----------------------------
The food and ball domains must differ in surface (values, spawn geometry,
track shapes) but exercise the *same reusable capabilities*, otherwise the
transfer question degenerates into "does an untrained parameter happen to
work elsewhere". v1 food was entirely stationary, so food selection exerted
no pressure on ``motion_extrapolation_duration`` while every ball scenario
demanded it. v2 adds moving-food families matched to the ball families'
latent demands:

===========================  ==============================  =======================
Food family (v2)             Latent capability               Ball family analogue
===========================  ==============================  =======================
stable_commitment            hold commitment, no distractor  (baseline for all)
true_switch_required         genuine value-driven switch     sudden_kick_with_decoy
occlusion_survival           persistence through occlusion   (all: occluded window)
drifting_food                linear extrapolation + occl.    decelerating
decelerating_drift           non-constant speed + occl.      decelerating
occluded_turn                reappearance off the linear     bouncing / swerve
                             prediction
competing_drifters           commitment among moving         sudden_kick_with_decoy
                             alternatives
===========================  ==============================  =======================

Ball-side generation is unchanged from v1 (same rng consumption, so same
tracks for a given seed); only the food families and their distribution
changed, which is why the set version tag below is bumped for every set the
generator emits.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable
from dataclasses import dataclass

from core.behavior.target_memory import TargetId
from core.math_utils import Vector2
from core.pursuit.transfer_gym import generate_ball_trajectory

MAX_FRAMES = 250
_LENGTH = MAX_FRAMES + 1

# Spans a meaningful fraction of TargetMemoryParams' memory_duration bounds
# (10-300, see core/behavior/target_memory.py::_PARAM_BOUNDS) so survival is a
# graded function of the tuned value rather than a near-universal freebie -
# a 15-frame ceiling was comfortably beaten by nearly every legal value,
# flattening the zero-shot fitness landscape (see substrate board build log).
_OCCLUSION_MIN_LEN = 10
_OCCLUSION_MAX_LEN = 80

# Food drifts well below PURSUER_SPEED (3.0, see the gym module): moving food
# must remain catchable so the families discriminate *commitment* quality,
# not raw pursuit capability.
_FOOD_DRIFT_SPEED_MIN = 0.6
_FOOD_DRIFT_SPEED_MAX = 1.4

_FOOD_FAMILY_NAMES = {
    0: "stable_commitment",
    1: "true_switch_required",
    2: "occlusion_survival",
    3: "drifting_food",
    4: "decelerating_drift",
    5: "occluded_turn",
    6: "competing_drifters",
}
# generate_ball_trajectory's family 4 ("speed_ratio", up to 1.3x pursuer speed)
# is deliberately excluded: target_memory only decides *what* to commit to, not
# *how* to steer (no lead-prediction parameter exists on TargetMemoryParams -
# see core/behavior/target_memory.py's module docstring), so a target that
# outruns PURSUER_SPEED is uncatchable regardless of selection quality. That
# family tests pursuit capability, not target memory, so it can't discriminate
# policies here and would only add noise.
_BALL_FAMILY_NAMES = {
    0: "decelerating",
    1: "bouncing",
    2: "swerve",
    3: "sudden_kick_with_decoy",
}
_SET_SALTS = {
    "train": 1000,
    "validation": 2000,
    "held_out": 3000,
    "ball_train": 4000,
    "ball_validation": 5000,
}

SCENARIO_SET_VERSION = "v2"

# One scenario per food family: the moving families joined in v2 and the
# budget stays comparable to v1's six-scenario sets (scale-up is the multi-run
# study's job, not this one's).
_FOOD_FAMILY_DISTRIBUTION = [0, 1, 2, 3, 4, 5, 6]
_BALL_FAMILY_DISTRIBUTION = [0, 1, 2, 3]


@dataclass(frozen=True)
class CandidateTrack:
    """One candidate's full scripted lifetime within a scenario."""

    target_id: TargetId
    value: float
    start_frame: int
    positions: tuple[Vector2, ...]
    velocities: tuple[Vector2, ...]
    visible_mask: tuple[bool, ...]


@dataclass(frozen=True)
class TargetMemoryScenario:
    """Several independently scripted candidates competing (or not) for the
    observer's commitment over time."""

    scenario_id: str
    family_name: str
    observer_start: Vector2
    tracks: tuple[CandidateTrack, ...]
    max_frames: int

    @property
    def available_value(self) -> float:
        return sum(track.value for track in self.tracks)


def _spawn_position(rng: random.Random) -> Vector2:
    angle = rng.uniform(0, 2 * math.pi)
    distance = rng.uniform(80.0, 160.0)
    return Vector2(math.cos(angle) * distance, math.sin(angle) * distance)


def _apply_occlusion(visible: list[bool], rng: random.Random, windows: int, max_start: int) -> None:
    """Punch `windows` brief invisible gaps into an otherwise-visible track,
    simulating another fish/object briefly blocking the line of sight. Gaps
    are placed early (before ``max_start``) so they land during the pursuer's
    approach rather than after it has already captured the target - a gap
    that only ever occurs post-capture can never test memory at all."""
    n = len(visible)
    span = _OCCLUSION_MAX_LEN + 2
    if n <= span:
        return
    start_ceiling = min(max_start, n - span)
    if start_ceiling < 1:
        return
    for _ in range(windows):
        gap_len = rng.randint(_OCCLUSION_MIN_LEN, _OCCLUSION_MAX_LEN)
        start = rng.randint(1, start_ceiling)
        for i in range(start, start + gap_len):
            visible[i] = False


def _drift_velocity(rng: random.Random) -> Vector2:
    angle = rng.uniform(0, 2 * math.pi)
    speed = rng.uniform(_FOOD_DRIFT_SPEED_MIN, _FOOD_DRIFT_SPEED_MAX)
    return Vector2(math.cos(angle) * speed, math.sin(angle) * speed)


def _integrate_drift(
    start: Vector2,
    length: int,
    velocity_at: Callable[[int], Vector2],
) -> tuple[list[Vector2], list[Vector2]]:
    """Script a moving track: ``velocity_at(frame)`` -> Vector2 per frame."""
    positions = [start.copy()]
    velocities = [velocity_at(0)]
    for frame in range(1, length):
        vel = velocity_at(frame)
        positions.append(positions[-1] + vel)
        velocities.append(vel)
    return positions, velocities


def _stationary_track(
    target_id: TargetId, value: float, pos: Vector2, length: int, visible: list[bool]
) -> CandidateTrack:
    return CandidateTrack(
        target_id=target_id,
        value=value,
        start_frame=0,
        positions=tuple(pos.copy() for _ in range(length)),
        velocities=tuple(Vector2(0.0, 0.0) for _ in range(length)),
        visible_mask=tuple(visible),
    )


def _moving_track(
    target_id: TargetId,
    value: float,
    positions: list[Vector2],
    velocities: list[Vector2],
    visible: list[bool],
    start_frame: int = 0,
) -> CandidateTrack:
    return CandidateTrack(
        target_id=target_id,
        value=value,
        start_frame=start_frame,
        positions=tuple(positions),
        velocities=tuple(velocities),
        visible_mask=tuple(visible),
    )


def _food_tracks(family_idx: int, rng: random.Random, length: int) -> list[CandidateTrack]:
    primary_value = rng.uniform(40.0, 60.0)
    primary_pos = _spawn_position(rng)
    primary_visible = [True] * length

    if family_idx == 0:  # stable_commitment
        return [
            _stationary_track(
                TargetId("food", 0), primary_value, primary_pos, length, primary_visible
            )
        ]

    if family_idx == 1:  # true_switch_required
        tracks = [
            _stationary_track(
                TargetId("food", 0), primary_value, primary_pos, length, primary_visible
            )
        ]
        # A spawns far enough that transit takes a while; B appears early,
        # during that transit (not after A would already be captured), so a
        # genuine redirect decision is required rather than a moot one.
        spawn_at = rng.randint(15, 35)
        better_len = length - spawn_at
        better_value = primary_value * rng.uniform(2.5, 3.5)
        better_pos = _spawn_position(rng)
        tracks.append(
            _moving_track(
                TargetId("food", 1),
                better_value,
                [better_pos.copy() for _ in range(better_len)],
                [Vector2(0.0, 0.0) for _ in range(better_len)],
                [True] * better_len,
                start_frame=spawn_at,
            )
        )
        return tracks

    if family_idx == 2:  # occlusion_survival
        _apply_occlusion(primary_visible, rng, windows=2, max_start=40)
        return [
            _stationary_track(
                TargetId("food", 0), primary_value, primary_pos, length, primary_visible
            )
        ]

    if family_idx == 3:  # drifting_food: straight constant-velocity drift
        drift = _drift_velocity(rng)
        positions, velocities = _integrate_drift(primary_pos, length, lambda _f: drift.copy())
        _apply_occlusion(primary_visible, rng, windows=1, max_start=40)
        return [
            _moving_track(
                TargetId("food", 0), primary_value, positions, velocities, primary_visible
            )
        ]

    if family_idx == 4:  # decelerating_drift: drifts fast, coasts to a stop
        drift = _drift_velocity(rng)
        decay = rng.uniform(0.975, 0.99)

        def _decel(frame: int) -> Vector2:
            factor = decay**frame
            return Vector2(drift.x * factor, drift.y * factor)

        positions, velocities = _integrate_drift(primary_pos, length, _decel)
        _apply_occlusion(primary_visible, rng, windows=1, max_start=40)
        return [
            _moving_track(
                TargetId("food", 0), primary_value, positions, velocities, primary_visible
            )
        ]

    if family_idx == 5:  # occluded_turn: direction change hidden inside the gap
        drift = _drift_velocity(rng)
        gap_start = rng.randint(20, 40)
        gap_len = rng.randint(30, _OCCLUSION_MAX_LEN)
        turn_frame = gap_start + gap_len // 2
        # 60-120 degrees off the pre-gap heading (either side): far enough
        # that a pure linear extrapolation points meaningfully away from the
        # true reappearance, close enough that reacquisition stays feasible.
        turn = math.radians(rng.uniform(60.0, 120.0)) * rng.choice((-1.0, 1.0))
        cos_t, sin_t = math.cos(turn), math.sin(turn)
        turned = Vector2(drift.x * cos_t - drift.y * sin_t, drift.x * sin_t + drift.y * cos_t)

        def _turning(frame: int) -> Vector2:
            return (drift if frame < turn_frame else turned).copy()

        positions, velocities = _integrate_drift(primary_pos, length, _turning)
        for i in range(gap_start, min(gap_start + gap_len, length)):
            primary_visible[i] = False
        return [
            _moving_track(
                TargetId("food", 0), primary_value, positions, velocities, primary_visible
            )
        ]

    if family_idx == 6:  # competing_drifters: moving decoy against a moving prize
        drift = _drift_velocity(rng)
        positions, velocities = _integrate_drift(primary_pos, length, lambda _f: drift.copy())
        _apply_occlusion(primary_visible, rng, windows=1, max_start=40)
        tracks = [
            _moving_track(
                TargetId("food", 0), primary_value, positions, velocities, primary_visible
            )
        ]
        decoy_at = rng.randint(20, 60)
        decoy_len = length - decoy_at
        decoy_value = primary_value * rng.uniform(0.3, 0.5)
        decoy_drift = _drift_velocity(rng)
        decoy_positions, decoy_velocities = _integrate_drift(
            _spawn_position(rng), decoy_len, lambda _f: decoy_drift.copy()
        )
        tracks.append(
            _moving_track(
                TargetId("food", 1),
                decoy_value,
                decoy_positions,
                decoy_velocities,
                [True] * decoy_len,
                start_frame=decoy_at,
            )
        )
        return tracks

    raise ValueError(f"Unknown food family index: {family_idx}")


def _ball_tracks(family_idx: int, rng: random.Random, length: int) -> list[CandidateTrack]:
    _, positions, velocities = generate_ball_trajectory(family_idx, rng)
    positions = positions[:length]
    velocities = velocities[:length]
    value = rng.uniform(50.0, 80.0)
    visible = [True] * length
    _apply_occlusion(visible, rng, windows=1, max_start=40)

    tracks = [
        CandidateTrack(
            target_id=TargetId("ball", 0),
            value=value,
            start_frame=0,
            positions=tuple(p.copy() for p in positions),
            velocities=tuple(v.copy() for v in velocities),
            visible_mask=tuple(visible),
        )
    ]

    if family_idx == 3:  # sudden_kick_with_decoy
        decoy_at = rng.randint(40, min(160, length - 40))
        decoy_len = rng.randint(10, 20)
        decoy_pos = _spawn_position(rng)
        decoy_value = value * rng.uniform(0.3, 0.5)
        tracks.append(
            CandidateTrack(
                target_id=TargetId("ball", 1),
                value=decoy_value,
                start_frame=decoy_at,
                positions=tuple(decoy_pos.copy() for _ in range(decoy_len)),
                velocities=tuple(Vector2(0.0, 0.0) for _ in range(decoy_len)),
                visible_mask=tuple([True] * decoy_len),
            )
        )

    return tracks


def generate_scenario_set(
    set_type: str, seed: int, version: str = SCENARIO_SET_VERSION
) -> list[TargetMemoryScenario]:
    """Generate a versioned, deterministic set of target-memory scenarios."""
    salt = _SET_SALTS[set_type]
    rng = random.Random(seed + salt)
    is_ball = set_type != "train" and set_type != "validation"
    family_distribution = _BALL_FAMILY_DISTRIBUTION if is_ball else _FOOD_FAMILY_DISTRIBUTION
    family_names = _BALL_FAMILY_NAMES if is_ball else _FOOD_FAMILY_NAMES

    scenarios = []
    for idx, fam in enumerate(family_distribution):
        scenario_id = f"{set_type}_{version}_{idx}"
        tracks = _ball_tracks(fam, rng, _LENGTH) if is_ball else _food_tracks(fam, rng, _LENGTH)
        scenarios.append(
            TargetMemoryScenario(
                scenario_id=scenario_id,
                family_name=family_names[fam],
                observer_start=Vector2(0.0, 0.0),
                tracks=tuple(tracks),
                max_frames=MAX_FRAMES,
            )
        )
    return scenarios
