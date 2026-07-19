"""Composable tank-object capabilities and deterministic interactions.

Trigger classes are immutable rules. Per-world activation, cooldown, stock, and
dwell state live in ``TankInteractionSystem`` so definitions can be shared
between worlds without leaking runtime state.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Protocol

from core.entities import Fish
from core.energy.energy_utils import apply_energy_delta
from core.events.domain_events import FeederTriggeredEvent, ResourceDispensedEvent
from core.entities.resources import Food
from core.systems.base import BaseSystem, SystemResult
from core.tank_objects import TankObject
from core.update_phases import UpdatePhase, runs_in_phase


@dataclass(frozen=True)
class InteractionContext:
    """Read-only facts used by a trigger rule."""

    actor: Any
    obj: TankObject


class InteractionTrigger(Protocol):
    @property
    def trigger_type(self) -> str:
        """Stable UI/configuration name for this trigger."""
        ...

    def is_active(self, context: InteractionContext) -> bool:
        """Return whether the actor currently satisfies this trigger."""


@dataclass(frozen=True)
class ProximityTrigger:
    radius: float = 50.0
    trigger_type: str = field(default="proximity", init=False)

    def is_active(self, context: InteractionContext) -> bool:
        return bool(_distance_between_centers(context.actor, context.obj) <= max(0.0, self.radius))


@dataclass(frozen=True)
class ContactTrigger:
    trigger_type: str = field(default="contact", init=False)

    def is_active(self, context: InteractionContext) -> bool:
        return bool(context.actor.rect.colliderect(context.obj.rect))


@dataclass(frozen=True)
class DwellTrigger:
    duration_frames: int = 90
    radius: float = 50.0
    trigger_type: str = field(default="dwell", init=False)

    def is_active(self, context: InteractionContext) -> bool:
        return bool(_distance_between_centers(context.actor, context.obj) <= max(0.0, self.radius))


@dataclass(frozen=True)
class DispensePoint:
    """An outlet in object-local coordinates."""

    x: float = 0.5
    y: float = 0.5


@dataclass(frozen=True)
class FeedingCapability:
    """Reusable resource-dispensing capability configuration."""

    capability_id: str
    resource_type: str
    capacity: float
    stock: float
    recharge_rate: float
    dispense_amount: float
    cooldown_frames: int
    trigger: InteractionTrigger
    outlets: tuple[DispensePoint, ...] = (DispensePoint(),)

    def to_config(self) -> dict[str, Any]:
        trigger_data: dict[str, Any] = {"type": self.trigger.trigger_type}
        if isinstance(self.trigger, ProximityTrigger):
            trigger_data["radius"] = self.trigger.radius
        elif isinstance(self.trigger, DwellTrigger):
            trigger_data.update(
                {"duration_frames": self.trigger.duration_frames, "radius": self.trigger.radius}
            )
        return {
            "capability_id": self.capability_id,
            "type": "feeding",
            "resource_type": self.resource_type,
            "capacity": self.capacity,
            "stock": self.stock,
            "recharge_rate": self.recharge_rate,
            "dispense_amount": self.dispense_amount,
            "cooldown_frames": self.cooldown_frames,
            "trigger": trigger_data,
            "outlets": [{"x": point.x, "y": point.y} for point in self.outlets],
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> FeedingCapability:
        trigger_data = config.get("trigger", {})
        trigger_type = trigger_data.get("type", "proximity")
        if trigger_type == "contact":
            trigger: InteractionTrigger = ContactTrigger()
        elif trigger_type == "dwell":
            trigger = DwellTrigger(
                duration_frames=int(trigger_data.get("duration_frames", 90)),
                radius=float(trigger_data.get("radius", 50.0)),
            )
        else:
            trigger = ProximityTrigger(radius=float(trigger_data.get("radius", 50.0)))
        outlets = tuple(
            DispensePoint(float(point.get("x", 0.5)), float(point.get("y", 0.5)))
            for point in config.get("outlets", [{"x": 0.5, "y": 0.5}])
        )
        return cls(
            capability_id=str(config.get("capability_id", "feeding-primary")),
            resource_type=str(config.get("resource_type", "algae")),
            capacity=max(0.0, float(config.get("capacity", 240.0))),
            stock=max(0.0, float(config.get("stock", config.get("capacity", 240.0)))),
            recharge_rate=max(0.0, float(config.get("recharge_rate", 0.25))),
            dispense_amount=max(0.0, float(config.get("dispense_amount", 12.0))),
            cooldown_frames=max(0, int(config.get("cooldown_frames", 30))),
            trigger=trigger,
            outlets=outlets or (DispensePoint(),),
        )


@dataclass(frozen=True)
class ResourceDispenseRequest:
    source_object_id: int
    capability_id: str
    resource_type: str
    amount: float
    outlet_position: tuple[float, float]
    triggering_actor_ids: tuple[int, ...]


@dataclass
class _CapabilityRuntime:
    stock: float
    cooldown_remaining: int = 0


@dataclass
class _InteractionRuntime:
    dwell_frames: dict[tuple[int, str, int], int] = field(default_factory=dict)
    capabilities: dict[tuple[int, str], _CapabilityRuntime] = field(default_factory=dict)


def _distance_between_centers(actor: Any, obj: TankObject) -> float:
    actor_center = actor.rect.center
    object_center = obj.rect.center
    return math.hypot(actor_center[0] - object_center[0], actor_center[1] - object_center[1])


def _outlet_position(obj: TankObject, point: DispensePoint) -> tuple[float, float]:
    """Convert a local outlet point to world coordinates, including rotation."""
    local_x = (point.x - 0.5) * obj.width
    local_y = (point.y - 0.5) * obj.height
    angle = math.radians(obj.rotation)
    rotated_x = local_x * math.cos(angle) - local_y * math.sin(angle)
    rotated_y = local_x * math.sin(angle) + local_y * math.cos(angle)
    center_x, center_y = obj.rect.center
    return center_x + rotated_x, center_y + rotated_y


@runs_in_phase(UpdatePhase.INTERACTION)
class TankInteractionSystem(BaseSystem):
    """Evaluates object capabilities and materializes requests during SPAWN."""

    def __init__(self, engine: Any) -> None:
        super().__init__(engine, "TankInteractions")
        self.runtime = _InteractionRuntime()
        self._pending_requests: list[ResourceDispenseRequest] = []
        self._activation_frames: dict[tuple[int, str], list[int]] = {}

    def _update_object_activity(
        self, frame: int, obj: TankObject, capability: FeedingCapability, state: _CapabilityRuntime
    ) -> None:
        """Publish a compact, ephemeral, per-capability activity summary for snapshots/UI."""
        key = (obj.object_id, capability.capability_id)
        recent_frames = [
            activation_frame
            for activation_frame in self._activation_frames.get(key, [])
            if activation_frame > frame - 600
        ]
        self._activation_frames[key] = recent_frames
        stock_percent = (
            round(100 * state.stock / capability.capacity) if capability.capacity > 0 else 0
        )
        if obj.feeder_activity is None:
            obj.feeder_activity = {}
        obj.feeder_activity[capability.capability_id] = {
            "stock_percent": stock_percent,
            "resource_type": capability.resource_type,
            "recent_activations": len(recent_frames),
            "last_activation_frame": recent_frames[-1] if recent_frames else None,
        }

    def _do_update(self, frame: int) -> SystemResult:
        objects = sorted(
            (entity for entity in self._engine.entities_list if isinstance(entity, TankObject)),
            key=lambda entity: entity.object_id,
        )
        actors = sorted(
            (entity for entity in self._engine.entities_list if isinstance(entity, Fish)),
            key=lambda entity: int(entity.get_entity_id() or 0),
        )
        object_ids = {obj.object_id for obj in objects}
        actor_ids = {int(actor.get_entity_id() or 0) for actor in actors}
        self.runtime.dwell_frames = {
            key: value
            for key, value in self.runtime.dwell_frames.items()
            if key[0] in object_ids and key[2] in actor_ids
        }
        self.runtime.capabilities = {
            key: value for key, value in self.runtime.capabilities.items() if key[0] in object_ids
        }
        self._activation_frames = {
            key: frames for key, frames in self._activation_frames.items() if key[0] in object_ids
        }
        activations = 0
        for obj in objects:
            for capability_config in obj.capability_config:
                if capability_config.get("type") != "feeding":
                    continue
                capability = FeedingCapability.from_config(capability_config)
                key = (obj.object_id, capability.capability_id)
                state = self.runtime.capabilities.setdefault(
                    key, _CapabilityRuntime(stock=capability.stock)
                )
                state.stock = min(capability.capacity, state.stock + capability.recharge_rate)
                state.cooldown_remaining = max(0, state.cooldown_remaining - 1)
                if state.cooldown_remaining > 0 or state.stock < capability.dispense_amount:
                    self._update_object_activity(frame, obj, capability, state)
                    continue

                for actor in actors:
                    interaction_key = (
                        obj.object_id,
                        capability.capability_id,
                        int(actor.get_entity_id() or 0),
                    )
                    context = InteractionContext(actor=actor, obj=obj)
                    if isinstance(capability.trigger, DwellTrigger):
                        if capability.trigger.is_active(context):
                            self.runtime.dwell_frames[interaction_key] = (
                                self.runtime.dwell_frames.get(interaction_key, 0) + 1
                            )
                        else:
                            self.runtime.dwell_frames.pop(interaction_key, None)
                        triggered = (
                            self.runtime.dwell_frames.get(interaction_key, 0)
                            >= capability.trigger.duration_frames
                        )
                    else:
                        self.runtime.dwell_frames.pop(interaction_key, None)
                        triggered = capability.trigger.is_active(context)

                    if not triggered:
                        continue
                    outlet = _outlet_position(obj, capability.outlets[0])
                    actor_id = int(actor.get_entity_id() or 0)
                    self._pending_requests.append(
                        ResourceDispenseRequest(
                            source_object_id=obj.object_id,
                            capability_id=capability.capability_id,
                            resource_type=capability.resource_type,
                            amount=capability.dispense_amount,
                            outlet_position=outlet,
                            triggering_actor_ids=(actor_id,),
                        )
                    )
                    state.stock -= capability.dispense_amount
                    state.cooldown_remaining = capability.cooldown_frames
                    self._activation_frames.setdefault(
                        (obj.object_id, capability.capability_id), []
                    ).append(frame)
                    self._emit_triggered(frame, obj, capability, actor_id)
                    activations += 1
                    if isinstance(capability.trigger, DwellTrigger):
                        self.runtime.dwell_frames[interaction_key] = 0
                    break
                self._update_object_activity(frame, obj, capability, state)
        return SystemResult(
            entities_affected=activations,
            details={"activations": activations, "pending_requests": len(self._pending_requests)},
        )

    def materialize_pending(self, frame: int) -> int:
        """Create normal Food entities during the SPAWN phase."""
        requests = sorted(
            self._pending_requests,
            key=lambda request: (
                request.source_object_id,
                request.capability_id,
                request.triggering_actor_ids,
            ),
        )
        self._pending_requests = []
        spawned = 0
        for request in requests:
            environment = self._engine.environment
            if environment is None:
                continue
            food = Food(
                environment,
                request.outlet_position[0],
                request.outlet_position[1],
                food_type=request.resource_type,
            )
            apply_energy_delta(
                food,
                request.amount - food.energy,
                source="tank_object_dispense",
                allow_direct_assignment=True,
            )
            if self._engine.request_spawn(food, reason="tank_object_dispense"):
                spawned += 1
                event_bus = getattr(environment, "event_bus", None)
                if event_bus is not None:
                    event_bus.emit(
                        ResourceDispensedEvent(
                            frame=frame,
                            object_id=request.source_object_id,
                            capability_id=request.capability_id,
                            actor_ids=request.triggering_actor_ids,
                            resource_type=request.resource_type,
                            amount=request.amount,
                        )
                    )
        return spawned

    def cleanup_object(self, object_id: int) -> None:
        self.runtime.capabilities = {
            key: value for key, value in self.runtime.capabilities.items() if key[0] != object_id
        }
        self.runtime.dwell_frames = {
            key: value for key, value in self.runtime.dwell_frames.items() if key[0] != object_id
        }

    def cleanup_actor(self, actor_id: int) -> None:
        self.runtime.dwell_frames = {
            key: value for key, value in self.runtime.dwell_frames.items() if key[2] != actor_id
        }

    def _emit_triggered(
        self, frame: int, obj: TankObject, capability: FeedingCapability, actor_id: int
    ) -> None:
        event_bus = getattr(self._engine.environment, "event_bus", None)
        if event_bus is not None:
            event_bus.emit(
                FeederTriggeredEvent(
                    frame=frame,
                    object_id=obj.object_id,
                    capability_id=capability.capability_id,
                    trigger_type=capability.trigger.trigger_type,
                    actor_id=actor_id,
                )
            )
