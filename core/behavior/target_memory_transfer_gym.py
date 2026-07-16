"""A frozen cross-domain transfer assay for the shared target-memory substrate.

Mirrors core/pursuit/transfer_gym.py's structure (see docs/EVOLVABILITY.md S3.1/
S3.5 and the substrate Board thread that specified this design) but evolves
TargetMemoryParams (core/behavior/target_memory.py) instead of the pursuit
BehaviorGraph: given a scenario where several candidates appear, move,
disappear, and reappear over time, does target_memory's persistence/switching
logic capture more value than naive frame-by-frame reselection - and does
food-adapted commitment transfer zero-shot to the ball domain versus a
founder-default ("disjoint") baseline that food selection never touched?

Scenario generation (including the food/ball capability-matching rationale)
lives in core/behavior/target_memory_transfer_scenarios.py; the evolution
loop and top-level assay live in target_memory_transfer_evolution.py. This
module owns episode execution, per-episode diagnostic metrics, and summary
aggregation.

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
from dataclasses import dataclass
from typing import Any

from core.behavior.target_memory import (
    TargetCandidate,
    TargetId,
    TargetMemoryParams,
    TargetMemoryState,
    TargetMemoryAction,
    TargetMemoryDecision,
    decide_target,
)
from core.behavior.target_memory_transfer_scenarios import (  # noqa: F401 - re-exported
    MAX_FRAMES,
    CandidateTrack,
    TargetMemoryScenario,
    generate_scenario_set,
)
from core.math_utils import Vector2

PURSUER_SPEED = 3.0
CAPTURE_RADIUS = 12.0

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


@dataclass(frozen=True)
class TargetMemoryEpisodeResult:
    """``captured_value`` is time-discounted (see ``_capture_credit``), not a
    raw value sum: with a generous frame budget, both a well-tuned and a
    badly-tuned params configuration eventually capture the same tracks
    (memory only changes *how fast*, e.g. coasting through an occlusion gap
    via extrapolation versus idling after a premature DROP), so a plain
    captured/available ratio can't tell them apart. Discounting by capture
    frame makes that speed difference visible as a fitness gradient.

    The remaining fields are *diagnostic* observations that never feed the
    score (overall_score stays a pure capture_ratio): they exist so a
    transfer result can be explained - which behaviors a parameter set
    exhibits, not just how much value it banked.

    - ``switches``: frame-to-frame commitment changes between two distinct
      targets (a DROP followed by a fresh commitment is not a switch).
    - ``stale_pursuit_frames``: frames spent steering at a target that is not
      currently visible (memory/extrapolation-driven pursuit).
    - ``reacquisition_events``/``reacquisition_frames_total``: each time the
      committed target reappears after an invisible gap, how many frames pass
      before it is selected again (a never-reselected reappearance counts the
      remaining episode frames rather than being dropped).
    - ``distance_traveled``: total observer movement, the energy proxy at
      constant pursuit speed.
    """

    captured_value: float
    available_value: float
    captures: int
    switches: int = 0
    stale_pursuit_frames: int = 0
    reacquisition_events: int = 0
    reacquisition_frames_total: int = 0
    distance_traveled: float = 0.0

    # New diagnostic metrics
    occlusion_survived_ratio: float = 0.0
    occlusion_dropped_ratio: float = 0.0
    wasted_frames: float = 0.0
    chasing_stale_frames: float = 0.0
    distance_error_at_reappearance: float = 0.0

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
    mean_switches: float = 0.0
    mean_stale_pursuit_frames: float = 0.0
    mean_reacquisition_frames: float = 0.0
    mean_distance_traveled: float = 0.0

    # New diagnostic metrics
    mean_occlusion_survived_ratio: float = 0.0
    mean_occlusion_dropped_ratio: float = 0.0
    mean_wasted_frames: float = 0.0
    mean_chasing_stale_frames: float = 0.0
    mean_distance_error_at_reappearance: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "capture_ratio": self.capture_ratio,
            "mean_captures": self.mean_captures,
            "family_fitness": self.family_fitness,
            "overall_score": self.overall_score,
            "mean_switches": self.mean_switches,
            "mean_stale_pursuit_frames": self.mean_stale_pursuit_frames,
            "mean_reacquisition_frames": self.mean_reacquisition_frames,
            "mean_distance_traveled": self.mean_distance_traveled,
            "mean_occlusion_survived_ratio": self.mean_occlusion_survived_ratio,
            "mean_occlusion_dropped_ratio": self.mean_occlusion_dropped_ratio,
            "mean_wasted_frames": self.mean_wasted_frames,
            "mean_chasing_stale_frames": self.mean_chasing_stale_frames,
            "mean_distance_error_at_reappearance": self.mean_distance_error_at_reappearance,
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

    # Source learning (food task performance)
    food_validation_score_default: float | None = None
    food_validation_score_food_trained: float | None = None

    # Evolved parameters
    food_trained_genomes: list[dict[str, float]] | None = None
    ball_trained_genomes: list[dict[str, float]] | None = None

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


@dataclass
class _EpisodeTrace:
    """Per-frame observations collected while an episode runs, folded into
    diagnostic metrics afterwards. Observation only - never fed back into
    decisions, so metrics cannot perturb determinism."""

    selections: list[TargetId | None]
    visible_ids: list[frozenset[TargetId]]
    actions: list[TargetMemoryAction]
    decisions: list[TargetMemoryDecision | None]
    observer_positions: list[tuple[float, float]]
    target_positions: list[dict[TargetId, tuple[float, float]]]
    captured_frames: dict[TargetId, int]
    distance_traveled: float = 0.0

    def metrics(self, scenario: TargetMemoryScenario) -> dict[str, Any]:
        switches = 0
        stale = 0
        for f, selected in enumerate(self.selections):
            if selected is None:
                continue
            if selected not in self.visible_ids[f]:
                stale += 1

        # Count actual SWITCH events when actions is populated, otherwise count transitions
        if self.actions:
            switches = sum(1 for act in self.actions if act == TargetMemoryAction.SWITCH)
        else:
            for f in range(1, len(self.selections)):
                prev = self.selections[f - 1]
                curr = self.selections[f]
                if prev is not None and curr is not None and prev != curr:
                    if prev not in self.captured_frames or self.captured_frames[prev] != f - 1:
                        switches += 1

        events = 0
        frames_total = 0
        n = len(self.selections)
        for f in range(1, n):
            for tid in self.visible_ids[f] - self.visible_ids[f - 1]:
                s = f - 1
                while s >= 0 and tid not in self.visible_ids[s]:
                    s -= 1
                if s < 0:
                    continue  # first appearance, not a reappearance
                if self.selections[s] != tid:
                    continue  # wasn't the committed target when it vanished
                g = f
                while g < n and self.selections[g] != tid:
                    g += 1
                events += 1
                frames_total += (g if g < n else n) - f

        # New occlusion diagnostics
        occlusion_events = 0
        commitment_survived = 0
        dropped_prematurely = 0
        wasted_frames = 0
        chasing_stale_frames = 0
        distance_errors = []

        for track in scenario.tracks:
            tid = track.target_id
            cap_frame = self.captured_frames.get(tid, n - 1)
            end_active_idx = min(cap_frame, track.start_frame + len(track.positions) - 1)
            if end_active_idx < track.start_frame:
                continue

            local_start = 0
            while local_start < len(track.visible_mask):
                if not track.visible_mask[local_start]:
                    global_idx = track.start_frame + local_start
                    if global_idx > end_active_idx:
                        break

                    local_end = local_start
                    while local_end < len(track.visible_mask) and not track.visible_mask[local_end]:
                        local_end += 1
                    local_end -= 1

                    global_end = min(end_active_idx, track.start_frame + local_end)

                    prev_frame = global_idx - 1
                    if prev_frame >= 0 and prev_frame < n:
                        was_visible = (
                            prev_frame >= track.start_frame
                            and track.visible_mask[prev_frame - track.start_frame]
                        )
                        if was_visible and self.selections[prev_frame] == tid:
                            occlusion_events += 1

                            dropped_at = None
                            for f in range(global_idx, global_end + 1):
                                if f == cap_frame:
                                    break
                                if self.selections[f] != tid or (
                                    f < len(self.actions)
                                    and self.actions[f] == TargetMemoryAction.DROP
                                ):
                                    dropped_at = f
                                    break

                            if dropped_at is not None:
                                dropped_prematurely += 1
                                end_gap = min(global_end + 1, n - 1)
                                for f in range(dropped_at, end_gap + 1):
                                    if self.selections[f] != tid:
                                        wasted_frames += 1
                            else:
                                commitment_survived += 1
                                next_frame = global_end + 1
                                if next_frame < n and next_frame <= end_active_idx:
                                    if tid in self.target_positions[global_end]:
                                        true_pos = self.target_positions[global_end][tid]
                                        if global_end < len(self.decisions):
                                            dec = self.decisions[global_end]
                                            if dec is not None:
                                                pred_pos = dec.target_position
                                                err = math.hypot(
                                                    pred_pos[0] - true_pos[0],
                                                    pred_pos[1] - true_pos[1],
                                                )
                                                distance_errors.append(err)

                    local_start = local_end + 1
                else:
                    local_start += 1

        for f, selected in enumerate(self.selections):
            if selected is not None and selected in self.captured_frames:
                if f > self.captured_frames[selected]:
                    chasing_stale_frames += 1

        occlusion_survived_ratio = (
            commitment_survived / occlusion_events if occlusion_events else 0.0
        )
        occlusion_dropped_ratio = (
            dropped_prematurely / occlusion_events if occlusion_events else 0.0
        )
        avg_dist_error = sum(distance_errors) / len(distance_errors) if distance_errors else 0.0

        return {
            "switches": switches,
            "stale_pursuit_frames": stale,
            "reacquisition_events": events,
            "reacquisition_frames_total": frames_total,
            "distance_traveled": self.distance_traveled,
            "occlusion_survived_ratio": occlusion_survived_ratio,
            "occlusion_dropped_ratio": occlusion_dropped_ratio,
            "wasted_frames": float(wasted_frames),
            "chasing_stale_frames": float(chasing_stale_frames),
            "distance_error_at_reappearance": avg_dist_error,
        }


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
    trace = _EpisodeTrace(
        selections=[],
        visible_ids=[],
        actions=[],
        decisions=[],
        observer_positions=[],
        target_positions=[],
        captured_frames={},
    )

    for frame in range(scenario.max_frames + 1):
        visible = _visible_candidates(scenario, frame, captured)
        state, decision = decide_target(state, visible, (observer.x, observer.y), params)
        trace.selections.append(decision.selected_target_id)
        trace.visible_ids.append(frozenset(c.target_id for c in visible))
        trace.actions.append(decision.action)
        trace.decisions.append(decision)
        trace.observer_positions.append((observer.x, observer.y))
        trace.target_positions.append(
            {
                t.target_id: (
                    t.positions[frame - t.start_frame].x,
                    t.positions[frame - t.start_frame].y,
                )
                for t in scenario.tracks
                if 0 <= frame - t.start_frame < len(t.positions)
            }
        )

        if decision.selected_target_id is not None:
            dx, dy = decision.target_vector
            moved = _step_toward(observer, dx, dy)
            trace.distance_traveled += math.hypot(moved.x - observer.x, moved.y - observer.y)
            observer = moved

            selected_track = next(
                (t for t in scenario.tracks if t.target_id == decision.selected_target_id), None
            )
            if selected_track is not None and selected_track.target_id not in captured:
                local = frame - selected_track.start_frame
                if 0 <= local < len(selected_track.positions):
                    pos = selected_track.positions[local]
                    d = math.hypot(pos.x - observer.x, pos.y - observer.y)
                    if d <= CAPTURE_RADIUS:
                        captured.add(selected_track.target_id)
                        trace.captured_frames[selected_track.target_id] = frame
                        captured_value += _capture_credit(
                            selected_track.value, frame, scenario.max_frames
                        )
                        if state.target_id == selected_track.target_id:
                            state = TargetMemoryState.empty()

    return TargetMemoryEpisodeResult(
        captured_value=captured_value,
        available_value=scenario.available_value,
        captures=len(captured),
        **trace.metrics(scenario),
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
    trace = _EpisodeTrace(
        selections=[],
        visible_ids=[],
        actions=[],
        decisions=[],
        observer_positions=[],
        target_positions=[],
        captured_frames={},
    )

    for frame in range(scenario.max_frames + 1):
        visible = _visible_candidates(scenario, frame, captured)
        target = _best_visible(visible)
        trace.selections.append(target.target_id if target is not None else None)
        trace.visible_ids.append(frozenset(c.target_id for c in visible))
        trace.actions.append(
            TargetMemoryAction.ACQUIRE if target is not None else TargetMemoryAction.IDLE
        )
        trace.decisions.append(None)
        trace.observer_positions.append((observer.x, observer.y))
        trace.target_positions.append(
            {
                t.target_id: (
                    t.positions[frame - t.start_frame].x,
                    t.positions[frame - t.start_frame].y,
                )
                for t in scenario.tracks
                if 0 <= frame - t.start_frame < len(t.positions)
            }
        )

        if target is not None:
            dx = target.position[0] - observer.x
            dy = target.position[1] - observer.y
            moved = _step_toward(observer, dx, dy)
            trace.distance_traveled += math.hypot(moved.x - observer.x, moved.y - observer.y)
            observer = moved
            selected_track = next(
                (t for t in scenario.tracks if t.target_id == target.target_id), None
            )
            if selected_track is not None and selected_track.target_id not in captured:
                local = frame - selected_track.start_frame
                if 0 <= local < len(selected_track.positions):
                    pos = selected_track.positions[local]
                    d = math.hypot(pos.x - observer.x, pos.y - observer.y)
                    if d <= CAPTURE_RADIUS:
                        captured.add(target.target_id)
                        trace.captured_frames[target.target_id] = frame
                        captured_value += _capture_credit(target.value, frame, scenario.max_frames)

    return TargetMemoryEpisodeResult(
        captured_value=captured_value,
        available_value=scenario.available_value,
        captures=len(captured),
        **trace.metrics(scenario),
    )


def _summarize(
    results: list[tuple[TargetMemoryScenario, TargetMemoryEpisodeResult]],
) -> EvaluationSummary:
    n = len(results)
    ratios = [r.capture_ratio for _, r in results]
    capture_ratio = sum(ratios) / n
    mean_captures = sum(r.captures for _, r in results) / n

    family_scores: dict[str, float] = {}
    family_counts: dict[str, int] = {}
    for scenario, r in results:
        fam = scenario.family_name
        family_scores[fam] = family_scores.get(fam, 0.0) + r.capture_ratio
        family_counts[fam] = family_counts.get(fam, 0) + 1
    family_fitness = {fam: family_scores[fam] / family_counts[fam] for fam in family_scores}

    total_reacq_events = sum(r.reacquisition_events for _, r in results)
    total_reacq_frames = sum(r.reacquisition_frames_total for _, r in results)

    return EvaluationSummary(
        capture_ratio=capture_ratio,
        mean_captures=mean_captures,
        family_fitness=family_fitness,
        overall_score=capture_ratio,
        mean_switches=sum(r.switches for _, r in results) / n,
        mean_stale_pursuit_frames=sum(r.stale_pursuit_frames for _, r in results) / n,
        mean_reacquisition_frames=(
            total_reacq_frames / total_reacq_events if total_reacq_events else 0.0
        ),
        mean_distance_traveled=sum(r.distance_traveled for _, r in results) / n,
        mean_occlusion_survived_ratio=sum(r.occlusion_survived_ratio for _, r in results) / n,
        mean_occlusion_dropped_ratio=sum(r.occlusion_dropped_ratio for _, r in results) / n,
        mean_wasted_frames=sum(r.wasted_frames for _, r in results) / n,
        mean_chasing_stale_frames=sum(r.chasing_stale_frames for _, r in results) / n,
        mean_distance_error_at_reappearance=sum(
            r.distance_error_at_reappearance for _, r in results
        )
        / n,
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
        mean_switches=sum(e.mean_switches for e in evals) / n,
        mean_stale_pursuit_frames=sum(e.mean_stale_pursuit_frames for e in evals) / n,
        mean_reacquisition_frames=sum(e.mean_reacquisition_frames for e in evals) / n,
        mean_distance_traveled=sum(e.mean_distance_traveled for e in evals) / n,
        mean_occlusion_survived_ratio=sum(e.mean_occlusion_survived_ratio for e in evals) / n,
        mean_occlusion_dropped_ratio=sum(e.mean_occlusion_dropped_ratio for e in evals) / n,
        mean_wasted_frames=sum(e.mean_wasted_frames for e in evals) / n,
        mean_chasing_stale_frames=sum(e.mean_chasing_stale_frames for e in evals) / n,
        mean_distance_error_at_reappearance=sum(
            e.mean_distance_error_at_reappearance for e in evals
        )
        / n,
    )
