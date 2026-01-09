"""Soccer participant protocol for entity-agnostic soccer matches.

This module defines a protocol for entities that can participate in soccer
matches, decoupling the match logic from specific entity types (Fish, Microbe).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional, Protocol, runtime_checkable

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
    def genome_ref(self) -> Optional[Any]:
        """Reference to genome for policy lookup."""
        ...

    @property
    def render_hint(self) -> Optional[dict]:
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
    genome_ref: Optional[Any] = None
    render_hint: Optional[dict] = None
    source_entity: Optional[Any] = field(default=None, repr=False)


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
    render_hint: Optional[dict] = None
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


def create_participants_from_fish(
    fish_list: list[Fish],
) -> tuple[list[SoccerParticipant], dict[str, Fish]]:
    """Create balanced teams of participants from a list of fish.

    Splits the fish list into two teams (left/right) and creates
    SoccerParticipant instances for each.

    Args:
        fish_list: List of Fish entities to convert

    Returns:
        Tuple of (participants list, player_id -> Fish mapping)
    """
    # Ensure even number of players
    if len(fish_list) % 2 != 0:
        fish_list = fish_list[:-1]

    half = len(fish_list) // 2
    participants: list[SoccerParticipant] = []
    fish_map: dict[str, Fish] = {}

    # Left team
    for i, fish in enumerate(fish_list[:half]):
        p = fish_to_participant(fish, "left", i + 1)
        participants.append(p)
        fish_map[p.participant_id] = fish

    # Right team
    for i, fish in enumerate(fish_list[half:]):
        p = fish_to_participant(fish, "right", i + 1)
        participants.append(p)
        fish_map[p.participant_id] = fish

    return participants, fish_map
