"""Authoritative tank decorating commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from core.tank_objects import OBJECT_DEFINITIONS, TankObject


class BuildCommands:
    """Place, move, and delete generic tank objects."""

    if TYPE_CHECKING:
        world: Any

        def _create_error_response(self, error_msg: str) -> dict[str, Any]: ...

    def _get_object(self, object_id: int) -> TankObject | None:
        engine = getattr(self.world, "engine", None)
        if engine is None:
            return None
        return next(
            (
                entity
                for entity in engine.entities_list
                if isinstance(entity, TankObject) and entity.object_id == object_id
            ),
            None,
        )

    def _valid_position(self, x: float, y: float, width: float, height: float) -> bool:
        engine = getattr(self.world, "engine", None)
        environment = getattr(engine, "environment", None) if engine else None
        if environment is None:
            return False
        (min_x, min_y), (max_x, max_y) = environment.get_bounds()
        return bool(min_x <= x and min_y <= y and x + width <= max_x and y + height <= max_y)

    def _cmd_place_tank_object(self, data: dict[str, Any]) -> dict[str, Any] | None:
        engine = getattr(self.world, "engine", None)
        if engine is None or engine.environment is None:
            return self._create_error_response("Tank engine is not available")
        kind = str(data.get("object_kind", ""))
        definition = OBJECT_DEFINITIONS.get(kind)
        if definition is None:
            return self._create_error_response(f"Unknown tank object kind: {kind}")
        x = float(data.get("x", 0.0))
        y = float(data.get("y", 0.0))
        width = float(data.get("width", definition.default_width))
        height = float(data.get("height", definition.default_height))
        if not self._valid_position(x, y, width, height):
            return self._create_error_response("Object must be fully inside the tank")
        capability_config = tuple(data.get("capability_config", ()))
        if not capability_config and kind in {"algae_reef", "protein_grotto"}:
            from core.tank_interactions import DwellTrigger, FeedingCapability, ProximityTrigger

            if kind == "algae_reef":
                capability = FeedingCapability(
                    capability_id="feeding-primary",
                    resource_type="algae",
                    capacity=240.0,
                    stock=240.0,
                    recharge_rate=0.25,
                    dispense_amount=12.0,
                    cooldown_frames=30,
                    trigger=ProximityTrigger(radius=72.0),
                )
            else:
                capability = FeedingCapability(
                    capability_id="feeding-primary",
                    resource_type="protein",
                    capacity=180.0,
                    stock=180.0,
                    recharge_rate=0.12,
                    dispense_amount=18.0,
                    cooldown_frames=45,
                    trigger=DwellTrigger(duration_frames=60, radius=58.0),
                )
            capability_config = (capability.to_config(),)
        obj = TankObject(
            engine.environment,
            x,
            y,
            object_kind=kind,
            width=width,
            height=height,
            rotation=float(data.get("rotation", 0.0)),
            capability_config=capability_config,
        )
        if engine.request_spawn(obj, reason="build_place_tank_object"):
            return {"success": True, "object": obj.to_object_state()}
        return self._create_error_response("Object placement was rejected")

    def _cmd_move_tank_object(self, data: dict[str, Any]) -> dict[str, Any] | None:
        object_id = int(data.get("object_id", -1))
        obj = self._get_object(object_id)
        if obj is None:
            return self._create_error_response(f"Tank object {object_id} was not found")
        x = float(data.get("x", obj.pos.x))
        y = float(data.get("y", obj.pos.y))
        if not self._valid_position(x, y, obj.width, obj.height):
            return self._create_error_response("Object must be fully inside the tank")
        obj.pos.x = x
        obj.pos.y = y
        obj.rect.topleft = obj.pos
        if "rotation" in data:
            obj.rotation = float(data["rotation"])
        return {"success": True, "object": obj.to_object_state()}

    def _cmd_delete_tank_object(self, data: dict[str, Any]) -> dict[str, Any] | None:
        object_id = int(data.get("object_id", -1))
        obj = self._get_object(object_id)
        if obj is None:
            return self._create_error_response(f"Tank object {object_id} was not found")
        engine = self.world.engine
        interaction_system = getattr(engine, "tank_interaction_system", None)
        if interaction_system is not None:
            interaction_system.cleanup_object(object_id)
        if engine.request_remove(obj, reason="build_delete_tank_object"):
            return {"success": True, "object_id": object_id}
        return self._create_error_response("Object deletion was rejected")
