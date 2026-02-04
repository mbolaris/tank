"""Soccer participant protocol for entity-agnostic soccer matches.

This module defines a protocol for entities that can participate in soccer
matches, decoupling the match logic from specific entity types (Fish, Microbe).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

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
        source_entity: Optional reference to the original entity
    """

    participant_id: str
    team: str
    genome_ref: Any | None = None
    render_hint: dict | None = None
    source_entity: Any | None = field(default=None, repr=False)


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

    if genome_ref and hasattr(genome_ref, "physical"):
        try:
            from core.genetics.physical import PHYSICAL_TRAIT_SPECS

            render_hint = {
                spec.name: getattr(genome_ref.physical, spec.name).value
                for spec in PHYSICAL_TRAIT_SPECS
            }
        except Exception:
            pass

    return SoccerParticipant(
        participant_id=f"{team}_{player_index}",
        team=team,
        genome_ref=genome_ref,
        render_hint=render_hint,
        source_entity=fish,
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
        if hasattr(entity, "fish_id"):
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
        if isinstance(entity, SoccerParticipantProtocol):
            entity_map[p.participant_id] = getattr(p, "source_entity", None) or p
        else:
            entity_map[p.participant_id] = entity

    # Right team
    for i, entity in enumerate(entities[half:]):
        # Prefer fish-like adaptation if fish_id is present. This avoids runtime-checkable
        # Protocol + Mock traps where mocks accidentally satisfy SoccerParticipantProtocol.
        if hasattr(entity, "fish_id"):
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
        if isinstance(entity, SoccerParticipantProtocol):
            entity_map[p.participant_id] = getattr(p, "source_entity", None) or p
        else:
            entity_map[p.participant_id] = entity

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
