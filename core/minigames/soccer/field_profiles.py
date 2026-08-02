"""Backend-owned soccer field geometry profiles."""

from __future__ import annotations

import logging
from dataclasses import dataclass, fields
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SoccerFieldGeometry:
    profile_id: str
    length: float
    width: float
    goal_width: float
    goal_depth: float
    centre_circle_radius: float = 0.0
    penalty_area_depth: float = 0.0
    penalty_area_width: float = 0.0
    goal_area_depth: float = 0.0
    goal_area_width: float = 0.0
    penalty_spot_distance: float = 0.0
    corner_arc_radius: float = 0.0

    def to_dict(self) -> dict[str, float | str]:
        """Serialize the profile, omitting zero-valued optional markings."""
        data: dict[str, float | str] = {
            "profile_id": self.profile_id,
            "length": self.length,
            "width": self.width,
            "goal_width": self.goal_width,
            "goal_depth": self.goal_depth,
        }
        marking_names = {
            "centre_circle_radius",
            "penalty_area_depth",
            "penalty_area_width",
            "goal_area_depth",
            "goal_area_width",
            "penalty_spot_distance",
            "corner_arc_radius",
        }
        for item in fields(self):
            value = getattr(self, item.name)
            if item.name in marking_names:
                if value != 0:
                    data[item.name] = value
            elif item.name not in data:
                data[item.name] = value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> SoccerFieldGeometry:
        if not data:
            return rcss_standard_105x68
        profile_id = str(data.get("profile_id", "rcss_standard_105x68"))
        profile = get_field_profile(profile_id)
        values = profile.to_dict()
        # Payload values are authoritative, including an explicitly zero
        # marking. Unknown profiles use the complete standard fallback.
        for item in fields(cls):
            if item.name != "profile_id" and item.name in data:
                values[item.name] = data[item.name]
        return cls(
            profile_id=str(values["profile_id"]),
            length=float(values["length"]),
            width=float(values["width"]),
            goal_width=float(values["goal_width"]),
            goal_depth=float(values["goal_depth"]),
            centre_circle_radius=float(values["centre_circle_radius"]),
            penalty_area_depth=float(values["penalty_area_depth"]),
            penalty_area_width=float(values["penalty_area_width"]),
            goal_area_depth=float(values["goal_area_depth"]),
            goal_area_width=float(values["goal_area_width"]),
            penalty_spot_distance=float(values["penalty_spot_distance"]),
            corner_arc_radius=float(values["corner_arc_radius"]),
        )


rcss_standard_105x68 = SoccerFieldGeometry(
    profile_id="rcss_standard_105x68",
    length=105.0,
    width=68.0,
    goal_width=14.02,
    goal_depth=2.44,
    centre_circle_radius=9.15,
    penalty_area_depth=16.5,
    penalty_area_width=40.32,
    goal_area_depth=5.5,
    goal_area_width=18.32,
    penalty_spot_distance=11.0,
    corner_arc_radius=1.0,
)

# Hand-authored for the current 3v3/6v6 training pitch.  It is deliberately
# not a uniform 100/105 scale of regulation geometry.
tank_small_sided = SoccerFieldGeometry(
    profile_id="tank_small_sided",
    length=100.0,
    width=60.0,
    goal_width=13.0,
    goal_depth=2.0,
    centre_circle_radius=7.0,
    penalty_area_depth=10.0,
    penalty_area_width=28.0,
    goal_area_depth=3.5,
    goal_area_width=16.0,
    penalty_spot_distance=8.0,
    corner_arc_radius=0.75,
)

FIELD_PROFILES = {
    rcss_standard_105x68.profile_id: rcss_standard_105x68,
    tank_small_sided.profile_id: tank_small_sided,
}
_unknown_profile_ids: set[str] = set()


def get_field_profile(profile_id: str | None) -> SoccerFieldGeometry:
    requested = str(profile_id or rcss_standard_105x68.profile_id)
    profile = FIELD_PROFILES.get(requested)
    if profile is not None:
        return profile
    if requested not in _unknown_profile_ids:
        _unknown_profile_ids.add(requested)
        logger.warning(
            "Unknown soccer field profile %r; using %s", requested, rcss_standard_105x68.profile_id
        )
    return rcss_standard_105x68


def reset_profile_warning_state() -> None:
    """Test helper to make the once-per-process warning observable."""
    _unknown_profile_ids.clear()


def geometry_for_params(params: Any) -> SoccerFieldGeometry:
    """Return the compatible profile for an RCSS parameter object."""
    if (
        float(getattr(params, "field_length", 0.0)) == 100.0
        and float(getattr(params, "field_width", 0.0)) == 60.0
    ):
        return tank_small_sided
    return SoccerFieldGeometry(
        profile_id=rcss_standard_105x68.profile_id,
        length=float(getattr(params, "field_length", rcss_standard_105x68.length)),
        width=float(getattr(params, "field_width", rcss_standard_105x68.width)),
        goal_width=float(getattr(params, "goal_width", rcss_standard_105x68.goal_width)),
        goal_depth=float(getattr(params, "goal_depth", rcss_standard_105x68.goal_depth)),
        centre_circle_radius=rcss_standard_105x68.centre_circle_radius,
        penalty_area_depth=rcss_standard_105x68.penalty_area_depth,
        penalty_area_width=rcss_standard_105x68.penalty_area_width,
        goal_area_depth=rcss_standard_105x68.goal_area_depth,
        goal_area_width=rcss_standard_105x68.goal_area_width,
        penalty_spot_distance=rcss_standard_105x68.penalty_spot_distance,
        corner_arc_radius=rcss_standard_105x68.corner_arc_radius,
    )


get_profile = get_field_profile


def serialize_geometry(geometry: SoccerFieldGeometry) -> dict[str, float | str]:
    return geometry.to_dict()


def deserialize_geometry(data: dict[str, Any] | None) -> SoccerFieldGeometry:
    return SoccerFieldGeometry.from_dict(data)
