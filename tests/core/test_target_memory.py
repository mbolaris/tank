"""Target Memory & Persistence v1.

Answers "what target am I committed to, and when should I switch?" for both
food-seeking and soccer-ball pursuit via one pure decision function
(core.behavior.target_memory.decide_target). See that module's docstring for
why per-fish state must never live inside a cached/compiled BehaviorGraph.
"""

from __future__ import annotations

import random

from backend.simulation_runner import SimulationRunner
from core.behavior.target_memory import (
    BALL_TARGET_ID,
    TargetCandidate,
    TargetId,
    TargetMemoryAction,
    TargetMemoryParams,
    TargetMemoryState,
    decide_target,
)
from core.behavior.target_memory_controller import advance_target_memory
from core.entities import Fish
from core.genetics.behavioral import BehavioralTraits
from core.genetics.genome import GENOME_SCHEMA_VERSION, Genome
from core.genetics.trait import GeneticTrait
from core.movement.ball_pursuit import ball_pursuit_velocity
from core.solutions.config_hash import compute_config_hash


def _food(entity_id: int, position: tuple[float, float], value: float) -> TargetCandidate:
    return TargetCandidate(
        target_id=TargetId("food", entity_id),
        position=position,
        velocity=(0.0, 0.0),
        value=value,
    )


# ---------------------------------------------------------------------------
# Pure decide_target scenarios (all 6 actions)
# ---------------------------------------------------------------------------


def test_idle_when_nothing_remembered_and_nothing_visible():
    state, decision = decide_target(TargetMemoryState.empty(), [], (0.0, 0.0), TargetMemoryParams())
    assert decision.action == TargetMemoryAction.IDLE
    assert decision.selected_target_id is None
    assert state == TargetMemoryState.empty()


def test_acquire_from_empty():
    candidate = _food(1, (10.0, 0.0), 50.0)
    state, decision = decide_target(
        TargetMemoryState.empty(), [candidate], (0.0, 0.0), TargetMemoryParams()
    )
    assert decision.action == TargetMemoryAction.ACQUIRE
    assert decision.selected_target_id == TargetId("food", 1)
    assert decision.target_vector == (10.0, 0.0)
    assert state.confidence == 1.0
    assert state.frames_since_seen == 0


def test_continue_while_visible_and_still_preferred():
    candidate = _food(1, (10.0, 0.0), 50.0)
    params = TargetMemoryParams()
    state, _ = decide_target(TargetMemoryState.empty(), [candidate], (0.0, 0.0), params)
    state, decision = decide_target(state, [candidate], (0.0, 0.0), params)
    assert decision.action == TargetMemoryAction.CONTINUE
    assert decision.selected_target_id == TargetId("food", 1)


def test_switch_while_visible_when_alternative_beats_effective_threshold():
    params = TargetMemoryParams(switch_threshold=1.4, commitment_strength=0.5)
    modest = _food(1, (10.0, 0.0), 50.0)
    state, _ = decide_target(TargetMemoryState.empty(), [modest], (0.0, 0.0), params)

    # effective_threshold at confidence=1.0 is 1.4 * 1.5 = 2.1
    just_below = _food(2, (20.0, 0.0), 50.0 * 2.1 - 0.01)
    state_a, decision_a = decide_target(state, [modest, just_below], (0.0, 0.0), params)
    assert decision_a.action == TargetMemoryAction.CONTINUE

    just_above = _food(2, (20.0, 0.0), 50.0 * 2.1 + 0.01)
    state_b, decision_b = decide_target(state, [modest, just_above], (0.0, 0.0), params)
    assert decision_b.action == TargetMemoryAction.SWITCH
    assert decision_b.selected_target_id == TargetId("food", 2)


def test_switch_during_search_via_confidence_discounted_comparison():
    """Even while a target is still within memory_duration (not yet DROPped),
    a sufficiently good alternative steals commitment - loyalty decays with
    confidence rather than being all-or-nothing at expiry."""
    params = TargetMemoryParams(switch_threshold=1.4, confidence_decay=0.3, memory_duration=50)
    original = _food(1, (10.0, 0.0), 50.0)
    state, _ = decide_target(TargetMemoryState.empty(), [original], (0.0, 0.0), params)
    state, decision = decide_target(state, [], (0.0, 0.0), params)  # lost -> SEARCH
    assert decision.action == TargetMemoryAction.SEARCH
    assert state.confidence == 0.7  # 1 - 0.3*1

    # remembered_effective_value = 50 * 0.7 * 1.4 = 49.0
    too_weak = _food(2, (5.0, 0.0), 49.0)
    state_a, decision_a = decide_target(state, [too_weak], (0.0, 0.0), params)
    assert decision_a.action == TargetMemoryAction.SEARCH

    strong_enough = _food(2, (5.0, 0.0), 49.1)
    state_b, decision_b = decide_target(state, [strong_enough], (0.0, 0.0), params)
    assert decision_b.action == TargetMemoryAction.SWITCH
    assert decision_b.selected_target_id == TargetId("food", 2)


def test_drop_on_expiry_with_nothing_to_switch_to():
    params = TargetMemoryParams(memory_duration=3, confidence_decay=0.1)
    candidate = _food(1, (10.0, 0.0), 50.0)
    state, _ = decide_target(TargetMemoryState.empty(), [candidate], (0.0, 0.0), params)

    decision = None
    for _ in range(3):
        state, decision = decide_target(state, [], (0.0, 0.0), params)
    assert decision.action == TargetMemoryAction.DROP
    assert decision.selected_target_id is None
    assert state == TargetMemoryState.empty()


def test_search_decays_confidence_and_dead_reckons_position():
    params = TargetMemoryParams(memory_duration=50, confidence_decay=0.05)
    moving = TargetCandidate(TargetId("food", 1), (10.0, 0.0), (1.0, 2.0), 50.0)
    state, _ = decide_target(TargetMemoryState.empty(), [moving], (0.0, 0.0), params)

    state, decision = decide_target(state, [], (0.0, 0.0), params)
    assert decision.action == TargetMemoryAction.SEARCH
    assert decision.target_confidence == 0.95
    assert decision.target_position == (11.0, 2.0)  # (10,0) + (1,2)*1


# ---------------------------------------------------------------------------
# Determinism / purity
# ---------------------------------------------------------------------------


def test_decide_target_is_pure_and_deterministic():
    params = TargetMemoryParams()
    candidates = [_food(1, (10.0, 0.0), 50.0), _food(2, (5.0, 5.0), 40.0)]
    state = TargetMemoryState.empty()

    result_a = decide_target(state, candidates, (0.0, 0.0), params)
    result_b = decide_target(state, candidates, (0.0, 0.0), params)
    assert result_a == result_b
    # The input state itself must not have been mutated (frozen dataclass
    # already guarantees this structurally, but confirm behaviorally too).
    assert state == TargetMemoryState.empty()


# ---------------------------------------------------------------------------
# Dead-reckoning regression (round 2, point 3: no compounding)
# ---------------------------------------------------------------------------


def test_dead_reckoning_never_compounds_across_frames():
    """last_seen_position/last_seen_velocity must stay fixed anchors across
    consecutive SEARCH frames - if a prior bug re-anchored them to each
    frame's predicted position, velocity would compound (accelerate) instead
    of extrapolating linearly."""
    params = TargetMemoryParams(memory_duration=50, motion_extrapolation_duration=50)
    moving = TargetCandidate(TargetId("food", 1), (0.0, 0.0), (1.0, 0.0), 50.0)
    state, _ = decide_target(TargetMemoryState.empty(), [moving], (0.0, 0.0), params)

    positions = []
    for _ in range(5):
        state, decision = decide_target(state, [], (0.0, 0.0), params)
        positions.append(decision.target_position[0])
        assert state.last_seen_position == (0.0, 0.0)
        assert state.last_seen_velocity == (1.0, 0.0)

    # Linear extrapolation: x = 0 + 1*frames_since_seen -> 1, 2, 3, 4, 5
    assert positions == [1.0, 2.0, 3.0, 4.0, 5.0]


def test_motion_extrapolation_freezes_after_its_duration():
    params = TargetMemoryParams(memory_duration=50, motion_extrapolation_duration=2)
    moving = TargetCandidate(TargetId("food", 1), (0.0, 0.0), (1.0, 0.0), 50.0)
    state, _ = decide_target(TargetMemoryState.empty(), [moving], (0.0, 0.0), params)

    positions = []
    for _ in range(5):
        state, decision = decide_target(state, [], (0.0, 0.0), params)
        positions.append(decision.target_position[0])

    # Extrapolates through frame 2, then freezes at x=2.0 for frames 3, 4, 5.
    assert positions == [1.0, 2.0, 2.0, 2.0, 2.0]


# ---------------------------------------------------------------------------
# Fish moves while target hidden -> vector recomputed fresh (round 1, point 1)
# ---------------------------------------------------------------------------


def test_target_vector_recomputes_from_current_observer_position():
    params = TargetMemoryParams(memory_duration=50)
    stationary = _food(1, (10.0, 0.0), 50.0)
    state, _ = decide_target(TargetMemoryState.empty(), [stationary], (0.0, 0.0), params)

    state, decision = decide_target(state, [], (0.0, 0.0), params)
    assert decision.target_vector == (10.0, 0.0)

    # The fish moved toward the remembered spot; recomputed relative vector
    # must shrink even though the remembered position itself is unchanged.
    state, decision = decide_target(state, [], (5.0, 0.0), params)
    assert decision.target_vector == (5.0, 0.0)
    assert decision.target_position == (10.0, 0.0)


# ---------------------------------------------------------------------------
# Target consumed/removed while remembered -> SEARCH, not a crash
# ---------------------------------------------------------------------------


def test_consumed_target_is_treated_as_absent_not_a_crash():
    params = TargetMemoryParams(memory_duration=50)
    candidate = _food(1, (10.0, 0.0), 50.0)
    state, _ = decide_target(TargetMemoryState.empty(), [candidate], (0.0, 0.0), params)

    # Food #1 was eaten; it simply no longer appears in the candidate list.
    state, decision = decide_target(state, [], (0.0, 0.0), params)
    assert decision.action == TargetMemoryAction.SEARCH
    assert decision.selected_target_id == TargetId("food", 1)


# ---------------------------------------------------------------------------
# Deterministic tie-break
# ---------------------------------------------------------------------------


def test_equal_value_candidates_resolve_deterministically_via_target_id():
    a = _food(5, (10.0, 0.0), 50.0)
    b = _food(2, (20.0, 0.0), 50.0)
    state, decision = decide_target(
        TargetMemoryState.empty(), [a, b], (0.0, 0.0), TargetMemoryParams()
    )
    assert decision.selected_target_id == TargetId("food", 2)  # smaller id wins

    state2, decision2 = decide_target(
        TargetMemoryState.empty(), [b, a], (0.0, 0.0), TargetMemoryParams()
    )
    assert decision2.selected_target_id == TargetId("food", 2)  # order-independent


# ---------------------------------------------------------------------------
# TargetMemoryParams: bounds, round-trip, crossover
# ---------------------------------------------------------------------------


def test_params_crossed_over_stays_within_bounds_and_round_trips():
    from core.behavior.target_memory import _PARAM_BOUNDS

    p1 = TargetMemoryParams()
    p2 = TargetMemoryParams(memory_duration=250.0, switch_threshold=2.8)
    child = p1.crossed_over(
        p2, weight1=0.3, mutation_rate=1.0, mutation_strength=1.0, rng=random.Random(11)
    )
    for key, (lo, hi) in _PARAM_BOUNDS.items():
        assert lo <= getattr(child, key) <= hi

    assert TargetMemoryParams.from_dict(child.to_dict()) == child


# ---------------------------------------------------------------------------
# Genome inheritance (rides the generic behavior_graph/target_pursuit_module loop)
# ---------------------------------------------------------------------------


def test_target_memory_inherits_through_behavioral_traits_both_modes():
    parent1 = BehavioralTraits.random(random.Random(1))
    parent2 = BehavioralTraits.random(random.Random(2))
    parent1.target_memory = GeneticTrait(TargetMemoryParams())
    parent2.target_memory = GeneticTrait(TargetMemoryParams(switch_threshold=2.0))

    blended = BehavioralTraits.from_parents(parent1, parent2, rng=random.Random(3))
    assert blended.target_memory is not None
    assert isinstance(blended.target_memory.value, TargetMemoryParams)

    recombined = BehavioralTraits.from_parents_recombination(parent1, parent2, rng=random.Random(4))
    assert recombined.target_memory is not None


def test_target_memory_absent_for_both_parents_stays_none_in_offspring():
    parent1 = BehavioralTraits.random(random.Random(5))
    parent2 = BehavioralTraits.random(random.Random(6))
    child = BehavioralTraits.from_parents(parent1, parent2, rng=random.Random(7))
    assert child.target_memory is None


# ---------------------------------------------------------------------------
# Genome serialization (persistence distinction: params ARE genome data,
# unlike the ephemeral per-fish TargetMemoryState runtime dict)
# ---------------------------------------------------------------------------


def test_genome_round_trips_target_memory():
    genome = Genome.random(rng=random.Random(1))
    genome.behavioral.target_memory = GeneticTrait(TargetMemoryParams(switch_threshold=1.8))

    data = genome.to_dict()
    assert data["schema_version"] == GENOME_SCHEMA_VERSION
    assert "target_memory" in data

    restored = Genome.from_dict(data, rng=random.Random(2))
    assert restored.behavioral.target_memory is not None
    assert restored.behavioral.target_memory.value.switch_threshold == 1.8


def test_old_genome_dict_without_target_memory_key_loads_fine():
    genome = Genome.random(rng=random.Random(3))  # no target_memory set
    data = genome.to_dict()
    assert "target_memory" not in data
    assert data["schema_version"] == GENOME_SCHEMA_VERSION - 3  # original pre-graph shape

    restored = Genome.from_dict(data, rng=random.Random(4))
    assert restored.behavioral.target_memory is None


def test_genome_validate_flags_out_of_bounds_target_memory():
    genome = Genome.random(rng=random.Random(5))
    genome.behavioral.target_memory = GeneticTrait(TargetMemoryParams(switch_threshold=999.0))
    result = genome.validate()
    assert any("target_memory" in issue for issue in result["issues"])


# ---------------------------------------------------------------------------
# Feature flag gating
# ---------------------------------------------------------------------------


def test_flag_off_trait_stays_none_and_state_dict_empty():
    runner = SimulationRunner(seed=42)
    fish = next(e for e in runner.world.entities_list if isinstance(e, Fish))
    assert fish.genome.behavioral.target_memory is None
    assert fish.target_memory_state == {}


def test_flag_on_founders_get_default_params():
    runner = SimulationRunner(seed=42, config={"target_memory_enabled": True})
    fish = next(e for e in runner.world.entities_list if isinstance(e, Fish))
    assert fish.genome.behavioral.target_memory is not None
    assert fish.genome.behavioral.target_memory.value == TargetMemoryParams()


def test_flag_off_leaves_ball_pursuit_byte_identical():
    """Flag-off run must reproduce the exact pre-target-memory RNG/decision
    sequence: same rng draws happen either way, only their downstream use
    differs, so results must match exactly."""

    def sample(seed: int) -> list[tuple[float, float] | None]:
        runner = SimulationRunner(seed=seed)
        fish = next(e for e in runner.world.entities_list if isinstance(e, Fish))
        fish.energy = fish.max_energy
        return [ball_pursuit_velocity(fish) for _ in range(20)]

    assert sample(42) == sample(42)


# ---------------------------------------------------------------------------
# Per-fish isolation (the spec's core constraint)
# ---------------------------------------------------------------------------


def test_two_fish_with_identical_params_have_independent_state():
    runner = SimulationRunner(seed=42, config={"target_memory_enabled": True})
    fish_list = [e for e in runner.world.entities_list if isinstance(e, Fish)][:2]
    assert len(fish_list) == 2
    fish_a, fish_b = fish_list

    assert fish_a.target_memory_state is not fish_b.target_memory_state

    fish_a.energy = fish_a.max_energy
    advance_target_memory(fish_a, 0)
    ball_pursuit_velocity(fish_a)
    # Mutating fish_a's memory dict must never affect fish_b's.
    fish_a.target_memory_state["probe"] = TargetMemoryState.empty()
    assert "probe" not in fish_b.target_memory_state


# ---------------------------------------------------------------------------
# Ball memory ages every frame regardless of pursuit gates (round 2, point 1)
# ---------------------------------------------------------------------------


def test_ball_memory_ages_every_frame_even_when_gates_skip_pursuit():
    runner = SimulationRunner(seed=42, config={"target_memory_enabled": True})
    fish = next(e for e in runner.world.entities_list if isinstance(e, Fish))
    # Below the play-energy threshold: every call returns None from the
    # energy gate, long before the RNG roll or memory *use* is reached.
    fish.energy = 0.0

    for frame in range(5):
        advance_target_memory(fish, frame)
        assert ball_pursuit_velocity(fish) is None

    state = fish.target_memory_state.get("ball")
    assert state is not None
    assert state.frames_since_seen == 0  # ball stayed visible throughout
    assert state.confidence == 1.0
    assert state.target_id == BALL_TARGET_ID


# ---------------------------------------------------------------------------
# Ball domain: visible_candidates iff a Ball exists (today's exists==perceived)
# ---------------------------------------------------------------------------


def test_ball_domain_visible_only_when_ball_exists():
    runner_with_ball = SimulationRunner(
        seed=42, config={"target_memory_enabled": True, "tank_ball_visible": True}
    )
    fish = next(e for e in runner_with_ball.world.entities_list if isinstance(e, Fish))
    fish.energy = fish.max_energy
    advance_target_memory(fish, 0)
    ball_pursuit_velocity(fish)
    assert fish.target_memory_state.get("ball") is not None
    assert fish.target_memory_state["ball"].target_id == BALL_TARGET_ID


# ---------------------------------------------------------------------------
# Config-hash regression
# ---------------------------------------------------------------------------


def test_simulation_config_module_is_excluded_from_config_hash():
    """target_memory_enabled lives on TankConfig in
    core/config/simulation_config.py. compute_config_hash only ever reads
    core.config.{ecosystem,entities,fish,food,plants,poker,simulation,soccer}
    (SIM_CONFIG_MODULES) - simulation_config.py isn't among them, so the
    flag's mere existence (let alone its value) cannot perturb config_hash.
    This is the structural fact the flag's safety rests on - see CLAUDE.md's
    documented past incident where a core/config/fish.py edit silently
    invalidated every champion's config_hash."""
    from core.solutions.config_hash import SIM_CONFIG_MODULES

    assert "simulation_config" not in SIM_CONFIG_MODULES


def test_config_hash_identical_whether_or_not_a_flagged_runner_ran_first():
    """Belt-and-suspenders: constructing a target_memory_enabled
    SimulationRunner in-process must not leave any side effect that changes
    a subsequent config_hash computation."""
    baseline = compute_config_hash("tank/survival_5k", seed=42)

    runner = SimulationRunner(seed=42, config={"target_memory_enabled": True})
    fish = next(e for e in runner.world.entities_list if isinstance(e, Fish))
    fish.energy = fish.max_energy
    advance_target_memory(fish, 0)
    ball_pursuit_velocity(fish)

    after = compute_config_hash("tank/survival_5k", seed=42)
    assert after == baseline


# ---------------------------------------------------------------------------
# Same-seed-twice reproducibility
# ---------------------------------------------------------------------------


def test_target_memory_state_reproducible_across_separate_seeded_runs():
    def run_and_capture() -> list[tuple]:
        runner = SimulationRunner(seed=42, config={"target_memory_enabled": True})
        fish_list = [e for e in runner.world.entities_list if isinstance(e, Fish)]
        traces = []
        for fish in fish_list[:5]:
            fish.energy = fish.max_energy
            advance_target_memory(fish, 0)
            ball_pursuit_velocity(fish)
            state = fish.target_memory_state.get("ball")
            traces.append((fish.fish_id, state))
        return traces

    trace_a = run_and_capture()
    trace_b = run_and_capture()
    assert trace_a == trace_b


# ---------------------------------------------------------------------------
# Tick-owned advancement: reads are pure, and aging survives arbiter
# short-circuiting (the lifecycle bug a 2026-07-14 review found in the
# original PR - see core/behavior/target_memory_controller.py's docstring).
# ---------------------------------------------------------------------------


def test_repeated_observation_builds_do_not_mutate_memory_within_a_frame():
    """Before this fix, build_tank_behavior_observation() advanced food
    memory as a side effect, so calling it 3x with no simulation ticks in
    between advanced frames_since_seen by 3 instead of 0."""
    from core.behavior.tank_adapter import build_tank_behavior_observation

    runner = SimulationRunner(seed=42, config={"target_memory_enabled": True})
    fish = next(e for e in runner.world.entities_list if isinstance(e, Fish))
    advance_target_memory(fish, 0)
    state_after_advance = fish.target_memory_state.get("food")

    for _ in range(3):
        build_tank_behavior_observation(fish)

    assert fish.target_memory_state.get("food") == state_after_advance


def test_get_entity_details_does_not_mutate_target_memory():
    """Before this fix, opening/polling the fish inspector (the Behavior
    Lens) advanced food memory as a side effect of building its observation,
    so merely watching a fish made it forget faster."""
    runner = SimulationRunner(
        seed=42,
        config={"target_memory_enabled": True, "graph_behavior_enabled": True},
    )
    snapshot = next(e for e in runner._collect_entities() if e.type == "fish")
    fish = next(e for e in runner.world.entities_list if isinstance(e, Fish))
    runner.step()
    state_after_tick = fish.target_memory_state.get("food")

    for _ in range(3):
        result = runner.handle_command("get_entity_details", {"entity_id": snapshot.id})
        assert result["success"] is True

    assert fish.target_memory_state.get("food") == state_after_tick


def test_memory_advances_exactly_once_per_simulation_tick():
    from core.behavior.tank_adapter import build_tank_behavior_observation

    runner = SimulationRunner(seed=42, config={"target_memory_enabled": True})
    fish = next(e for e in runner.world.entities_list if isinstance(e, Fish))
    assert fish.target_memory_updated_frame is None

    runner.step()
    frame_after_first_tick = fish.target_memory_updated_frame
    assert frame_after_first_tick is not None

    for _ in range(3):  # reads must not advance it further
        build_tank_behavior_observation(fish)
    assert fish.target_memory_updated_frame == frame_after_first_tick

    runner.step()
    assert fish.target_memory_updated_frame != frame_after_first_tick


def test_policy_override_does_not_pause_target_memory():
    """Before this fix, PolicyOverrideConsideration winning the arbiter
    short-circuited it before GraphBehaviorConsideration - the only thing
    that used to advance food memory - ever ran."""
    runner = SimulationRunner(seed=42, config={"target_memory_enabled": True})
    fish = next(e for e in runner.world.entities_list if isinstance(e, Fish))
    fish.movement_policy = lambda _observation, _rng: (1.0, 0.0)

    updated_frames = []
    for _ in range(3):
        runner.step()
        arbitration = fish.movement_strategy.last_arbitration
        assert arbitration.selected is not None
        assert arbitration.selected.source == "policy_override"
        updated_frames.append(fish.target_memory_updated_frame)

    assert len(set(updated_frames)) == 3  # advanced on every tick despite the override


def test_graph_threat_decision_does_not_pause_ball_memory():
    """Before this fix, GraphBehaviorConsideration returning THREAT
    short-circuited the arbiter before BallPursuitConsideration - the only
    thing that used to advance ball memory - ever ran."""
    from core.entities import Crab

    runner = SimulationRunner(
        seed=42,
        config={
            "target_memory_enabled": True,
            "graph_behavior_enabled": True,
            "tank_ball_visible": True,
        },
    )
    fish = next(e for e in runner.world.entities_list if isinstance(e, Fish))
    assert fish.genome.behavioral.behavior_graph is not None
    # Close enough to trigger threat detection (200px radius) but not
    # overlapping, so a same-frame collision can't confound the assertions.
    crab = Crab(environment=runner.world.environment, x=fish.pos.x + 50.0, y=fish.pos.y)
    runner.world.add_entity(crab)

    runner.step()

    arbitration = fish.movement_strategy.last_arbitration
    assert arbitration.selected is not None
    assert arbitration.selected.kind == "graph_threat_avoidance"

    state = fish.target_memory_state.get("ball")
    assert state is not None
    assert state.frames_since_seen == 0  # ball stayed visible -> memory was evaluated
    assert fish.target_memory_updated_frame is not None


def test_two_controller_ticks_advance_hidden_target_age_by_exactly_two(monkeypatch):
    """Before this fix, frames_since_seen tracked how many times an adapter
    happened to be called, not how many simulation frames actually elapsed -
    this proves two controller ticks age a hidden target by exactly two, no
    matter how many extra reads (movement, inspector, Lens) land in between,
    going through the real build_tank_behavior_observation adapter rather
    than calling decide_target directly."""
    import core.behavior.tank_adapter as tank_adapter_module
    from core.algorithms.composable.food_selection import FoodCandidateScore
    from core.entities import Food

    runner = SimulationRunner(seed=42, config={"target_memory_enabled": True})
    fish = next(e for e in runner.world.entities_list if isinstance(e, Fish))
    food = next(e for e in runner.world.entities_list if isinstance(e, Food))

    visible = [
        FoodCandidateScore(
            food=food, position=(food.pos.x, food.pos.y), velocity=(0.0, 0.0), score=50.0
        )
    ]
    monkeypatch.setattr(tank_adapter_module, "score_food_candidates", lambda _fish: visible)

    advance_target_memory(fish, 0)  # ACQUIRE
    assert fish.target_memory_state["food"].frames_since_seen == 0

    visible.clear()  # food "vanishes" and stays gone

    for frame in (1, 2):
        advance_target_memory(fish, frame)
        for _ in range(5):  # extra reads between/after ticks must not perturb aging
            tank_adapter_module.build_tank_behavior_observation(fish)

    assert fish.target_memory_state["food"].frames_since_seen == 2
