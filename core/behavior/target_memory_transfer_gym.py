"""A frozen cross-domain transfer assay for the shared target-memory substrate.

Mirrors core/pursuit/transfer_gym.py's structure (see docs/EVOLVABILITY.md S3.1/
S3.5 and the substrate Board thread that specified this design) but evolves
TargetMemoryParams (core/behavior/target_memory.py) instead of the pursuit
BehaviorGraph: given a scenario where several candidates appear, move,
disappear, and reappear over time, does target_memory's persistence/switching
logic capture more value than naive frame-by-frame reselection - and does
food-adapted commitment transfer zero-shot to the ball domain versus a
founder-default ("disjoint") baseline that food selection never touched?

Mutation uses a single fixed (mutation_rate, mutation_strength) constant for
both training arms (MUTATION_RATE/MUTATION_STRENGTH below), matching
TargetMemoryParams.crossed_over()'s own contract. This is deliberate, not an
oversight: target_memory's per-trait self-adapting meta-gene
(GeneticTrait.mutation_rate/mutation_strength, core/genetics/trait.py) is not
currently consumed by inherit_behavior_graph (core/genetics/
behavioral_inheritance.py) for graph-shaped traits - contrast TraitSpec.inherit,
which does scale ordinary scalar traits by it. The fixed constants below are
therefore the only mutation-intensity lever that actually exists for
target_memory today, so "the same schedule for both arms" is satisfied
completely by a shared constant; there is no per-lineage meta-gene state to
replay. If that wiring gap is ever closed, this assay's matched-budget claim
should be re-verified against the new mechanism.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any

from core.behavior.target_memory import (
    TargetCandidate,
    TargetId,
    TargetMemoryParams,
    TargetMemoryState,
    decide_target,
)
from core.math_utils import Vector2
from core.pursuit.transfer_gym import generate_ball_trajectory

PURSUER_SPEED = 3.0
CAPTURE_RADIUS = 12.0
MAX_FRAMES = 250

POPULATION_SIZE = 16
GENERATIONS = 15
EVOLUTION_RUNS = 2
MUTATION_RATE = 0.2
MUTATION_STRENGTH = 0.1
CROSSOVER_WEIGHT = 0.5
# Minimum ball_trained-vs-default gap (in overall_score, [0,1]) required before
# the adaptation-speed comparison is considered meaningful. Measured on the
# ball-validation set (never the training or held-out sets). Below this, the
# gap is indistinguishable from run-to-run evolution noise (empirically,
# repeated ball_trained runs land within a few hundredths of default on many
# seeds), so gating adaptation generations on it would measure noise, not
# adaptation. See TargetMemoryTransferEvaluation.adaptation_reference_established.
MIN_REFERENCE_EFFECT = 0.02

_LENGTH = MAX_FRAMES + 1
# Spans a meaningful fraction of TargetMemoryParams' memory_duration bounds
# (10-300, see core/behavior/target_memory.py::_PARAM_BOUNDS) so survival is a
# graded function of the tuned value rather than a near-universal freebie -
# a 15-frame ceiling was comfortably beaten by nearly every legal value,
# flattening the zero-shot fitness landscape (see substrate board build log).
_OCCLUSION_MIN_LEN = 10
_OCCLUSION_MAX_LEN = 80

_FOOD_FAMILY_NAMES = {0: "stable_commitment", 1: "true_switch_required", 2: "occlusion_survival"}
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


@dataclass(frozen=True)
class TargetMemoryEpisodeResult:
    """``captured_value`` is time-discounted (see ``_capture_credit``), not a
    raw value sum: with a generous frame budget, both a well-tuned and a
    badly-tuned params configuration eventually capture the same tracks
    (memory only changes *how fast*, e.g. coasting through an occlusion gap
    via extrapolation versus idling after a premature DROP), so a plain
    captured/available ratio can't tell them apart. Discounting by capture
    frame makes that speed difference visible as a fitness gradient."""

    captured_value: float
    available_value: float
    captures: int

    @property
    def capture_ratio(self) -> float:
        return self.captured_value / self.available_value if self.available_value else 0.0


def _capture_credit(value: float, frame: int, max_frames: int) -> float:
    """Linearly decay a captured track's value from full credit at frame 0 to
    near-zero at the episode horizon, rewarding faster convergence."""
    return value * (1.0 - frame / (max_frames + 1))


@dataclass(frozen=True)
class EvaluationSummary:
    """Aggregated metrics over a set of scenarios."""

    capture_ratio: float
    mean_captures: float
    family_fitness: dict[str, float]
    overall_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "capture_ratio": self.capture_ratio,
            "mean_captures": self.mean_captures,
            "family_fitness": self.family_fitness,
            "overall_score": self.overall_score,
        }


@dataclass(frozen=True)
class TargetMemoryTransferEvaluation:
    """Rich evaluation payload comparing multiple groups on the zero-shot ball set.

    ``adaptation_generations_*``/``adaptation_threshold`` are ``None`` when
    ``adaptation_reference_established`` is False: the ball_trained group
    failed to clear ``MIN_REFERENCE_EFFECT`` over default on the
    ball-validation set, so there is no meaningful bar to measure
    "generations to adapt" against for this seed. Consumers must check the
    flag before reading those fields, rather than treating a near-zero
    threshold as a real result. When established, the threshold and each
    generation's crossing check are also measured on ball-validation while
    selection runs on ball-training, so the metric reflects generalization
    rather than training fit; the held-out set is never touched by any
    adaptation machinery.
    """

    group_summaries: dict[str, EvaluationSummary]
    adaptation_generations_food: int | None
    adaptation_generations_default: int | None
    adaptation_threshold: float | None
    adaptation_reference_established: bool
    adaptation_reference_gap: float

    @property
    def naive_greedy_score(self) -> float:
        return self.group_summaries["naive_greedy"].overall_score

    @property
    def default_score(self) -> float:
        return self.group_summaries["default_params"].overall_score

    @property
    def food_trained_score(self) -> float:
        return self.group_summaries["food_trained"].overall_score

    @property
    def ball_trained_score(self) -> float:
        return self.group_summaries["ball_trained"].overall_score


# ---------------------------------------------------------------------------
# Scenario generation
# ---------------------------------------------------------------------------
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


def _food_tracks(family_idx: int, rng: random.Random, length: int) -> list[CandidateTrack]:
    primary_value = rng.uniform(40.0, 60.0)
    primary_pos = _spawn_position(rng)
    primary_visible = [True] * length

    if family_idx == 2:  # occlusion_survival
        _apply_occlusion(primary_visible, rng, windows=2, max_start=40)

    tracks = [
        CandidateTrack(
            target_id=TargetId("food", 0),
            value=primary_value,
            start_frame=0,
            positions=tuple(primary_pos.copy() for _ in range(length)),
            velocities=tuple(Vector2(0.0, 0.0) for _ in range(length)),
            visible_mask=tuple(primary_visible),
        )
    ]

    if family_idx == 1:  # true_switch_required
        # A spawns far enough that transit takes a while; B appears early,
        # during that transit (not after A would already be captured), so a
        # genuine redirect decision is required rather than a moot one.
        spawn_at = rng.randint(15, 35)
        better_len = length - spawn_at
        better_value = primary_value * rng.uniform(2.5, 3.5)
        better_pos = _spawn_position(rng)
        tracks.append(
            CandidateTrack(
                target_id=TargetId("food", 1),
                value=better_value,
                start_frame=spawn_at,
                positions=tuple(better_pos.copy() for _ in range(better_len)),
                velocities=tuple(Vector2(0.0, 0.0) for _ in range(better_len)),
                visible_mask=tuple([True] * better_len),
            )
        )

    return tracks


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
    set_type: str, seed: int, version: str = "v1"
) -> list[TargetMemoryScenario]:
    """Generate a versioned, deterministic set of target-memory scenarios."""
    salt = _SET_SALTS[set_type]
    rng = random.Random(seed + salt)
    is_ball = set_type != "train" and set_type != "validation"
    family_distribution = [0, 1, 2, 3] if is_ball else [0, 0, 1, 1, 2, 2]
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


# ---------------------------------------------------------------------------
# Episode evaluation
# ---------------------------------------------------------------------------
def _visible_candidates(
    scenario: TargetMemoryScenario, frame: int, captured: set[TargetId]
) -> list[TargetCandidate]:
    visible = []
    for track in scenario.tracks:
        if track.target_id in captured:
            continue
        local = frame - track.start_frame
        if local < 0 or local >= len(track.positions):
            continue
        if not track.visible_mask[local]:
            continue
        pos = track.positions[local]
        vel = track.velocities[local]
        visible.append(
            TargetCandidate(track.target_id, (pos.x, pos.y), (vel.x, vel.y), track.value)
        )
    return visible


def _step_toward(observer: Vector2, dx: float, dy: float) -> Vector2:
    dist = math.hypot(dx, dy)
    if dist <= 1e-9:
        return observer
    return observer + Vector2(dx / dist, dy / dist) * PURSUER_SPEED


def run_target_memory_episode(
    params: TargetMemoryParams, scenario: TargetMemoryScenario
) -> TargetMemoryEpisodeResult:
    """Run one deterministic episode: target_memory picks a target each frame,
    the observer steers directly at it, and a target is captured (and removed)
    once the observer closes within CAPTURE_RADIUS of it."""
    observer = scenario.observer_start.copy()
    state = TargetMemoryState.empty()
    captured: set[TargetId] = set()
    captured_value = 0.0

    for frame in range(scenario.max_frames + 1):
        visible = _visible_candidates(scenario, frame, captured)
        state, decision = decide_target(state, visible, (observer.x, observer.y), params)

        if decision.selected_target_id is not None:
            dx, dy = decision.target_vector
            observer = _step_toward(observer, dx, dy)

            selected = next(
                (c for c in visible if c.target_id == decision.selected_target_id), None
            )
            if selected is not None:
                d = math.hypot(selected.position[0] - observer.x, selected.position[1] - observer.y)
                if d <= CAPTURE_RADIUS:
                    captured.add(selected.target_id)
                    captured_value += _capture_credit(selected.value, frame, scenario.max_frames)

    return TargetMemoryEpisodeResult(
        captured_value=captured_value,
        available_value=scenario.available_value,
        captures=len(captured),
    )


def _best_visible(visible: list[TargetCandidate]) -> TargetCandidate | None:
    best: TargetCandidate | None = None
    for c in visible:
        if (
            best is None
            or c.value > best.value
            or (c.value == best.value and c.target_id < best.target_id)
        ):
            best = c
    return best


def run_naive_greedy_episode(scenario: TargetMemoryScenario) -> TargetMemoryEpisodeResult:
    """No memory at all: chase the best currently-visible candidate every
    frame, forgetting instantly the moment it isn't visible. The floor
    target_memory's persistence must beat to earn its keep."""
    observer = scenario.observer_start.copy()
    captured: set[TargetId] = set()
    captured_value = 0.0

    for frame in range(scenario.max_frames + 1):
        visible = _visible_candidates(scenario, frame, captured)
        target = _best_visible(visible)
        if target is not None:
            dx = target.position[0] - observer.x
            dy = target.position[1] - observer.y
            observer = _step_toward(observer, dx, dy)
            d = math.hypot(target.position[0] - observer.x, target.position[1] - observer.y)
            if d <= CAPTURE_RADIUS:
                captured.add(target.target_id)
                captured_value += _capture_credit(target.value, frame, scenario.max_frames)

    return TargetMemoryEpisodeResult(
        captured_value=captured_value,
        available_value=scenario.available_value,
        captures=len(captured),
    )


def _summarize(
    results: list[tuple[TargetMemoryScenario, TargetMemoryEpisodeResult]],
) -> EvaluationSummary:
    ratios = [r.capture_ratio for _, r in results]
    capture_ratio = sum(ratios) / len(ratios)
    mean_captures = sum(r.captures for _, r in results) / len(results)

    family_scores: dict[str, float] = {}
    family_counts: dict[str, int] = {}
    for scenario, r in results:
        fam = scenario.family_name
        family_scores[fam] = family_scores.get(fam, 0.0) + r.capture_ratio
        family_counts[fam] = family_counts.get(fam, 0) + 1
    family_fitness = {fam: family_scores[fam] / family_counts[fam] for fam in family_scores}

    return EvaluationSummary(
        capture_ratio=capture_ratio,
        mean_captures=mean_captures,
        family_fitness=family_fitness,
        overall_score=capture_ratio,
    )


def evaluate_params_on_set(
    params: TargetMemoryParams, scenarios: list[TargetMemoryScenario]
) -> EvaluationSummary:
    return _summarize([(s, run_target_memory_episode(params, s)) for s in scenarios])


def evaluate_naive_greedy_on_set(scenarios: list[TargetMemoryScenario]) -> EvaluationSummary:
    return _summarize([(s, run_naive_greedy_episode(s)) for s in scenarios])


def average_summaries(evals: list[EvaluationSummary]) -> EvaluationSummary:
    """Average several evaluation runs (e.g. multiple independent evolution
    runs for the same group) into one summary. Public: shared with
    target_memory_transfer_evolution, which orchestrates those runs."""
    n = len(evals)
    family_fitness = {
        fam: sum(e.family_fitness.get(fam, 0.0) for e in evals) / n
        for fam in evals[0].family_fitness
    }
    return EvaluationSummary(
        capture_ratio=sum(e.capture_ratio for e in evals) / n,
        mean_captures=sum(e.mean_captures for e in evals) / n,
        family_fitness=family_fitness,
        overall_score=sum(e.overall_score for e in evals) / n,
    )
