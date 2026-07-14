"""Presenter utilities for formatting Target Memory details for the fish inspector."""

from __future__ import annotations

import math
from typing import Any


def get_target_memory_details(fish: Any) -> dict[str, Any] | None:
    """Collect Target Memory details for the inspector. Read-only."""
    config = getattr(getattr(fish, "environment", None), "simulation_config", None)
    if config is None or not getattr(config.tank, "target_memory_enabled", False):
        return None

    params_trait = getattr(fish.genome.behavioral, "target_memory", None)
    params = params_trait.value if params_trait is not None else None
    if params is None:
        return None

    # Get state and decision maps
    state_map = getattr(fish, "target_memory_state", None)
    if not isinstance(state_map, dict):
        return None

    decision_map = getattr(fish, "last_target_memory_decisions", None)
    if not isinstance(decision_map, dict):
        return None

    # Determine which domains are influencing movement
    last_arb = getattr(getattr(fish, "movement_strategy", None), "last_arbitration", None)
    selected_intent = getattr(last_arb, "selected", None) if last_arb is not None else None
    active_kind = getattr(selected_intent, "kind", "") if selected_intent is not None else ""

    # active_kind:
    # - "soccer_pursuit" -> ball
    # - "composable_behavior" | "graph_food" -> food
    influencing_domains = {
        "food": active_kind in ("composable_behavior", "graph_food"),
        "ball": active_kind == "soccer_pursuit",
    }

    # Format both domains
    domains_data = {}
    for domain in ("food", "ball"):
        state = state_map.get(domain)
        if state is None:
            continue
        decision = decision_map.get(domain)

        domain_label = "Food" if domain == "food" else "Ball"

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
            effective_threshold = switch_threshold_base * (
                1.0 + commitment_strength * confidence_val
            )
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

        domains_data[domain] = {
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
            "influencing_movement": influencing_domains[domain],
        }

    # Format recent event latch (Point 3)
    current_frame = int(getattr(getattr(fish, "environment", None), "frame_count", 0))
    event = getattr(fish, "last_target_memory_event", None)
    recent_event_data = None
    if event is not None:
        event_frame = event.get("frame", 0)
        # Latched for 25 frames
        age = current_frame - event_frame
        if 0 <= age <= 25:
            recent_event_data = {
                "domain": event["domain"],
                "action": event["action"],
                "from_target": event["from_target"],
                "to_target": event["to_target"],
                "age_frames": age,
            }

    return {
        "domains": domains_data,
        "recent_event": recent_event_data,
    }
