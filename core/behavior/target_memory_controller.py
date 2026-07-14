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

    fish.last_target_memory_decisions = {
        "food": compute_food_target_memory_decision(fish),
        "ball": compute_ball_target_memory_decision(fish),
    }
    fish.target_memory_updated_frame = frame


__all__ = ["advance_target_memory"]
