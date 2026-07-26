"""Per-entity wire payload (rendered by the frontend canvas)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class EntitySnapshot:
    """Minimal snapshot of an entity for client rendering."""

    id: int
    type: str
    x: float
    y: float
    width: float
    height: float
    vel_x: float = 0.0
    vel_y: float = 0.0
    radius: float | None = None
    team: str | None = None
    energy: float | None = None
    generation: int | None = None
    age: int | None = None
    species: str | None = None
    genome_data: dict[str, Any] | None = None
    food_type: str | None = None
    plant_type: int | None = None
    # Fractal plant fields
    genome: dict[str, Any] | None = None
    max_energy: float | None = None
    size_multiplier: float | None = None
    iterations: int | None = None
    nectar_ready: bool | None = None
    # Plant nectar fields
    source_plant_id: int | None = None
    source_plant_x: float | None = None
    source_plant_y: float | None = None
    # Floral genome for nectar rendering
    floral_type: str | None = None
    floral_petals: int | None = None
    floral_layers: int | None = None
    floral_spin: float | None = None
    floral_hue: float | None = None
    floral_saturation: float | None = None
    # Poker effects
    poker_effect_state: dict[str, Any] | None = None
    # Birth effects
    birth_effect_timer: int | None = None
    # Death effects
    death_effect_state: dict[str, Any] | None = None
    # Soccer effects (energy gain from kicks/goals)
    soccer_effect_state: dict[str, Any] | None = None
    # Crab hunt state
    can_hunt: bool | None = None
    # Rendering metadata hints
    render_hint: dict[str, Any] | None = None
    taxonomy: dict[str, Any] | None = None

    def to_full_dict(self) -> dict[str, Any]:
        """Return the full payload used on sync frames."""

        data = {
            "id": self.id,
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "vel_x": self.vel_x,
            "vel_y": self.vel_y,
        }

        if self.radius is not None:
            data["radius"] = self.radius
        if self.team is not None:
            data["team"] = self.team

        if self.energy is not None:
            data["energy"] = self.energy
        if self.generation is not None:
            data["generation"] = self.generation
        if self.age is not None:
            data["age"] = self.age
        if self.species is not None:
            data["species"] = self.species
        if self.genome_data is not None:
            data["genome_data"] = self.genome_data
        if self.food_type is not None:
            data["food_type"] = self.food_type
        if self.plant_type is not None:
            data["plant_type"] = self.plant_type
        if self.genome is not None:
            data["genome"] = self.genome
        if self.max_energy is not None:
            data["max_energy"] = self.max_energy
        if self.size_multiplier is not None:
            data["size_multiplier"] = self.size_multiplier
        if self.iterations is not None:
            data["iterations"] = self.iterations
        if self.nectar_ready is not None:
            data["nectar_ready"] = self.nectar_ready
        if self.source_plant_id is not None:
            data["source_plant_id"] = self.source_plant_id
        if self.source_plant_x is not None:
            data["source_plant_x"] = self.source_plant_x
        if self.source_plant_y is not None:
            data["source_plant_y"] = self.source_plant_y
        if self.floral_type is not None:
            data["floral_type"] = self.floral_type
        if self.floral_petals is not None:
            data["floral_petals"] = self.floral_petals
        if self.floral_layers is not None:
            data["floral_layers"] = self.floral_layers
        if self.floral_spin is not None:
            data["floral_spin"] = self.floral_spin
        if self.floral_hue is not None:
            data["floral_hue"] = self.floral_hue
        if self.floral_saturation is not None:
            data["floral_saturation"] = self.floral_saturation
        if self.poker_effect_state is not None:
            data["poker_effect_state"] = self.poker_effect_state
        if self.birth_effect_timer is not None:
            data["birth_effect_timer"] = self.birth_effect_timer
        if self.death_effect_state is not None:
            data["death_effect_state"] = self.death_effect_state
        if self.can_hunt is not None:
            data["can_hunt"] = self.can_hunt
        if self.render_hint is not None:
            data["render_hint"] = self.render_hint
        if self.soccer_effect_state is not None:
            data["soccer_effect_state"] = self.soccer_effect_state

        if self.taxonomy is not None:
            data.update(self.taxonomy)

        return data

    def to_delta_dict(self) -> dict[str, Any]:
        """Return only fast-changing fields for delta frames."""

        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "vel_x": self.vel_x,
            "vel_y": self.vel_y,
            "poker_effect_state": self.poker_effect_state,
            "birth_effect_timer": self.birth_effect_timer,
            "death_effect_state": self.death_effect_state,
            "soccer_effect_state": self.soccer_effect_state,
        }
