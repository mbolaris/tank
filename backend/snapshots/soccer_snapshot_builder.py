"""Soccer-specific snapshot builder for rendering soccer world state."""

from __future__ import annotations

from typing import Any, Iterable

from backend.state_payloads import EntitySnapshot


class SoccerSnapshotBuilder:
    """Snapshot builder that converts soccer snapshots to EntitySnapshot DTOs."""

    def __init__(self) -> None:
        self._entity_ids: dict[str, int] = {}
        self._next_id = 1

    def collect(self, live_entities: Iterable[Any]) -> list[EntitySnapshot]:
        # Soccer snapshot data comes from build(), not live entity lists.
        _ = live_entities
        return []

    def to_snapshot(self, entity: Any) -> EntitySnapshot | None:
        if not isinstance(entity, dict):
            return None

        entity_type = entity.get("type", "unknown")
        entity_id = entity.get("id", entity_type)
        stable_id = self._get_stable_id(f"{entity_type}:{entity_id}")
        radius = entity.get("radius", 0.3)
        return EntitySnapshot(
            id=stable_id,
            type=entity_type,
            x=entity.get("x", 0.0),
            y=entity.get("y", 0.0),
            width=radius * 2,
            height=radius * 2,
            vel_x=entity.get("vx", 0.0),
            vel_y=entity.get("vy", 0.0),
            render_hint={
                "style": "soccer",
                "sprite": entity_type,
                "team": entity.get("team"),
                "stamina": entity.get("stamina"),
                "facing_angle": entity.get("facing", entity.get("facing_angle", 0.0)),
            },
        )

    def build(self, step_result: Any, world: Any) -> list[EntitySnapshot]:
        snapshots: list[EntitySnapshot] = []
        snapshot_data = getattr(step_result, "snapshot", {}) or {}

        # Transform configuration
        # Match frontend's hardcoded dimensions in SoccerTopDownRenderer.ts
        RENDER_WIDTH = 1088.0
        RENDER_HEIGHT = 612.0

        # Get sim dimensions from world config or defaults
        config = getattr(world, "_config", None)
        sim_width = getattr(config, "field_width", 100.0)
        sim_height = getattr(config, "field_height", 60.0)

        # Calculate scale and offsets
        # Sim is centered at (0,0), Render is (0,0) at top-left
        scale_x = RENDER_WIDTH / sim_width
        scale_y = RENDER_HEIGHT / sim_height
        # Use uniform scale for entities to preserve aspect ratio
        entity_scale = (scale_x + scale_y) / 2.0

        offset_x = RENDER_WIDTH / 2.0
        offset_y = RENDER_HEIGHT / 2.0

        ball_data = snapshot_data.get("ball")
        if ball_data:
            raw_radius = ball_data.get("radius", 0.2)
            radius = raw_radius * entity_scale

            raw_x = ball_data.get("x", 0.0)
            raw_y = ball_data.get("y", 0.0)

            ball_snapshot = EntitySnapshot(
                id=self._get_stable_id("ball"),
                type="ball",
                x=raw_x * scale_x + offset_x,
                y=raw_y * scale_y + offset_y,
                width=radius * 2,
                height=radius * 2,
                vel_x=ball_data.get("vx", 0.0) * scale_x,
                vel_y=ball_data.get("vy", 0.0) * scale_y,
                render_hint={
                    "style": "soccer",
                    "sprite": "ball",
                    "velocity_x": ball_data.get("vx", 0.0),
                    "velocity_y": ball_data.get("vy", 0.0),
                },
            )
            snapshots.append(ball_snapshot)

        players_data = snapshot_data.get("players", [])
        for player_data in players_data:
            player_id = player_data.get("id", "player")

            raw_radius = player_data.get("radius", 0.3)
            radius = raw_radius * entity_scale

            facing_angle = player_data.get("facing", player_data.get("facing_angle", 0.0))
            stamina = player_data.get("stamina")
            energy = player_data.get("energy")

            raw_x = player_data.get("x", 0.0)
            raw_y = player_data.get("y", 0.0)

            # Try to get genome data from the world's player_map
            genome_data = None
            player_map = getattr(world, "player_map", {})
            # Backend IDs are typically "left_0", "right_1", etc.
            # Convert player_data['id'] (which is likely the string ID) back to Fish object
            # Note: player_data['id'] is what we use.
            fish = player_map.get(str(player_id))

            if fish and hasattr(fish, "genome") and hasattr(fish.genome, "physical"):
                # Extract physical traits for rendering
                from core.genetics.physical import PHYSICAL_TRAIT_SPECS

                genome_data = {
                    spec.name: getattr(fish.genome.physical, spec.name).value
                    for spec in PHYSICAL_TRAIT_SPECS
                }

            player_snapshot = EntitySnapshot(
                id=self._get_stable_id(f"player:{player_id}"),
                type="player",
                x=raw_x * scale_x + offset_x,
                y=raw_y * scale_y + offset_y,
                width=radius * 2,
                height=radius * 2,
                vel_x=player_data.get("vx", 0.0) * scale_x,
                vel_y=player_data.get("vy", 0.0) * scale_y,
                energy=energy if energy is not None else stamina,
                genome_data=genome_data,
                render_hint={
                    "style": "soccer",
                    "sprite": "player",
                    "team": player_data.get("team"),
                    "jersey_number": player_data.get("jersey_number", 1),
                    "stamina": stamina,
                    "facing_angle": facing_angle,
                    "has_ball": player_data.get("has_ball", False),
                },
            )
            snapshots.append(player_snapshot)

        z_order = {"player": 5, "ball": 10}
        snapshots.sort(key=lambda s: z_order.get(s.type, 0))
        return snapshots

    def _get_stable_id(self, key: str) -> int:
        stable = self._entity_ids.get(key)
        if stable is None:
            stable = self._next_id
            self._next_id += 1
            self._entity_ids[key] = stable
        return stable
