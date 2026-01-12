"""Team provider for the Soccer League."""

from __future__ import annotations

from typing import Any

from core.config.simulation_config import SoccerConfig
from core.minigames.soccer.league.types import LeagueTeam, TeamAvailability, TeamSource
from core.minigames.soccer.selection import get_entity_energy, get_entity_id


class LeagueTeamProvider:
    """Provides league teams from all active worlds."""

    def __init__(self, config: SoccerConfig) -> None:
        self.config = config
        # Cache results to prevent flickering availability when locks fail
        # structure: world_id -> (timestamp, teams_dict, availability_dict)
        self._cache: dict[str, tuple[float, dict[str, LeagueTeam], dict[str, TeamAvailability]]] = (
            {}
        )
        self._last_all_teams: dict[str, LeagueTeam] = {}
        self._last_all_availability: dict[str, TeamAvailability] = {}

    def get_teams(
        self, world_state: Any
    ) -> tuple[dict[str, LeagueTeam], dict[str, TeamAvailability]]:
        """Identify all possible teams and their availability from all worlds."""
        import time

        combined_teams: dict[str, LeagueTeam] = {}
        combined_availability: dict[str, TeamAvailability] = {}

        # 1. Identify Tank Teams
        # Try to find WorldManager
        world_manager = None
        if hasattr(world_state, "environment") and hasattr(
            world_state.environment, "world_manager"
        ):
            world_manager = world_state.environment.world_manager

        # Identify current world ID to skip locking
        current_world_id = None
        if hasattr(world_state, "environment") and hasattr(world_state.environment, "world_id"):
            current_world_id = world_state.environment.world_id

        # If we have a manager, iterate all worlds
        if world_manager:
            for world_id, instance in world_manager.get_all_worlds().items():
                # For each world, try to get fresh data
                teams, avail = self._get_world_teams(instance, world_id == current_world_id)
                if teams is not None and avail is not None:
                    # Update cache
                    self._cache[world_id] = (time.time(), teams, avail)
                else:
                    # Use cache if available
                    if world_id in self._cache:
                        _, teams, avail = self._cache[world_id]
                    else:
                        teams, avail = {}, {}

                combined_teams.update(teams)
                combined_availability.update(avail)
        else:
            # Fallback for tests or single-instance without manager
            # Treat world_state as the only source
            entities = []
            if hasattr(world_state, "get_fish_list"):
                entities = list(world_state.get_fish_list())

            # Try to get world_id from state
            source_id = getattr(world_state, "world_id", "Tank")

            # Use "Local" or configured world name
            name = getattr(world_state, "name", source_id)
            if hasattr(world_state, "config") and hasattr(world_state.config, "tank"):
                # Try to find a name? Default to "Tank"
                pass

            # Process single source (legacy/test path)
            eligible = self._filter_eligible(entities)
            self._process_source_group(
                combined_teams, combined_availability, source_id, name, eligible
            )

        # 2. Identify Bot Teams
        # Add global bot teams (only once)
        self._add_bot_teams(combined_teams, combined_availability)

        # Store last full result
        self._last_all_teams = combined_teams
        self._last_all_availability = combined_availability

        return combined_teams, combined_availability

    def find_entities(self, world_state: Any, entity_ids: set[Any]) -> dict[Any, Any]:
        """Find specific entities across all active worlds."""
        found: dict[Any, Any] = {}

        # Try to find WorldManager
        world_manager = None
        if hasattr(world_state, "environment") and hasattr(
            world_state.environment, "world_manager"
        ):
            world_manager = world_state.environment.world_manager

        current_world_id = None
        if hasattr(world_state, "environment") and hasattr(world_state.environment, "world_id"):
            current_world_id = world_state.environment.world_id

        if world_manager:
            for world_id, instance in world_manager.get_all_worlds().items():
                # Optimization: stop if we found everyone
                if len(found) == len(entity_ids):
                    break

                entities = self._get_world_entities_safe(instance, world_id == current_world_id)
                if entities:
                    for e in entities:
                        eid = get_entity_id(e)
                        if eid in entity_ids:
                            found[eid] = e
        else:
            # Fallback local
            if hasattr(world_state, "get_fish_list"):
                for e in world_state.get_fish_list():
                    eid = get_entity_id(e)
                    if eid in entity_ids:
                        found[eid] = e

        return found

    def _get_world_entities_safe(self, instance: Any, is_current_world: bool) -> list[Any] | None:
        runner = instance.runner
        if not hasattr(runner, "engine") or not hasattr(runner.engine, "get_fish_list"):
            return None

        if is_current_world:
            return list(runner.engine.get_fish_list())

        if hasattr(runner, "lock"):
            if runner.lock.acquire(blocking=False):
                try:
                    return list(runner.engine.get_fish_list())
                finally:
                    runner.lock.release()
        return None

    def _get_world_teams(
        self, instance: Any, is_current_world: bool
    ) -> tuple[dict[str, LeagueTeam] | None, dict[str, TeamAvailability] | None]:
        """Get teams for a specific world instance, safely handling locks."""
        entities = self._get_world_entities_safe(instance, is_current_world)

        if entities is None:
            return None, None

        teams: dict[str, LeagueTeam] = {}
        avail: dict[str, TeamAvailability] = {}

        eligible = self._filter_eligible(entities)

        # Use world name or ID for display
        source_name = instance.name or instance.world_id[:8]

        # We use world_id as source_id to be unique
        self._process_source_group(teams, avail, instance.world_id, source_name, eligible)

        return teams, avail

    def _filter_eligible(self, entities: list[Any]) -> list[Any]:
        """Filter entities that can pay the entry fee."""
        entry_fee = self.config.entry_fee_energy

        def _is_valid(e: Any) -> bool:
            if callable(getattr(e, "is_dead", None)) and e.is_dead():
                return False
            energy = getattr(e, "energy", None)
            if energy is None:
                return False
            try:
                val = float(energy)
                if entry_fee <= 0:
                    return True
                return val >= entry_fee
            except (ValueError, TypeError):
                return False

        return [e for e in entities if _is_valid(e)]

    def _process_source_group(
        self,
        teams: dict[str, LeagueTeam],
        availability: dict[str, TeamAvailability],
        source_id: str,
        display_name: str,
        eligible_entities: list[Any],
    ) -> None:
        """Create A and B teams for a source."""
        # Sort by energy/id
        sorted_entities = sorted(
            eligible_entities, key=lambda e: (get_entity_energy(e), get_entity_id(e)), reverse=True
        )

        # Team A
        # Use simple IDs that are stable-ish: "{source_id}_A"
        # But user wants display name "[TankName] A"

        # We need unique team IDs globally. source_id is unique (world_id).
        # Display name is for UI.

        self._create_team(
            teams,
            availability,
            team_id=f"{source_id}:A",
            display_name=f"{display_name} A Team",
            source_id=source_id,
            entities=sorted_entities,
            offset=0,
        )

        # Team B
        team_size = self._get_team_size()
        self._create_team(
            teams,
            availability,
            team_id=f"{source_id}:B",
            display_name=f"{display_name} B Team",
            source_id=source_id,
            entities=sorted_entities,
            offset=team_size,
        )

    def _create_team(
        self,
        teams: dict[str, LeagueTeam],
        availability: dict[str, TeamAvailability],
        team_id: str,
        display_name: str,
        source_id: str,
        entities: list[Any],
        offset: int,
    ) -> None:
        team_size = self._get_team_size()
        candidates = entities[offset : offset + team_size]
        count = len(candidates)
        is_available = count >= team_size

        roster = [get_entity_id(e) for e in candidates]

        teams[team_id] = LeagueTeam(
            team_id=team_id,
            display_name=display_name,
            source=TeamSource.TANK,
            roster=roster,
        )

        reason = "ok" if is_available else f"Not enough players ({count}/{team_size})"
        availability[team_id] = TeamAvailability(
            is_available=is_available,
            eligible_count=count,
            reason=reason,
            min_energy_threshold=self.config.entry_fee_energy,
        )

    def _add_bot_teams(
        self, teams: dict[str, LeagueTeam], availability: dict[str, TeamAvailability]
    ) -> None:
        """Add static bot teams."""
        teams["Bot:Balanced"] = LeagueTeam(
            team_id="Bot:Balanced",
            display_name="Bot Balanced",
            source=TeamSource.BOT,
            roster=[],  # Bots adhere to special logic, empty roster implies generated
        )
        availability["Bot:Balanced"] = TeamAvailability(
            is_available=True, eligible_count=11, reason="Always available"
        )

    def _get_team_size(self) -> int:
        return self.config.team_size if self.config.team_size > 0 else 11
