"""Soccer-specific snapshot builder for rendering soccer world state."""

from __future__ import annotations

from typing import Any, Iterable, List, Optional

from backend.state_payloads import EntitySnapshot


class SoccerSnapshotBuilder:
    """Snapshot builder that converts soccer entities to EntitySnapshot DTOs.
    
    This builder handles:
    - Ball: converted to a simple circle entity
    - Players: converted to positioned entities with team color hints
    """

    def collect(self, live_entities: Iterable[Any]) -> List[EntitySnapshot]:
        """Collect and sort snapshots for all live entities.
        
        For soccer, entities come from the step result snapshot, not a raw list.
        This method is provided for interface compatibility.
        """
        # Soccer doesn't use this method - entities come from build()
        return []

    def to_snapshot(self, entity: Any) -> Optional[EntitySnapshot]:
        """Convert a single entity dict to an EntitySnapshot.
        
        Args:
            entity: Dict with entity data (player or ball)
            
        Returns:
            EntitySnapshot if conversion successful
        """
        if not isinstance(entity, dict):
            return None
            
        entity_type = entity.get("type", "unknown")
        entity_id = entity.get("id", "unknown")
        
        return EntitySnapshot(
            id=entity_id,
            type=entity_type,
            x=entity.get("x", 0.0),
            y=entity.get("y", 0.0),
            width=entity.get("radius", 0.3) * 2,
            height=entity.get("radius", 0.3) * 2,
            rotation=entity.get("facing_angle", 0.0),
            z_order=1 if entity_type == "ball" else 0,
            render_hint={
                "style": "soccer",
                "sprite": entity_type,
                "team": entity.get("team"),
                "stamina": entity.get("stamina"),
            },
        )

    def build(
        self,
        step_result: Any,
        world: Any,
    ) -> List[EntitySnapshot]:
        """Build entity snapshots from a StepResult.
        
        Args:
            step_result: The result from world.reset() or world.step()
            world: The world backend (SoccerWorldBackendAdapter)
            
        Returns:
            List of EntitySnapshot DTOs sorted by z-order for rendering
        """
        snapshots: List[EntitySnapshot] = []
        snapshot_data = step_result.snapshot
        
        # Convert ball
        ball_data = snapshot_data.get("ball")
        if ball_data:
            ball_snapshot = EntitySnapshot(
                id="ball",
                type="ball",
                x=ball_data.get("x", 0.0),
                y=ball_data.get("y", 0.0),
                width=ball_data.get("radius", 0.2) * 2,
                height=ball_data.get("radius", 0.2) * 2,
                rotation=0.0,
                z_order=10,  # Ball on top
                render_hint={
                    "style": "soccer",
                    "sprite": "ball",
                    "velocity_x": ball_data.get("vx", 0.0),
                    "velocity_y": ball_data.get("vy", 0.0),
                },
            )
            snapshots.append(ball_snapshot)
        
        # Convert players
        players_data = snapshot_data.get("players", [])
        for player_data in players_data:
            player_snapshot = EntitySnapshot(
                id=player_data.get("id", "unknown"),
                type="player",
                x=player_data.get("x", 0.0),
                y=player_data.get("y", 0.0),
                width=player_data.get("radius", 0.3) * 2,
                height=player_data.get("radius", 0.3) * 2,
                rotation=player_data.get("facing_angle", 0.0),
                z_order=5,
                render_hint={
                    "style": "soccer",
                    "sprite": "player",
                    "team": player_data.get("team"),
                    "jersey_number": player_data.get("jersey_number", 1),
                    "stamina": player_data.get("stamina", 100.0),
                    "has_ball": player_data.get("has_ball", False),
                },
            )
            snapshots.append(player_snapshot)
        
        # Sort by z_order
        snapshots.sort(key=lambda s: s.z_order)
        return snapshots
