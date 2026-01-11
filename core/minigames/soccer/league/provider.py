"""Team provider for the Soccer League."""

from __future__ import annotations

from typing import Any

from core.config.simulation_config import SoccerConfig
from core.minigames.soccer.league.types import LeagueTeam, TeamAvailability, TeamSource
from core.minigames.soccer.selection import get_entity_energy, get_entity_id


class LeagueTeamProvider:
    """Provides league teams from the current world state."""

    def __init__(self, config: SoccerConfig) -> None:
        self.config = config

    def get_teams(
        self, world_state: Any
    ) -> tuple[dict[str, LeagueTeam], dict[str, TeamAvailability]]:
        """Identify all possible teams and their availability."""
        teams: dict[str, LeagueTeam] = {}
        availability: dict[str, TeamAvailability] = {}

        # 1. Identify Tank Teams
        source_groups = self._group_entities_by_source(world_state)

        for source_id, entities in source_groups.items():
            # Sort by soccer rating (using energy/genome as proxy for now, ideally Elo)
            # Todo: Integrate real Elo rating here if available on entity
            sorted_entities = sorted(
                entities, key=lambda e: (get_entity_energy(e), get_entity_id(e)), reverse=True
            )

            # Team A
            self._create_source_team(teams, availability, source_id, "A", sorted_entities, 0)

            # Team B (if we have enough for A, consider B)
            # Note: We slice from AFTER Team A
            team_size = self._get_team_size()
            self._create_source_team(
                teams, availability, source_id, "B", sorted_entities, team_size
            )

        # 2. Identify Bot Teams
        self._add_bot_teams(teams, availability)

        return teams, availability

    def _group_entities_by_source(self, world_state: Any) -> dict[str, list[Any]]:
        """Group eligible entities by their source."""
        # For now, we assume all entities in the main world belong to the "local" source
        # unless we have multi-world logic.
        # If `world_state` has a way to distinguish sources (e.g. from network), use it.
        # Fallback: All entities -> "Local"

        entities = []
        if hasattr(world_state, "get_fish_list"):
            entities = list(world_state.get_fish_list())

        # Filter eligible (alive AND can pay entry fee)
        # Note: We must check entry fee here to prevent ValueError in evaluator later
        entry_fee = self.config.entry_fee_energy

        def _is_valid(e: Any) -> bool:
            # Check dead
            if callable(getattr(e, "is_dead", None)) and e.is_dead():
                return False
            # Check energy
            energy = getattr(e, "energy", None)
            if energy is None:
                return False
            try:
                val = float(energy)
                return val > entry_fee
            except (ValueError, TypeError):
                return False

        eligible = [e for e in entities if _is_valid(e)]

        # In a single-instance sim, everyone is "Main" usually.
        # We can try to use `world_id` if available.
        world_id = getattr(world_state, "world_id", "Main")

        return {world_id: eligible}

    def _create_source_team(
        self,
        teams: dict[str, LeagueTeam],
        availability: dict[str, TeamAvailability],
        source_id: str,
        suffix: str,
        sorted_entities: list[Any],
        offset: int,
    ) -> None:
        team_id = f"{source_id}:{suffix}"
        team_size = self._get_team_size()

        candidates = sorted_entities[offset : offset + team_size]
        count = len(candidates)
        is_available = count >= team_size

        roster = [get_entity_id(e) for e in candidates]

        teams[team_id] = LeagueTeam(
            team_id=team_id,
            display_name=f"{source_id} {suffix}",
            source=TeamSource.TANK,
            source_id=source_id,
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
        # Bot:Balanced
        teams["Bot:Balanced"] = LeagueTeam(
            team_id="Bot:Balanced",
            display_name="Bot Balanced",
            source=TeamSource.BOT,
            source_id=None,
            roster=[],  # Bots adhere to special logic, empty roster implies generated
        )
        availability["Bot:Balanced"] = TeamAvailability(
            is_available=True, eligible_count=11, reason="Always available"
        )

        # We can add more bots if configured
        # e.g. if self.config.bot_count > 1...

    def _get_team_size(self) -> int:
        return self.config.team_size if self.config.team_size > 0 else 11
