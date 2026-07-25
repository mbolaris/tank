"""Domain-neutral target commitment and memory.

Answers "what target am I committed to, and when should I switch?" for any
target-selection domain (food, soccer ball, later prey/predators/social
partners) via one pure decision function (:func:`decide_target`). This is a
separate concern from the Target Pursuit Module (``core/behavior/pursuit_nodes.py``):
pursuit answers "how do I steer to hit X", this answers "what is X, and should
it change" - they compose, with this module's output vector feeding into
``TargetObservation`` exactly like the raw candidate vector did before.

State (:class:`TargetMemoryState`) is kept per-fish, per-domain
(``Fish.target_memory_state: dict[str, TargetMemoryState]``) - never inside a
cached/compiled ``BehaviorGraph``, whose ``compile_cached()`` is a
process-global LRU keyed by content fingerprint (two fish with identical
parameters would receive the literal same compiled object, so mutable state
stored on a graph node would leak across fish).
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import Enum
from typing import Protocol

Vector2f = tuple[float, float]


@dataclass(frozen=True, order=True)
class TargetId:
    """Uniform, orderable identity across domains.

    Food ids are real per-world integers (see ``Environment.generate_new_food_id``);
    the ball uses a fixed sentinel since there is structurally at most one.
    A single type keeps ``TargetCandidate``/``TargetMemoryState``/
    ``TargetMemoryDecision`` domain-neutral and orderable (needed for a
    deterministic tie-break), so food and ball ids can never be accidentally
    cross-compared.
    """

    kind: str
    entity_id: int


BALL_TARGET_ID = TargetId("ball", 0)


# Active evolvable parameter bounds. Other parameters are frozen to defaults.
_PARAM_BOUNDS: dict[str, tuple[float, float]] = {
    "memory_duration": (10.0, 300.0),
    "motion_extrapolation_duration": (0.0, 120.0),
}


@dataclass(frozen=True)
class TargetMemoryParams:
    """Evolvable parameters governing target commitment.

    ``memory_duration`` (not ``confidence_decay``) is what gates giving up -
    confidence only modulates how picky the fish stays about switching while
    still searching, so it may legitimately reach 0 well before
    ``memory_duration`` elapses; that isn't a bug, it's an evolvable choice
    ("how quickly do I stop being picky, even though I keep searching").
    ``commitment_strength`` only affects the *visible* branch of
    :func:`decide_target` - it raises the effective switch bar above the
    baseline while a sighting is fresh, decaying back to the baseline
    (never below it) as confidence fades. Once a target is hidden, confidence
    alone drives the (separate) willingness-to-switch calculation, so folding
    commitment in there too would double-count the same signal.
    """

    memory_duration: float = 90.0
    confidence_decay: float = 0.02
    switch_threshold: float = 1.4
    commitment_strength: float = 0.5
    motion_extrapolation_duration: float = 30.0

    def to_dict(self) -> dict[str, float]:
        return {
            "memory_duration": self.memory_duration,
            "confidence_decay": self.confidence_decay,
            "switch_threshold": self.switch_threshold,
            "commitment_strength": self.commitment_strength,
            "motion_extrapolation_duration": self.motion_extrapolation_duration,
        }

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> TargetMemoryParams:
        return cls(**data)

    def crossed_over(
        self,
        other: TargetMemoryParams,
        *,
        weight1: float,
        mutation_rate: float,
        mutation_strength: float,
        rng: random.Random,
    ) -> TargetMemoryParams:
        """Blend each parameter toward self by ``weight1``, then mutate.

        Mirrors ``BehaviorGraph.crossed_over``'s blend/mutate/clamp shape
        (over a fixed field set rather than matching graph nodes), which is
        what lets this ride ``inherit_behavior_graph``'s existing generic
        loop unchanged - see core/genetics/behavioral_inheritance.py.
        """
        self_values = self.to_dict()
        other_values = other.to_dict()
        blended: dict[str, float] = {
            "confidence_decay": 0.02,
            "switch_threshold": 1.4,
            "commitment_strength": 0.5,
        }
        for key, (lo, hi) in _PARAM_BOUNDS.items():
            value = self_values[key] * weight1 + other_values[key] * (1.0 - weight1)
            if rng.random() < mutation_rate:
                span = hi - lo
                value += rng.gauss(0.0, mutation_strength * span)
            blended[key] = max(lo, min(hi, value))
        return TargetMemoryParams(**blended)


@dataclass(frozen=True)
class TargetMemoryState:
    """Per-fish, per-domain runtime memory. Immutable - decide_target returns
    a new instance for the caller to store back, rather than mutating in place."""

    target_id: TargetId | None = None
    last_seen_position: Vector2f = (0.0, 0.0)
    last_seen_velocity: Vector2f = (0.0, 0.0)
    remembered_value: float = 0.0
    confidence: float = 0.0
    frames_since_seen: int = 0

    @classmethod
    def empty(cls) -> TargetMemoryState:
        return cls()


@dataclass(frozen=True)
class TargetCandidate:
    """A perceivable target this frame, with the same "value" definition its
    domain's selector uses (e.g. food's distance/energy-weighted desirability -
    see core/algorithms/composable/food_selection.py::score_food_candidates)."""

    target_id: TargetId
    position: Vector2f
    velocity: Vector2f
    value: float


class TargetMemoryAction(str, Enum):
    IDLE = "idle"  # nothing remembered, nothing available
    ACQUIRE = "acquire"  # nothing remembered (or just expired); locking onto a candidate
    CONTINUE = "continue"  # remembered target still visible and still preferred
    SWITCH = "switch"  # remembered target replaced by a better alternative
    SEARCH = "search"  # remembered target hidden, still within memory_duration
    DROP = "drop"  # memory expired with nothing to switch to; fully gives up


@dataclass(frozen=True)
class TargetMemoryDecision:
    selected_target_id: TargetId | None
    target_position: Vector2f
    target_vector: Vector2f  # relative to observer_position, computed fresh every call
    target_velocity: Vector2f
    target_confidence: float
    action: TargetMemoryAction
    effective_switch_threshold: float | None = None
    remembered_effective_value: float | None = None
    candidate_value: float | None = None


def _vector(origin: Vector2f, point: Vector2f) -> Vector2f:
    return (point[0] - origin[0], point[1] - origin[1])


def _find(candidates: Sequence[TargetCandidate], target_id: TargetId) -> TargetCandidate | None:
    for candidate in candidates:
        if candidate.target_id == target_id:
            return candidate
    return None


def _best_candidate(
    candidates: Sequence[TargetCandidate], exclude: TargetId | None
) -> TargetCandidate | None:
    """Highest-value candidate other than ``exclude``; ties favor the smaller
    TargetId so the choice is deterministic regardless of scan order."""
    best: TargetCandidate | None = None
    for candidate in candidates:
        if exclude is not None and candidate.target_id == exclude:
            continue
        if (
            best is None
            or candidate.value > best.value
            or (candidate.value == best.value and candidate.target_id < best.target_id)
        ):
            best = candidate
    return best


def _state_for(candidate: TargetCandidate) -> TargetMemoryState:
    return TargetMemoryState(
        target_id=candidate.target_id,
        last_seen_position=candidate.position,
        last_seen_velocity=candidate.velocity,
        remembered_value=candidate.value,
        confidence=1.0,
        frames_since_seen=0,
    )


def _decision_for(
    candidate: TargetCandidate,
    observer_position: Vector2f,
    action: TargetMemoryAction,
) -> TargetMemoryDecision:
    return TargetMemoryDecision(
        selected_target_id=candidate.target_id,
        target_position=candidate.position,
        target_vector=_vector(observer_position, candidate.position),
        target_velocity=candidate.velocity,
        target_confidence=1.0,
        action=action,
    )


def _empty_decision(
    observer_position: Vector2f, action: TargetMemoryAction
) -> TargetMemoryDecision:
    return TargetMemoryDecision(
        selected_target_id=None,
        target_position=observer_position,
        target_vector=(0.0, 0.0),
        target_velocity=(0.0, 0.0),
        target_confidence=0.0,
        action=action,
    )


def decide_target(
    state: TargetMemoryState,
    visible_candidates: Sequence[TargetCandidate],
    observer_position: Vector2f,
    params: TargetMemoryParams,
) -> tuple[TargetMemoryState, TargetMemoryDecision]:
    """Decide whether to continue, switch, search for, or drop a target.

    Pure and RNG-free: callers must call this every frame (not just frames
    they act on a target) so ``frames_since_seen``/confidence reflect real
    elapsed time, then store the returned state back for next frame's call.
    """
    remembered = _find(visible_candidates, state.target_id) if state.target_id is not None else None
    alternative = _best_candidate(visible_candidates, exclude=state.target_id)

    # Diagnostic variables
    cand_value = alternative.value if alternative is not None else None

    if state.target_id is None:
        if alternative is None:
            return TargetMemoryState.empty(), TargetMemoryDecision(
                selected_target_id=None,
                target_position=observer_position,
                target_vector=(0.0, 0.0),
                target_velocity=(0.0, 0.0),
                target_confidence=0.0,
                action=TargetMemoryAction.IDLE,
                effective_switch_threshold=None,
                remembered_effective_value=None,
                candidate_value=None,
            )
        return _state_for(alternative), TargetMemoryDecision(
            selected_target_id=alternative.target_id,
            target_position=alternative.position,
            target_vector=_vector(observer_position, alternative.position),
            target_velocity=alternative.velocity,
            target_confidence=1.0,
            action=TargetMemoryAction.ACQUIRE,
            effective_switch_threshold=None,
            remembered_effective_value=None,
            candidate_value=cand_value,
        )

    if remembered is not None:
        eff_threshold = params.switch_threshold * (
            1.0 + params.commitment_strength * state.confidence
        )
        rem_eff_value = remembered.value * eff_threshold
        if alternative is not None and alternative.value > rem_eff_value:
            return _state_for(alternative), TargetMemoryDecision(
                selected_target_id=alternative.target_id,
                target_position=alternative.position,
                target_vector=_vector(observer_position, alternative.position),
                target_velocity=alternative.velocity,
                target_confidence=1.0,
                action=TargetMemoryAction.SWITCH,
                effective_switch_threshold=eff_threshold,
                remembered_effective_value=rem_eff_value,
                candidate_value=cand_value,
            )
        return _state_for(remembered), TargetMemoryDecision(
            selected_target_id=remembered.target_id,
            target_position=remembered.position,
            target_vector=_vector(observer_position, remembered.position),
            target_velocity=remembered.velocity,
            target_confidence=1.0,
            action=TargetMemoryAction.CONTINUE,
            effective_switch_threshold=eff_threshold,
            remembered_effective_value=rem_eff_value,
            candidate_value=cand_value,
        )

    # Remembered target not among this frame's candidates.
    next_frames_since_seen = state.frames_since_seen + 1
    eff_threshold = state.confidence * params.switch_threshold
    rem_eff_value = state.remembered_value * state.confidence * params.switch_threshold
    if alternative is not None and alternative.value > rem_eff_value:
        return _state_for(alternative), TargetMemoryDecision(
            selected_target_id=alternative.target_id,
            target_position=alternative.position,
            target_vector=_vector(observer_position, alternative.position),
            target_velocity=alternative.velocity,
            target_confidence=1.0,
            action=TargetMemoryAction.SWITCH,
            effective_switch_threshold=eff_threshold,
            remembered_effective_value=rem_eff_value,
            candidate_value=cand_value,
        )
    if next_frames_since_seen >= params.memory_duration:
        return TargetMemoryState.empty(), TargetMemoryDecision(
            selected_target_id=None,
            target_position=observer_position,
            target_vector=(0.0, 0.0),
            target_velocity=(0.0, 0.0),
            target_confidence=0.0,
            action=TargetMemoryAction.DROP,
            effective_switch_threshold=eff_threshold,
            remembered_effective_value=rem_eff_value,
            candidate_value=cand_value,
        )

    confidence = max(0.0, 1.0 - params.confidence_decay * next_frames_since_seen)
    extrapolation_frames = min(float(next_frames_since_seen), params.motion_extrapolation_duration)
    predicted_position = (
        state.last_seen_position[0] + state.last_seen_velocity[0] * extrapolation_frames,
        state.last_seen_position[1] + state.last_seen_velocity[1] * extrapolation_frames,
    )
    next_state = replace(state, confidence=confidence, frames_since_seen=next_frames_since_seen)
    decision = TargetMemoryDecision(
        selected_target_id=state.target_id,
        target_position=predicted_position,
        target_vector=_vector(observer_position, predicted_position),
        target_velocity=state.last_seen_velocity,
        target_confidence=confidence,
        action=TargetMemoryAction.SEARCH,
        effective_switch_threshold=eff_threshold,
        remembered_effective_value=rem_eff_value,
        candidate_value=cand_value,
    )
    return next_state, decision


class TargetMemoryHolder(Protocol):
    """Carrier of per-domain target memory - ``Fish`` in production.

    Declared structurally so this module stays free of entity imports; the
    ``hasattr`` guard below still covers carriers built without the attribute.
    """

    target_memory_state: dict[str, TargetMemoryState]


def invalidate_target_memory(
    fish: TargetMemoryHolder,
    domain: str,
    target_id: TargetId,
) -> None:
    """Invalidate a target memory if the fish knows it is completed."""
    if not hasattr(fish, "target_memory_state"):
        return
    state = fish.target_memory_state.get(domain)
    if state is not None and state.target_id == target_id:
        fish.target_memory_state[domain] = TargetMemoryState.empty()
