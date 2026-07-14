"""On-demand entity detail collection for the fish inspector (U4/E1).

The 30fps broadcast intentionally strips heavy per-fish fields (behavior
parameters, trait metadata) to keep the wire payload lean. This mixin serves
those details for a *single* entity when the client explicitly asks, via the
``get_entity_details`` command.

Read-only telemetry: handlers here never consume simulation RNG and never
mutate entity state (guardrail #1 in docs/EXPERIENCE_ROADMAP.md). The only
side effect is refreshing the identity provider's reverse-lookup map, which
is backend bookkeeping, not simulation state.
"""

from __future__ import annotations

import logging
import math
from typing import Any

logger = logging.getLogger(__name__)

GET_ENTITY_DETAILS_COMMAND = "get_entity_details"

# Energy-ratio bands matching the fish_health_* counters in
# backend/state_payloads.py (critical <15%, low 15-30%, healthy 30-80%).
_ENERGY_CRITICAL = 0.15
_ENERGY_LOW = 0.30
_ENERGY_FULL = 0.80


class EntityDetailsMixin:
    """Provides the ``get_entity_details`` command for tank-like worlds."""

    def _handle_get_entity_details(self, runner: Any, data: dict) -> dict:
        """Build a detail payload for one entity, addressed by its snapshot id.

        The id is the stable id the client sees in broadcast entity snapshots
        (fish_id + type offset), not the raw ``fish_id``.
        """
        raw_id = data.get("entity_id")
        try:
            entity_id = int(raw_id)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return {"success": False, "error": f"Invalid entity_id: {raw_id!r}"}

        provider = self._get_identity_provider(runner)
        if provider is None:
            return {"success": False, "error": "Entity identity provider unavailable"}

        # Refresh the reverse-lookup map from the live entity list so a
        # recently-removed entity resolves to "not found" rather than stale data.
        entities = getattr(runner.world, "entities_list", None) or []
        if hasattr(provider, "sync_entities"):
            provider.sync_entities(list(entities))

        entity = provider.get_entity_by_id(str(entity_id))
        if entity is None:
            return {"success": False, "error": "entity_not_found", "entity_id": entity_id}

        entity_type, _ = provider.get_identity(entity)
        details: dict[str, Any] = {
            "id": entity_id,
            "type": entity_type,
            "frame": int(getattr(runner.world, "frame_count", 0)),
        }
        try:
            if entity_type == "fish":
                details.update(_fish_details(entity))
            else:
                details.update(_generic_details(entity))
        except Exception as exc:  # Defensive: a partial payload beats a dropped command
            logger.warning("Error building entity details for %s: %s", entity_id, exc)
            details["detail_error"] = str(exc)
        return {"success": True, "details": details}

    @staticmethod
    def _get_identity_provider(runner: Any) -> Any | None:
        """Locate the engine's identity provider (canonical stable-id source)."""
        engine = getattr(runner.world, "engine", None)
        if engine is None:
            # TankWorldBackendAdapter path: runner.world.world.engine
            inner = getattr(runner.world, "world", None)
            engine = getattr(inner, "engine", None) if inner is not None else None
        return getattr(engine, "_identity_provider", None) if engine is not None else None


def _fish_details(fish: Any) -> dict[str, Any]:
    """Collect inspector details for a fish. Read-only."""
    energy = float(fish.energy)
    max_energy = float(fish.max_energy)
    energy_ratio = energy / max_energy if max_energy > 0 else 0.0
    life_stage = getattr(fish, "life_stage", None)
    parent_id = getattr(fish, "parent_id", None)

    details: dict[str, Any] = {
        "fish_id": getattr(fish, "fish_id", None),
        "energy": round(energy, 1),
        "max_energy": round(max_energy, 1),
        "energy_ratio": round(energy_ratio, 3),
        "status": _energy_status(energy_ratio),
        "age": int(fish.age),
        "max_age": int(fish.max_age),
        "life_stage": life_stage.name.lower() if life_stage is not None else None,
        "generation": int(fish.generation),
        "species": getattr(fish, "species", None),
        "taxonomy": _taxonomy_details(fish),
        "lineage": {
            "parent_id": parent_id,
            "is_soup_spawn": parent_id is None,
        },
        "behavior": _behavior_details(fish),
        "traits": _trait_details(fish),
        "games": _game_details(fish, energy_ratio),
        "modules": _pursuit_module_details(fish),
        "target_memory": _target_memory_details(fish),
    }

    repro = getattr(fish, "_reproduction_component", None)
    if repro is not None:
        details["reproduction"] = {
            "overflow_energy_bank": round(float(getattr(repro, "overflow_energy_bank", 0.0)), 1),
            "is_gravid": bool(getattr(fish, "is_gravid", False)),
        }
    return details


def _taxonomy_details(fish: Any) -> dict[str, Any] | None:
    """Return the read-only display taxonomy, if this fish has been classified."""
    taxon_id = getattr(fish, "taxon_id", "")
    if not taxon_id:
        return None
    return {
        "taxon_id": taxon_id,
        "common_name": getattr(fish, "common_name", ""),
        "scientific_name": getattr(fish, "scientific_name", ""),
        "status": getattr(fish, "species_confidence", "provisional"),
        "strain_id": getattr(fish, "strain_id", None),
    }


def _energy_status(energy_ratio: float) -> str:
    """Coarse, human-readable energy state (bands match fish_health_* stats)."""
    if energy_ratio < _ENERGY_CRITICAL:
        return "critical"
    if energy_ratio < _ENERGY_LOW:
        return "hungry"
    if energy_ratio < _ENERGY_FULL:
        return "content"
    return "full"


def _behavior_details(fish: Any) -> dict[str, Any]:
    """Behavior algorithm identity plus the on-demand parameter set.

    These are exactly the fields the broadcast strips for bandwidth
    (see TankSnapshotBuilder._enrich_fish).
    """
    behavior_trait = getattr(fish.genome.behavioral, "behavior", None)
    behavior = behavior_trait.value if behavior_trait is not None else None
    behavior_id = getattr(behavior, "behavior_id", None) if behavior is not None else None

    algorithm_name = None
    if behavior_id:
        extract = getattr(fish, "_extract_algorithm_name", None)
        algorithm_name = extract(behavior_id) if callable(extract) else str(behavior_id)[:15]

    parameters: dict[str, Any] | None = None
    if behavior is not None and hasattr(behavior, "to_dict"):
        behavior_dict = behavior.to_dict()
        raw_params = behavior_dict.get("parameters") if isinstance(behavior_dict, dict) else None
        if isinstance(raw_params, dict):
            parameters = {
                k: round(v, 4) if isinstance(v, float) else v for k, v in raw_params.items()
            }

    details = {
        "algorithm": algorithm_name,
        "behavior_id": str(behavior_id) if behavior_id else None,
        "parameters": parameters,
    }
    graph_trait = getattr(fish.genome.behavioral, "behavior_graph", None)
    graph = graph_trait.value if graph_trait is not None else None
    if graph is not None:
        details["lens"] = _graph_behavior_lens(fish, graph)
    details["movement_intent"] = _movement_intent_details(fish)
    return details


def _movement_intent_details(fish: Any) -> dict[str, Any] | None:
    """Return the last real arbitration result without re-running controllers.

    Lower-priority drives are deliberately not evaluated after a winner because
    a controller may consume simulation RNG.  They are therefore reported as
    suppressed, rather than fabricated as rejected intents.
    """
    arbitration = getattr(getattr(fish, "movement_strategy", None), "last_arbitration", None)
    if arbitration is None:
        return None
    selected = getattr(arbitration, "selected", None)
    if selected is None:
        return {"chosen": None, "suppressed_sources": []}
    return {
        "chosen": {
            "velocity": _display_node_value(selected.velocity),
            "kind": selected.kind,
            "urgency": round(float(selected.urgency), 3),
            "confidence": round(float(selected.confidence), 3),
            "target_id": selected.target_id,
            "source": selected.source,
        },
        "suppressed_sources": list(getattr(arbitration, "suppressed_sources", ())),
    }


def _graph_behavior_lens(fish: Any, graph: Any) -> dict[str, Any]:
    """Explain one selected fish's current graph decision without retaining traces."""
    from core.behavior.tank_adapter import (
        ForagingIntentKind,
        build_tank_behavior_observation,
        classify_foraging_intent,
    )

    observation = build_tank_behavior_observation(fish)
    output, node_trace = graph.compile_cached().evaluate_with_node_trace(observation.values)
    outputs = {entry.node_id: _display_node_value(entry.output) for entry in node_trace}
    explanations = {
        entry.node_id: _display_node_value(entry.explanation)
        for entry in node_trace
        if entry.explanation is not None
    }
    cohesion = observation.values["cohesion_vector"]
    # Single source of truth for what the graph selected - shared with movement
    # arbitration (GraphBehaviorConsideration) so the Lens can never disagree
    # with what the fish actually did.
    kind = classify_foraging_intent(observation, graph)
    if kind is ForagingIntentKind.THREAT:
        intent = "Fleeing threat"
    elif kind is ForagingIntentKind.FOOD:
        intent = "Chasing food"
    elif kind is ForagingIntentKind.SEARCH:
        intent = "Searching"
    elif _nonzero_vector(cohesion):
        intent = "Following the group"
    else:
        intent = "Searching"
    contributions, cancellation = _graph_contributions(
        food=observation.values["food_vector"],
        cohesion=cohesion,
        kind=kind,
        graph=graph,
    )
    return {
        "intent": intent,
        "target": observation.target_label,
        "inputs": {name: _display_node_value(value) for name, value in observation.values.items()},
        "outputs": outputs,
        "explanations": explanations,
        "output": _display_node_value(output),
        "contributions": contributions,
        "cancellation": cancellation,
        "fingerprint": graph.fingerprint(),
        "graph": graph.to_dict(),
    }


def _display_node_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _display_node_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_display_node_value(item) for item in value]
    if isinstance(value, tuple):
        return [round(float(component), 3) for component in value]
    if isinstance(value, float):
        return round(value, 3)
    return value


def _graph_contributions(
    *, food: Any, cohesion: Any, kind: Any, graph: Any
) -> tuple[dict[str, float], float]:
    """Calculate weighted-vector influence rather than displaying raw weights.

    ``kind`` is the already-computed ``ForagingIntentKind`` from
    ``classify_foraging_intent`` - reused here rather than re-deriving a
    threat/energy check independently, so this can never disagree with what
    ``_graph_behavior_lens`` (or movement arbitration) already decided.
    """
    from core.behavior.tank_adapter import ForagingIntentKind

    if kind is ForagingIntentKind.THREAT:
        return {"threat_response": 1.0, "food_pursuit": 0.0, "school_cohesion": 0.0}, 0.0
    blend = next((node for node in graph.nodes if node.node_id == "blend"), None)
    parameters = dict(getattr(blend, "parameters", {}))
    first_name, first = (
        ("school_cohesion", cohesion)
        if kind is ForagingIntentKind.COHESION
        else ("food_pursuit", food)
    )
    first_weight, second_weight = float(parameters.get("first_weight", 1.0)), float(
        parameters.get("second_weight", 0.2)
    )
    first_magnitude = first_weight * _vector_magnitude(first)
    second_magnitude = second_weight * _vector_magnitude(cohesion)
    total = first_magnitude + second_magnitude
    contributions = {"food_pursuit": 0.0, "school_cohesion": 0.0, "threat_response": 0.0}
    if total:
        contributions[first_name] += first_magnitude / total
        contributions["school_cohesion"] += second_magnitude / total
    blended = (
        first_weight * float(first[0]) + second_weight * float(cohesion[0]),
        first_weight * float(first[1]) + second_weight * float(cohesion[1]),
    )
    cancellation = 1.0 - math.hypot(*blended) / total if total else 0.0
    return contributions, max(0.0, cancellation)


def _vector_magnitude(value: Any) -> float:
    return math.hypot(float(value[0]), float(value[1])) if _nonzero_vector(value) else 0.0


def _nonzero_vector(value: Any) -> bool:
    return isinstance(value, tuple) and len(value) == 2 and (value[0] != 0.0 or value[1] != 0.0)


def _trait_details(fish: Any) -> dict[str, float]:
    """The heritable trait values shown in the Trends trait-drift chart."""
    traits: dict[str, float] = {}
    for group_name in ("physical", "behavioral"):
        group = getattr(fish.genome, group_name, None)
        if group is None:
            continue
        for trait_name in (
            "speed_modifier",
            "size_modifier",
            "color_hue",
            "aggression",
            "pursuit_aggression",
            "hunting_stamina",
            "prediction_skill",
        ):
            trait = getattr(group, trait_name, None)
            value = getattr(trait, "value", None)
            if isinstance(value, (int, float)):
                traits[trait_name] = round(float(value), 4)
    metabolism = getattr(fish.genome, "metabolism_rate", None)
    if isinstance(metabolism, (int, float)):
        traits["metabolism_rate"] = round(float(metabolism), 4)
    return traits


def _game_details(fish: Any, energy_ratio: float) -> dict[str, Any]:
    """Poker and ball-play participation. Mirrors gates read-only."""
    from core.movement.ball_pursuit import PLAY_ENERGY_THRESHOLD_RATIO

    ball = getattr(fish.environment, "ball", None)
    return {
        "poker": {
            "eligible": bool(getattr(fish, "can_play_poker", False)),
            "cooldown_frames": int(getattr(fish, "poker_cooldown", 0)),
        },
        "soccer": {
            "ball_present": ball is not None,
            # Same surplus gate as core.movement.ball_pursuit: only fish at the
            # overflow boundary spend energy on play.
            "eligible": ball is not None and energy_ratio > PLAY_ENERGY_THRESHOLD_RATIO,
        },
    }


def _pursuit_module_details(fish: Any) -> dict[str, Any] | None:
    """Explain the shared Target Pursuit Module's current parameters and aim.

    None when the fish doesn't carry the module (opt-in graph experiment
    only - see core.behavior.feature_flags). The same module instance is
    reachable by both the food adapter and the soccer-ball adapter; this
    reports whichever target the fish currently has, following the adapters'
    own food-first priority.
    """
    module_trait = getattr(fish.genome.behavioral, "target_pursuit_module", None)
    module = module_trait.value if module_trait is not None else None
    if module is None:
        return None

    target_name, target_vector, aim_vector = _pursuit_module_current_aim(fish, module)
    curr_params = _pursuit_module_parameters(module)

    # Calculate evolution statistics
    living_fish = []
    env = getattr(fish, "environment", None)
    if env is not None:
        entities = getattr(env, "entities_list", None) or []
        for e in entities:
            if hasattr(e, "genome") and hasattr(e, "fish_id"):
                living_fish.append(e)

    all_fish_params = []
    for f in living_fish:
        f_trait = getattr(f.genome.behavioral, "target_pursuit_module", None)
        f_module = f_trait.value if f_trait is not None else None
        if f_module is not None:
            f_params = _pursuit_module_parameters(f_module)
            all_fish_params.append((f, f_params))

    parameters_evolution = {}
    for k, current_value in curr_params.items():
        values = [p[k] for _, p in all_fish_params]
        species_values = [
            p[k] for f, p in all_fish_params if getattr(f, "species", None) == fish.species
        ]

        # Species median
        if species_values:
            sorted_vals = sorted(species_values)
            n = len(sorted_vals)
            if n % 2 == 1:
                species_median = sorted_vals[n // 2]
            else:
                species_median = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0
        else:
            species_median = current_value

        # Percentile within the population
        if len(values) > 1:
            less = sum(1 for v in values if v < current_value)
            equal = sum(1 for v in values if v == current_value)
            percentile = ((less + 0.5 * equal) / len(values)) * 100.0
        else:
            percentile = 50.0

        # Similar carriers: count and percent
        eps = max(0.05, 0.05 * abs(current_value))
        similar_carriers = [f for f, p in all_fish_params if abs(p[k] - current_value) <= eps]
        carriers_count = len(similar_carriers)
        carriers_pct = (carriers_count / len(living_fish)) * 100.0 if living_fish else 0.0

        # Trend calculation based on generations
        if len(all_fish_params) < 2:
            trend = "stable"
        else:
            generations = [f.generation for f, _ in all_fish_params]
            median_gen = sorted(generations)[len(generations) // 2]
            older_group = [p[k] for f, p in all_fish_params if f.generation < median_gen]
            younger_group = [p[k] for f, p in all_fish_params if f.generation >= median_gen]

            if not older_group or not younger_group:
                trend = "stable"
            else:
                older_carriers = sum(1 for v in older_group if abs(v - current_value) <= eps)
                older_prevalence = older_carriers / len(older_group)

                younger_carriers = sum(1 for v in younger_group if abs(v - current_value) <= eps)
                younger_prevalence = younger_carriers / len(younger_group)

                diff = younger_prevalence - older_prevalence
                if diff > 0.02:
                    trend = "increasing"
                elif diff < -0.02:
                    trend = "declining"
                else:
                    trend = "stable"

        # Parent value
        parent_value = None
        parent_params = getattr(fish, "parent_pursuit_params", None)
        if isinstance(parent_params, dict) and k in parent_params:
            parent_value = parent_params[k]
        else:
            parent_fish = next((f for f in living_fish if f.fish_id == fish.parent_id), None)
            if parent_fish is not None:
                p_trait = getattr(parent_fish.genome.behavioral, "target_pursuit_module", None)
                p_module = p_trait.value if p_trait is not None else None
                if p_module is not None:
                    p_params = _pursuit_module_parameters(p_module)
                    parent_value = p_params.get(k)

        parameters_evolution[k] = {
            "current": current_value,
            "parent": parent_value,
            "species_median": species_median,
            "percentile": percentile,
            "carriers_count": carriers_count,
            "carriers_pct": carriers_pct,
            "trend": trend,
        }

    return {
        "name": "Target Pursuit v1",
        "used_for": ["Food", "Soccer"],
        "parameters": curr_params,
        "parameters_evolution": parameters_evolution,
        "current_target": target_name,
        "target_vector": target_vector,
        "aim_vector": aim_vector,
        "inherited_from": getattr(fish, "parent_id", None),
    }


def _pursuit_module_parameters(module: Any) -> dict[str, float]:
    """Read the module's own evolvable parameters by calling the core utility."""
    from core.behavior.pursuit_nodes import pursuit_module_parameters

    return pursuit_module_parameters(module)


def _pursuit_module_current_aim(fish: Any, module: Any) -> tuple[str | None, Any, Any]:
    """Evaluate the module against whichever target this fish currently has.

    MovementIntent active kind is used to determine target priority.
    """
    last_arb = getattr(getattr(fish, "movement_strategy", None), "last_arbitration", None)
    selected_intent = getattr(last_arb, "selected", None)
    active_kind = getattr(selected_intent, "kind", "")

    if active_kind == "soccer_pursuit":
        ball = getattr(fish.environment, "ball", None)
        if ball is not None:
            from core.behavior.soccer_adapter import build_soccer_target_observation

            ball_observation = build_soccer_target_observation(
                self_position=(fish.pos.x, fish.pos.y),
                self_velocity=(fish.vel.x, fish.vel.y),
                self_speed=fish.speed,
                ball_position=(ball.pos.x, ball.pos.y),
                ball_velocity=(ball.vel.x, ball.vel.y),
            )
            output = module.compile_cached().evaluate(ball_observation.to_values())
            aim_vector = output if isinstance(output, tuple) and len(output) == 2 else None
            return (
                "Soccer Ball",
                _display_node_value(ball_observation.target_vector),
                _display_node_value(aim_vector),
            )

    from core.behavior.tank_adapter import build_tank_behavior_observation

    observation = build_tank_behavior_observation(fish)
    if observation.target_label is not None:
        return (
            observation.target_label,
            _display_node_value(observation.values.get("target_vector")),
            _display_node_value(observation.values.get("food_vector")),
        )

    ball = getattr(fish.environment, "ball", None)
    if ball is not None:
        from core.behavior.soccer_adapter import build_soccer_target_observation

        ball_observation = build_soccer_target_observation(
            self_position=(fish.pos.x, fish.pos.y),
            self_velocity=(fish.vel.x, fish.vel.y),
            self_speed=fish.speed,
            ball_position=(ball.pos.x, ball.pos.y),
            ball_velocity=(ball.vel.x, ball.vel.y),
        )
        output = module.compile_cached().evaluate(ball_observation.to_values())
        aim_vector = output if isinstance(output, tuple) and len(output) == 2 else None
        return (
            "Soccer Ball",
            _display_node_value(ball_observation.target_vector),
            _display_node_value(aim_vector),
        )

    return None, None, None


def _generic_details(entity: Any) -> dict[str, Any]:
    """Minimal details for non-fish entities (plants, crabs, castles, ...)."""
    details: dict[str, Any] = {}
    energy = getattr(entity, "energy", None)
    if isinstance(energy, (int, float)):
        details["energy"] = round(float(energy), 1)
    max_energy = getattr(entity, "max_energy", None)
    if isinstance(max_energy, (int, float)):
        details["max_energy"] = round(float(max_energy), 1)
    return details


def _target_memory_details(fish: Any) -> dict[str, Any] | None:
    """Collect Target Memory details for the inspector. Read-only."""
    config = getattr(getattr(fish, "environment", None), "simulation_config", None)
    if config is None or not getattr(config.tank, "target_memory_enabled", False):
        return None

    params_trait = getattr(fish.genome.behavioral, "target_memory", None)
    params = params_trait.value if params_trait is not None else None
    if params is None:
        return None

    # Determine active domain based on last arbitration kind
    last_arb = getattr(getattr(fish, "movement_strategy", None), "last_arbitration", None)
    selected_intent = getattr(last_arb, "selected", None)
    active_kind = getattr(selected_intent, "kind", "")

    if active_kind == "soccer_pursuit":
        active_domain = "ball"
    else:
        active_domain = "food"

    # Get state and decision
    state_map = getattr(fish, "target_memory_state", None)
    if not isinstance(state_map, dict):
        return None
    state = state_map.get(active_domain)
    if state is None:
        return None

    decision_map = getattr(fish, "last_target_memory_decisions", None)
    decision = decision_map.get(active_domain) if isinstance(decision_map, dict) else None

    # Domain display name
    domain_label = "Food" if active_domain == "food" else "Ball"

    # Action display name
    action_label = "Idle"
    action_val = None
    if decision is not None:
        action_val = (
            decision.action.value if hasattr(decision.action, "value") else str(decision.action)
        )
        action_label = action_val.capitalize()

    # Remembering target label
    remembering_label = "None"
    target_id = getattr(state, "target_id", None)
    if target_id is not None:
        kind = getattr(target_id, "kind", "")
        entity_id = getattr(target_id, "entity_id", 0)
        if kind == "food":
            remembering_label = f"Food #{entity_id}"
        elif kind == "ball":
            remembering_label = "Soccer Ball"
        else:
            remembering_label = f"{kind.capitalize()} #{entity_id}"

    # Last seen frames ago
    last_seen_val = getattr(state, "frames_since_seen", 0)
    last_seen_text = f"{last_seen_val} frames ago" if last_seen_val > 0 else "visible"

    # Confidence percentage
    confidence_val = getattr(state, "confidence", 0.0)
    confidence_text = f"{round(confidence_val * 100)}%"

    # Predicted location offset
    pred_offset = 0.0
    pred_location_text = "0 px ahead"
    if last_seen_val > 0 and decision is not None:
        extrapolation_duration = getattr(params, "motion_extrapolation_duration", 30.0)
        extrapolation_frames = min(float(last_seen_val), extrapolation_duration)
        vx, vy = getattr(state, "last_seen_velocity", (0.0, 0.0))
        disp_x = vx * extrapolation_frames
        disp_y = vy * extrapolation_frames
        pred_offset = math.hypot(disp_x, disp_y)
        pred_location_text = f"{round(pred_offset)} px ahead"

    # Effective switch threshold
    switch_threshold_base = getattr(params, "switch_threshold", 1.4)
    commitment_strength = getattr(params, "commitment_strength", 0.5)
    if action_val in ("continue", "switch", "acquire"):
        effective_threshold = switch_threshold_base * (1.0 + commitment_strength * confidence_val)
    elif action_val == "search":
        effective_threshold = switch_threshold_base * confidence_val
    else:
        effective_threshold = switch_threshold_base
    threshold_text = f"{round(effective_threshold, 2)}×"

    # Memory duration
    memory_duration_val = round(getattr(params, "memory_duration", 90.0))

    # Positions and vectors
    last_seen_pos = [
        round(float(state.last_seen_position[0]), 1),
        round(float(state.last_seen_position[1]), 1),
    ]
    if decision is not None:
        predicted_pos = [
            round(float(decision.target_position[0]), 1),
            round(float(decision.target_position[1]), 1),
        ]
        search_vector = [
            round(float(decision.target_vector[0]), 1),
            round(float(decision.target_vector[1]), 1),
        ]
    else:
        predicted_pos = last_seen_pos
        search_vector = [0.0, 0.0]

    # Did we switch?
    is_switching = action_val in ("switch", "acquire")

    return {
        "domain": domain_label,
        "action": action_label,
        "action_raw": action_val,
        "remembering": remembering_label,
        "last_seen": last_seen_text,
        "last_seen_frames": last_seen_val,
        "confidence": confidence_text,
        "confidence_raw": confidence_val,
        "predicted_location": pred_location_text,
        "predicted_offset": pred_offset,
        "switch_threshold": threshold_text,
        "memory_duration": memory_duration_val,
        "last_seen_position": last_seen_pos,
        "predicted_position": predicted_pos,
        "search_vector": search_vector,
        "is_switching": is_switching,
    }
