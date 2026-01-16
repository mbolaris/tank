"""Tank-specific snapshot builder for rendering tank world state."""

from __future__ import annotations

import logging
from typing import Any, Iterable

from backend.state_payloads import EntitySnapshot
from core.config.plants import PLANT_NECTAR_ENERGY
from core.entities import Fish, Food, Plant
from core.entities.ball import Ball
from core.entities.base import Castle
from core.entities.goal_zone import GoalZone
from core.entities.plant import PlantNectar
from core.entities.predators import Crab
from core.worlds.shared.identity import TankLikeEntityIdentityProvider

logger = logging.getLogger(__name__)


class TankSnapshotBuilder:
    """Snapshot builder that converts tank entities to EntitySnapshot DTOs."""

    def __init__(self) -> None:
        self._identity_provider = TankLikeEntityIdentityProvider()

    def collect(self, live_entities: Iterable[Any]) -> list[EntitySnapshot]:
        """Collect snapshots for all live entities.

        Args:
            live_entities: Iterable of entities currently in the world

        Returns:
            List of EntitySnapshot DTOs sorted by z-order
        """
        # Ensure identity provider is in sync
        # Note: In a real hot loop, we might optimize this, but for now
        # safe correctness is prioritized.
        if isinstance(live_entities, list):
            # Prune IDs for entities that are no longer present to prevent
            # memory leaks and Python id() reuse collisions
            self._identity_provider.prune_stale_ids({id(e) for e in live_entities})
            self._identity_provider.sync_entities(live_entities)

        snapshots = []
        for entity in live_entities:
            snapshot = self.to_snapshot(entity)
            if snapshot is not None:
                snapshots.append(snapshot)

        # Sort by z-order
        # Castles (0) < Plants/Food/Nectar (1) < Fish/Crabs (2)
        snapshots.sort(key=self._get_z_order)
        return snapshots

    def build(self, step_result: Any, world: Any) -> list[EntitySnapshot]:
        """Build entity snapshots from a StepResult (protocol method)."""
        # For Tank/Petri, we typically rely on live entity collection
        # via collect(), but if step_result has entities, we could use that.
        # However, MultiAgentWorldBackend's snapshots are currently raw dicts
        # or minimal metadata. The robust path for now is to use the world's
        # entities list if available.
        entities_list = getattr(world, "entities_list", [])

        # DEBUG: Count entity types
        counts = {}
        for e in entities_list:
            t = type(e).__name__
            counts[t] = counts.get(t, 0) + 1
        logger.info(f"SNAPSHOT DEBUG: Found entities: {counts}")

        return self.collect(entities_list)

    def to_snapshot(self, entity: Any) -> EntitySnapshot | None:
        """Convert a single entity to an EntitySnapshot."""
        if not hasattr(entity, "pos") or not hasattr(entity, "width"):
            return None

        # Get stable ID and type
        entity_type, stable_id = self._identity_provider.get_identity(entity)

        # Base fields
        x = float(entity.pos.x)
        y = float(entity.pos.y)
        width = float(entity.width)
        height = float(entity.height)
        vel = getattr(entity, "vel", None)
        vel_x = float(getattr(vel, "x", 0.0)) if vel else 0.0
        vel_y = float(getattr(vel, "y", 0.0)) if vel else 0.0

        # Default minimal snapshot
        snapshot = EntitySnapshot(
            id=int(stable_id) if stable_id.isdigit() else hash(stable_id),
            type=entity_type,
            x=x,
            y=y,
            width=width,
            height=height,
            vel_x=vel_x,
            vel_y=vel_y,
        )

        # Enrich based on entity type
        if isinstance(entity, Fish):
            self._enrich_fish(snapshot, entity)
        elif isinstance(entity, Plant):
            self._enrich_plant(snapshot, entity)
        elif isinstance(entity, PlantNectar):
            self._enrich_nectar(snapshot, entity)
        elif isinstance(entity, Food):
            self._enrich_food(snapshot, entity)
        elif isinstance(entity, Crab):
            self._enrich_crab(snapshot, entity)
        elif isinstance(entity, Castle):
            # Castle is simple, just needs type (already set)
            pass
        elif isinstance(entity, Ball):
            self._enrich_ball(snapshot, entity)
            # logger.info(f"SNAPSHOT: Serializing Ball {entity.id} r={entity.radius}")
        elif isinstance(entity, GoalZone):
            self._enrich_goal_zone(snapshot, entity)
            # logger.info(f"SNAPSHOT: Serializing GoalZone {entity.id} team={entity.team_id}")

        return snapshot

    def _enrich_ball(self, snapshot: EntitySnapshot, ball: Ball) -> None:
        snapshot.radius = ball.radius
        snapshot.render_hint = {
            "style": "soccer_ball",
            "color": "#FFFFFF",
            "radius": ball.radius,
        }

    def _enrich_goal_zone(self, snapshot: EntitySnapshot, goal: GoalZone) -> None:
        snapshot.radius = goal.radius
        snapshot.team = goal.team_id
        snapshot.render_hint = {
            "style": "goal_zone",
            "team": goal.team_id,
            "radius": goal.radius,
            "color": goal.color,
        }

    def _enrich_fish(self, snapshot: EntitySnapshot, fish: Fish) -> None:
        snapshot.energy = fish.energy
        snapshot.generation = fish.generation
        # Access age via lifecycle component
        snapshot.age = fish._lifecycle_component.age
        snapshot.species = fish.species

        # Render hints & Genome Data
        if hasattr(fish, "genome"):
            gd = fish.genome.to_dict()

            # OPTIMIZATION: Strip heavy fields for WebSocket broadcast (saves ~6-10KB per fish)
            # These fields are needed for persistence/full inspection but not for 30fps visualization
            if "trait_meta" in gd:
                del gd["trait_meta"]
            if "poker_strategy" in gd:
                del gd["poker_strategy"]
            if (
                "behavior" in gd
                and isinstance(gd["behavior"], dict)
                and "parameters" in gd["behavior"]
            ):
                del gd["behavior"]["parameters"]

            snapshot.genome_data = gd

        genome = fish.genome
        snapshot.render_hint = {
            "style": "pixel",
            "sprite": "fish",
            "color_hue": genome.physical.color_hue.value,
            "highlight_color": 0xFFFFFF if getattr(fish, "is_highlighted", False) else None,
            "has_egg": getattr(fish, "is_gravid", False),
        }

        # Additional data - safely access visual effects if they exist
        vs = getattr(fish, "visual_state", None)
        if vs:
            snapshot.poker_effect_state = vs.poker_effect_state
            snapshot.birth_effect_timer = vs.birth_effect_timer
            if vs.death_effect_state:
                snapshot.death_effect_state = vs.death_effect_state

        # Soccer effect state (set directly on entity by SoccerSystem)
        if hasattr(fish, "soccer_effect_state") and fish.soccer_effect_state:
            snapshot.soccer_effect_state = fish.soccer_effect_state
            # Decrement timer and clear when expired
            fish.soccer_effect_state["timer"] -= 1
            if fish.soccer_effect_state["timer"] <= 0:
                fish.soccer_effect_state = None

    def _enrich_plant(self, snapshot: EntitySnapshot, plant: Plant) -> None:
        snapshot.energy = plant.energy
        snapshot.max_energy = plant.max_energy
        snapshot.size_multiplier = getattr(plant, "size_multiplier", 1.0)

        # Poker effect state for plants
        if hasattr(plant, "poker_effect_state"):
            snapshot.poker_effect_state = plant.poker_effect_state

        # Genome integration
        if plant.genome:
            snapshot.genome = plant.genome.to_dict()

            # Use helper method for iterations as it depends on size/energy
            snapshot.iterations = plant.get_fractal_iterations()

            # Use direct attributes from PlantGenome (flat structure)
            snapshot.floral_hue = getattr(plant.genome, "floral_hue", 0.0)
            snapshot.floral_saturation = getattr(plant.genome, "floral_saturation", 0.0)

            # Construct render hint from available properties
            snapshot.render_hint = {
                "style": "fractal",
                "color_hue": getattr(plant.genome, "color_hue", 0.0),
                "color_saturation": getattr(plant.genome, "color_saturation", 0.0),
                "leaf_density": getattr(plant.genome, "leaf_density", 0.5),
            }

            # Helper for nectar visual state
            snapshot.nectar_ready = (
                plant.nectar_cooldown == 0
                and plant.energy >= PLANT_NECTAR_ENERGY
                and plant.energy / plant.max_energy >= 0.90
            )

    def _enrich_nectar(self, snapshot: EntitySnapshot, nectar: PlantNectar) -> None:
        snapshot.energy = nectar.energy
        if nectar.source_plant:
            _, source_id = self._identity_provider.get_identity(nectar.source_plant)
            snapshot.source_plant_id = int(source_id)

    def _enrich_food(self, snapshot: EntitySnapshot, food: Food) -> None:
        # Defensive property access for robust snapshotting
        energy = getattr(food, "energy", None)
        if energy is None and hasattr(food, "get_energy_value"):
            try:
                energy = float(food.get_energy_value())
            except Exception:
                energy = None

        snapshot.energy = energy
        snapshot.food_type = getattr(food, "food_type", "regular")

    def _enrich_crab(self, snapshot: EntitySnapshot, crab: Crab) -> None:
        snapshot.energy = crab.energy
        can_hunt = getattr(crab, "can_hunt", True)
        if callable(can_hunt):
            snapshot.can_hunt = can_hunt()
        else:
            snapshot.can_hunt = can_hunt

        # Determine current action for sprite state
        action = "idle"
        if crab.vel.length_squared() > 0.1:
            action = "moving"

        snapshot.render_hint = {
            "style": "pixel",
            "sprite": "crab",
            "action": action,
            "facing_right": crab.vel.x >= 0,
        }

    def _get_z_order(self, snapshot: EntitySnapshot) -> int:
        if snapshot.type == "castle":
            return 0
        if snapshot.type in ("plant", "food", "plant_nectar"):
            return 1
        return 2
