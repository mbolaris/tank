"""Generic, entity-backed objects placed in a tank.

This module deliberately does not introduce one Python class per object kind.
Definitions describe reusable catalog entries; ``TankObject`` instances carry
world-specific placement and runtime configuration while participating in the
normal entity lifecycle.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from core.entities.base import Entity
from core.world import World

DEFAULT_TANK_WIDTH = 1088.0
DEFAULT_TANK_HEIGHT = 612.0


@dataclass(frozen=True)
class TankObjectDefinition:
    """Immutable catalog metadata for a placeable object kind."""

    kind: str
    definition_version: int = 1
    display_name: str = "Tank Object"
    description: str = "A placeable part of the ecosystem."
    visual_asset: str | None = None
    default_width: float = 64.0
    default_height: float = 64.0
    default_capabilities: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class TankObjectLayout:
    """World-template placement; catalog definitions stay position-free."""

    kind: str
    x: float
    y: float
    width: float | None = None
    height: float | None = None
    rotation: float = 0.0


def _template_layout(
    kind: str, x: float, y: float, width: float, height: float
) -> TankObjectLayout:
    """Create a default-layout record from normalized tank coordinates.

    The template deliberately reserves the middle of the aquarium for fish and
    soccer play.  ``x``/``y`` are top-left fractions; dimensions remain pixels
    so placeable-object sizes have one unambiguous simulation representation.
    """
    return TankObjectLayout(kind, x * DEFAULT_TANK_WIDTH, y * DEFAULT_TANK_HEIGHT, width, height)


DEFAULT_TANK_LAYOUT: tuple[TankObjectLayout, ...] = (
    # Left ecological zone: lush, but clear of the goal mouth.
    _template_layout("algae_reef", 0.11, 0.70, 148.0, 106.0),
    # Small foreground details give the seabed texture without closing the
    # central swimming corridor (roughly x=0.30..0.56 of the tank).
    _template_layout("decorative_rock", 0.29, 0.86, 82.0, 48.0),
    _template_layout("decorative_rock", 0.48, 0.88, 62.0, 40.0),
    # Lower right-centre landmark: 27% smaller than the former default castle.
    _template_layout("castle", 0.57, 0.73, 120.0, 120.0),
    _template_layout("decorative_rock", 0.70, 0.87, 70.0, 44.0),
    # Right ecological zone, fully clear of the goal and tank edge.
    _template_layout("protein_grotto", 0.76, 0.74, 138.0, 104.0),
)


OBJECT_DEFINITIONS: dict[str, TankObjectDefinition] = {
    "castle": TankObjectDefinition(
        kind="castle",
        display_name="Castle",
        description="A landmark that gives the tank a sense of place.",
        visual_asset="castle-improved.png",
        default_width=120.0,
        default_height=120.0,
    ),
    "algae_reef": TankObjectDefinition(
        kind="algae_reef",
        display_name="Algae Reef",
        description="A natural habitat ready for a feeding capability.",
        visual_asset="algae_reef",
        default_width=170.0,
        default_height=105.0,
    ),
    "protein_grotto": TankObjectDefinition(
        kind="protein_grotto",
        display_name="Protein Grotto",
        description="A secluded place ready for a feeding capability.",
        visual_asset="protein_grotto",
        default_width=165.0,
        default_height=125.0,
    ),
    "decorative_rock": TankObjectDefinition(
        kind="decorative_rock",
        display_name="Decorative Rock",
        description="A quiet piece of scenery with no capabilities.",
        visual_asset="decorative_rock",
        default_width=72.0,
        default_height=50.0,
    ),
}


class TankObject(Entity):
    """A persistent, generic placeable world entity.

    ``object_id`` is the sole intrinsic world-instance identity. Mutable
    runtime interaction state will be added by capability systems, not stored
    in catalog definitions.
    """

    def __init__(
        self,
        environment: World,
        x: float,
        y: float,
        *,
        object_kind: str = "castle",
        object_id: int | None = None,
        width: float | None = None,
        height: float | None = None,
        rotation: float = 0.0,
        capability_config: tuple[dict[str, Any], ...] | list[dict[str, Any]] = (),
    ) -> None:
        super().__init__(environment, x, y)
        definition = OBJECT_DEFINITIONS.get(object_kind)
        if definition is None:
            raise ValueError(f"Unknown tank object kind: {object_kind}")
        self.object_id = object_id if object_id is not None else self._allocate_id(environment)
        if self.object_id < 0:
            raise ValueError("object_id must be non-negative")
        environment._next_tank_object_id = max(  # type: ignore[attr-defined]
            getattr(environment, "_next_tank_object_id", 1), self.object_id + 1
        )
        self.object_kind = object_kind
        self.rotation = float(rotation)
        self.capability_config = tuple(dict(item) for item in capability_config)
        self.blocks_root_spots = object_kind == "castle"
        self.set_size(
            definition.default_width if width is None else width,
            definition.default_height if height is None else height,
        )

    @staticmethod
    def _allocate_id(environment: World) -> int:
        object_id = getattr(environment, "_next_tank_object_id", 1)
        environment._next_tank_object_id = object_id + 1  # type: ignore[attr-defined]
        return object_id

    @property
    def snapshot_type(self) -> str:
        return self.object_kind

    def get_entity_id(self) -> int:
        return self.object_id

    def is_dead(self) -> bool:
        return False

    def to_object_state(self) -> dict[str, Any]:
        """Return the serializable instance state, excluding catalog metadata."""
        return {
            "type": self.object_kind,
            "object_id": self.object_id,
            "x": self.pos.x,
            "y": self.pos.y,
            "width": self.width,
            "height": self.height,
            "rotation": self.rotation,
            "capability_config": [dict(item) for item in self.capability_config],
        }


class _CastleCompatibilityMeta(type):
    """Keep legacy ``isinstance(entity, Castle)`` checks semantically precise."""

    def __instancecheck__(cls, instance: object) -> bool:
        return isinstance(instance, TankObject) and instance.object_kind == "castle"


class Castle(metaclass=_CastleCompatibilityMeta):
    """Compatibility constructor for the generic castle object.

    New code constructs ``TankObject(object_kind="castle")`` directly.  This
    shim avoids treating every generic tank object as a castle in legacy code.
    """

    def __new__(cls, environment: World, x: float = 431.0, y: float = 387.0) -> Castle:
        # ``Castle`` is a type-only compatibility surface; its concrete
        # instances are the generic TankObject configured as a castle.
        return cast(Castle, TankObject(environment, x, y, object_kind="castle"))

    @property
    def snapshot_type(self) -> str:
        """Legacy class-level contract; concrete instances are TankObjects."""
        return "castle"
