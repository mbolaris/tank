"""Soccer participant protocol for entity-agnostic soccer matches.

This module defines a protocol for entities that can participate in soccer
matches, decoupling the match logic from specific entity types (Fish, Microbe).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from core.entities import Fish


@runtime_checkable
class SoccerParticipantProtocol(Protocol):
    """Protocol for entities that can participate in soccer matches."""

    @property
    def participant_id(self) -> str:
        """Unique identifier for this participant."""
        ...

    @property
    def team(self) -> str:
        """Team assignment ('left' or 'right')."""
        ...

    @property
    def genome_ref(self) -> Any | None:
        """Reference to genome for policy lookup."""
        ...

    @property
    def render_hint(self) -> dict | None:
        """Rendering hints (genome data for avatar)."""
        ...


@dataclass
class SoccerParticipant:
    """Concrete participant for soccer matches.

    This dataclass provides a simple, entity-agnostic representation
    of a soccer player. It can be created from Fish or other entities.

    Attributes:
        participant_id: Unique identifier for this participant
        team: Team assignment ('left' or 'right')
        genome_ref: Optional reference to genome for policy lookup
        render_hint: Optional rendering hints (genome data for avatar)
        fish_id: Optional aquarium identity.  This is an identity value, not
            a reference to the live fish.
    """

    participant_id: str
    team: str
    genome_ref: Any | None = None
    render_hint: dict | None = None
    team_id: str | None = None
    uniform_number: int | None = None
    avatar_kind: str = "fish"
    fish_id: int | None = None
    tank_id: str | None = None
    generation: int | None = None
    parent_id: int | None = None
    policy_label: str | None = None
    repro_credit_capable: bool = False
    energy: float | None = None
    max_energy: float | None = None
    display_name: str | None = None
    tank_name: str | None = None
    offspring_count: int = 0

    def __post_init__(self) -> None:
        # ``team`` is the established internal side name.  ``team_id`` is the
        # stable wire identity and intentionally has a separate namespace.
        if self.team_id is None:
            self.team_id = self.team
        if self.uniform_number is None:
            try:
                self.uniform_number = int(self.participant_id.rsplit("_", 1)[1])
            except (IndexError, ValueError):
                self.uniform_number = 0

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "participant_id": self.participant_id,
            "side": self.team,
            "team_id": self.team_id,
            "uniform_number": self.uniform_number,
            "avatar_kind": self.avatar_kind,
        }
        for name in (
            "fish_id",
            "tank_id",
            "generation",
            "parent_id",
            "policy_label",
            "display_name",
            "tank_name",
            "offspring_count",
        ):
            value = getattr(self, name)
            if value is not None:
                data[name] = value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SoccerParticipant:
        return cls(
            participant_id=str(data["participant_id"]),
            team=str(data.get("side", data.get("team", "left"))),
            team_id=str(data.get("team_id", data.get("side", "left"))),
            uniform_number=int(data.get("uniform_number", 0)),
            avatar_kind=str(data.get("avatar_kind", "bot")),
            fish_id=data.get("fish_id"),
            tank_id=data.get("tank_id"),
            generation=data.get("generation"),
            parent_id=data.get("parent_id"),
            policy_label=data.get("policy_label"),
            display_name=data.get("display_name"),
            tank_name=data.get("tank_name"),
            offspring_count=int(data.get("offspring_count", 0)),
        )


def fish_to_participant(
    fish: Fish,
    team: str,
    player_index: int,
) -> SoccerParticipant:
    """Convert a Fish entity to a SoccerParticipant.

    Args:
        fish: The Fish entity to convert
        team: Team assignment ('left' or 'right')
        player_index: Index of player on team (1-based)

    Returns:
        SoccerParticipant with fish data
    """
    # Extract genome data for rendering
    render_hint: dict | None = None
    genome_ref = getattr(fish, "genome", None)

    if (
        genome_ref
        and hasattr(genome_ref, "physical")
        and getattr(genome_ref, "physical", None) is not None
    ):
        try:
            from core.genetics.physical import PHYSICAL_TRAIT_SPECS

            candidate_hint = {
                spec.name: getattr(genome_ref.physical, spec.name).value
                for spec in PHYSICAL_TRAIT_SPECS
            }
            if all(isinstance(value, (bool, int, float, str)) for value in candidate_hint.values()):
                render_hint = candidate_hint
        except Exception:
            logger.debug("Failed to build render hints from physical traits", exc_info=True)

    raw_tank_id = getattr(fish, "tank_id", None)
    tank_id = raw_tank_id if isinstance(raw_tank_id, str) else None
    raw_generation = getattr(fish, "generation", None)
    generation = raw_generation if isinstance(raw_generation, int) else None
    raw_parent_id = getattr(fish, "parent_id", None)
    parent_id = raw_parent_id if isinstance(raw_parent_id, int) else None
    raw_display_name = getattr(fish, "name", None)
    display_name = raw_display_name if isinstance(raw_display_name, str) else None
    raw_tank_name = getattr(fish, "tank_name", None)
    tank_name = raw_tank_name if isinstance(raw_tank_name, str) else None
    raw_offspring_count = getattr(fish, "offspring_count", 0)
    offspring_count = int(raw_offspring_count) if isinstance(raw_offspring_count, int) else 0
    raw_energy = getattr(fish, "energy", None)
    energy = float(raw_energy) if isinstance(raw_energy, (int, float)) else None
    raw_max_energy = getattr(fish, "max_energy", None)
    max_energy = float(raw_max_energy) if isinstance(raw_max_energy, (int, float)) else None

    return SoccerParticipant(
        participant_id=f"{team}_{player_index}",
        team=team,
        genome_ref=genome_ref,
        render_hint=render_hint,
        team_id=tank_id or team,
        uniform_number=player_index,
        # Entities that are not tank fish (bots, reference policies) reach this
        # function because they carry a `fish_id`; they declare their own kind
        # so the arena can take its neutral render branch (§6.3) instead of
        # drawing them as fish with a genome they do not have.
        avatar_kind=str(getattr(fish, "avatar_kind", "fish")),
        fish_id=(int(fish.fish_id) if getattr(fish, "fish_id", None) is not None else None),
        tank_id=tank_id,
        generation=generation,
        parent_id=parent_id,
        energy=energy,
        max_energy=max_energy,
        display_name=display_name,
        tank_name=tank_name,
        offspring_count=offspring_count,
        repro_credit_capable=hasattr(
            getattr(fish, "reproduction_component", None), "add_repro_credits"
        )
        or hasattr(getattr(fish, "_reproduction_component", None), "add_repro_credits"),
    )


def create_participants(
    entities: list[Any],
) -> tuple[list[SoccerParticipantProtocol], dict[str, Any]]:
    """Create balanced teams of participants from a list of entities.

    This is the main entry point for adapting entities to SoccerParticipant.
    It supports:
    - Already-adapted SoccerParticipantProtocol objects (used directly)
    - Fish-like entities with fish_id (Fish, BotEntity, etc.)

    Args:
        entities: List of entities to convert (Fish, BotEntity, or SoccerParticipantProtocol)

    Returns:
        Tuple of (participants list, participant_id -> entity mapping)

    Raises:
        TypeError: If an entity doesn't have fish_id and isn't a SoccerParticipantProtocol
    """
    # Ensure even number of players
    if len(entities) % 2 != 0:
        entities = entities[:-1]

    half = len(entities) // 2
    participants: list[SoccerParticipantProtocol] = []
    entity_map: dict[str, Any] = {}

    # Left team
    for i, entity in enumerate(entities[:half]):
        p: SoccerParticipantProtocol
        # Prefer fish-like adaptation if fish_id is present. This avoids runtime-checkable
        # Protocol + Mock traps where mocks accidentally satisfy SoccerParticipantProtocol.
        if hasattr(entity, "fish_id") and not isinstance(entity, SoccerParticipant):
            # It's a Fish-like entity (Fish, BotEntity, etc.)
            # fish_to_participant handles entities with or without genome
            p = fish_to_participant(entity, "left", i + 1)
        # Check if already a participant (duck-typing via protocol)
        elif isinstance(entity, SoccerParticipantProtocol):
            # Already adapted - use directly
            p = entity
            if not isinstance(p.team, str):
                raise ValueError(
                    f"Pre-adapted participant {p.participant_id} must define team as 'left' or 'right'"
                )
            # Ensure team is set correctly for left team
            if p.team != "left":
                raise ValueError(
                    f"Pre-adapted participant {p.participant_id} has team={p.team}, expected 'left'"
                )
        else:
            raise TypeError(
                f"Entity {entity} is not a SoccerParticipantProtocol and does not have required 'fish_id' attribute. "
                "Cannot adapt to soccer participant."
            )

        participants.append(p)
        # The map is deliberately participant-only. Live source entities are
        # reconciled after full time through their stable identity.
        entity_map[p.participant_id] = p

    # Right team
    for i, entity in enumerate(entities[half:]):
        # Prefer fish-like adaptation if fish_id is present. This avoids runtime-checkable
        # Protocol + Mock traps where mocks accidentally satisfy SoccerParticipantProtocol.
        if hasattr(entity, "fish_id") and not isinstance(entity, SoccerParticipant):
            # It's a Fish-like entity (Fish, BotEntity, etc.)
            # fish_to_participant handles entities with or without genome
            p = fish_to_participant(entity, "right", i + 1)
        # Check if already a participant
        elif isinstance(entity, SoccerParticipantProtocol):
            # Already adapted - use directly
            p = entity
            if not isinstance(p.team, str):
                raise ValueError(
                    f"Pre-adapted participant {p.participant_id} must define team as 'left' or 'right'"
                )
            # Ensure team is set correctly for right team
            if p.team != "right":
                raise ValueError(
                    f"Pre-adapted participant {p.participant_id} has team={p.team}, expected 'right'"
                )
        else:
            raise TypeError(
                f"Entity {entity} is not a SoccerParticipantProtocol and does not have required 'fish_id' attribute. "
                "Cannot adapt to soccer participant."
            )

        participants.append(p)
        entity_map[p.participant_id] = p

    return participants, entity_map


def create_participants_from_fish(
    fish_list: list[Fish],
) -> tuple[list[SoccerParticipant], dict[str, Fish]]:
    """Create balanced teams of participants from a list of fish.

    DEPRECATED: Use create_participants() instead for entity-agnostic adaptation.

    Splits the fish list into two teams (left/right) and creates
    SoccerParticipant instances for each.

    Args:
        fish_list: List of Fish entities to convert

    Returns:
        Tuple of (participants list, player_id -> Fish mapping)
    """
    # Delegate to create_participants for consistency
    return create_participants(fish_list)  # type: ignore[return-value]
