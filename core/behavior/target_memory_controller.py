"""Tick-owned advancement of per-fish target memory.

core.behavior.target_memory.decide_target is pure, but callers must invoke it
exactly once per elapsed simulation frame for frames_since_seen/confidence to
mean anything. Before this module existed, food and ball memory were each
advanced inline by the adapter function a caller happened to invoke
(core.behavior.tank_adapter.build_tank_behavior_observation,
core.movement.ball_pursuit.ball_pursuit_velocity) - which meant:

- Read-only callers (the Behavior Lens, the pursuit-module inspector) could
  advance memory just by inspecting a fish, since both are on-demand
  ``get_entity_details`` handlers that call the same adapter functions the
  real movement decision does.
- The movement arbiter's short-circuiting (core.movement.considerations)
  could skip a domain's advancement entirely: a PolicyOverrideConsideration
  win skipped GraphBehaviorConsideration (and with it, food memory), and a
  THREAT/FOOD graph decision skipped BallPursuitConsideration (and with it,
  ball memory) - despite both adapters' own docstrings claiming they ran
  unconditionally.

This module is the single place that advances every domain, called once per
fish per frame from Fish.update() before movement arbitration runs at all.
core.behavior.tank_adapter and core.movement.ball_pursuit now only *read*
Fish.last_target_memory_decisions - they never call decide_target themselves.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.entities import Fish


def advance_target_memory(fish: Fish, frame: int) -> None:
    """Advance every target-memory domain for ``fish``, at most once per ``frame``.

    A second call with the same ``frame`` is a no-op, so even an unexpected
    extra call site (or an inspector call that races a real tick) can never
    perturb aging - the one required call site is Fish.update(), before
    BehaviorExecutor.execute().
    """
    if fish.target_memory_updated_frame == frame:
        return

    from core.behavior.tank_adapter import compute_food_target_memory_decision
    from core.movement.ball_pursuit import compute_ball_target_memory_decision
    from core.behavior.target_memory import TargetMemoryAction

    old_food_decision = fish.last_target_memory_decisions.get("food")
    old_ball_decision = fish.last_target_memory_decisions.get("ball")

    new_food_decision = compute_food_target_memory_decision(fish)
    new_ball_decision = compute_ball_target_memory_decision(fish)

    fish.last_target_memory_decisions = {
        "food": new_food_decision,
        "ball": new_ball_decision,
    }
    fish.target_memory_updated_frame = frame

    # Event latching for switches and acquisitions
    food_triggered = False
    if new_food_decision is not None and new_food_decision.action in (
        TargetMemoryAction.SWITCH,
        TargetMemoryAction.ACQUIRE,
    ):
        old_id = (
            old_food_decision.selected_target_id.entity_id
            if (old_food_decision and old_food_decision.selected_target_id)
            else None
        )
        new_id = (
            new_food_decision.selected_target_id.entity_id
            if new_food_decision.selected_target_id
            else None
        )
        ev = {
            "domain": "food",
            "action": new_food_decision.action.value,
            "frame": frame,
            "from_target": old_id,
            "to_target": new_id,
        }
        fish.last_target_memory_events["food"] = ev
        fish.last_target_memory_event = ev
        food_triggered = True

    if new_ball_decision is not None and new_ball_decision.action in (
        TargetMemoryAction.SWITCH,
        TargetMemoryAction.ACQUIRE,
    ):
        old_id = (
            old_ball_decision.selected_target_id.entity_id
            if (old_ball_decision and old_ball_decision.selected_target_id)
            else None
        )
        new_id = (
            new_ball_decision.selected_target_id.entity_id
            if new_ball_decision.selected_target_id
            else None
        )
        ev = {
            "domain": "ball",
            "action": new_ball_decision.action.value,
            "frame": frame,
            "from_target": old_id,
            "to_target": new_id,
        }
        fish.last_target_memory_events["ball"] = ev
        if not food_triggered:
            fish.last_target_memory_event = ev


__all__ = ["advance_target_memory"]
