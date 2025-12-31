"""Domain event definitions for simulation telemetry.

These events represent significant occurrences in the simulation domain.
They are data-only (frozen dataclasses) and carry all context needed
for handlers to process them.

Design principles:
- Immutable: Events are facts that happened, don't mutate them
- Complete: Include all data handlers need (no callbacks to domain)
- Typed: Use strong types for type-safe dispatch and IDE support
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntityAteFoodEvent:
    """An entity consumed food.

    Attributes:
        entity_id: ID of the entity that ate
        food_type: Type of food consumed ("nectar", "live_food", "falling_food")
        energy_gained: Amount of energy gained
        algorithm_id: Behavior algorithm ID for tracking
        frame: Simulation frame when this occurred
    """

    entity_id: int
    food_type: str
    energy_gained: float
    algorithm_id: int
    frame: int


@dataclass(frozen=True)
class EnergyTransferredEvent:
    """Energy was transferred between entities or to/from environment.

    Attributes:
        src_id: Source entity ID (0 for environment/system)
        dst_id: Destination entity ID (0 for environment/system)
        amount: Absolute amount of energy transferred
        reason: Why the transfer occurred (e.g., "skill_game", "poker")
        frame: Simulation frame when this occurred
    """

    src_id: int
    dst_id: int
    amount: float
    reason: str
    frame: int


@dataclass(frozen=True)
class PokerHandResolvedEvent:
    """A poker hand completed.

    Attributes:
        participant_ids: Tuple of all participant entity IDs
        delta_by_participant: Energy change for each participant (ID -> delta)
        winner_id: ID of the winning participant
        winner_type: Type of winner ("fish" or "plant")
        house_cut: Energy taken by the house
        frame: Simulation frame when this occurred
    """

    participant_ids: tuple[int, ...]
    delta_by_participant: dict[int, float]
    winner_id: int
    winner_type: str
    house_cut: float
    frame: int


@dataclass(frozen=True)
class EntityDiedEvent:
    """An entity died.

    Attributes:
        entity_id: ID of the entity that died
        generation: Generation number of the entity
        age: Age of the entity at death
        reason: Cause of death ("starvation", "old_age", "predation", etc.)
        algorithm_id: Behavior algorithm ID (if applicable)
        remaining_energy: Energy at time of death
        frame: Simulation frame when this occurred
    """

    entity_id: int
    generation: int
    age: int
    reason: str
    algorithm_id: int | None
    remaining_energy: float
    frame: int


@dataclass(frozen=True)
class EntitySpawnedEvent:
    """An entity was spawned.

    Attributes:
        entity_id: ID of the new entity
        parent_id: ID of parent entity (None for soup spawn)
        kind: Entity type ("fish", "plant", "food")
        generation: Generation number
        algorithm_id: Behavior algorithm ID (if applicable)
        algorithm_name: Human-readable algorithm name
        energy: Initial energy
        is_soup_spawn: True if spawned from primordial soup (no parent)
        frame: Simulation frame when this occurred
    """

    entity_id: int
    parent_id: int | None
    kind: str
    generation: int
    algorithm_id: int | None
    algorithm_name: str | None
    energy: float
    is_soup_spawn: bool
    frame: int


@dataclass(frozen=True)
class ReproductionOccurredEvent:
    """Reproduction occurred.

    Attributes:
        parent_id: ID of the reproducing entity
        offspring_id: ID of the new offspring
        algorithm_id: Behavior algorithm ID
        is_asexual: True if asexual reproduction
        frame: Simulation frame when this occurred
    """

    parent_id: int
    offspring_id: int
    algorithm_id: int
    is_asexual: bool
    frame: int


@dataclass(frozen=True)
class EnergyBurnedEvent:
    """Energy was consumed/burned.

    Attributes:
        entity_id: ID of the entity burning energy
        source: Category of burn ("existence", "movement", "metabolism", etc.)
        amount: Amount of energy burned
        scope: "fish" or "plant"
        frame: Simulation frame when this occurred
    """

    entity_id: int
    source: str
    amount: float
    scope: str
    frame: int


@dataclass(frozen=True)
class EnergyGainedEvent:
    """Energy was gained from environment/food.

    Attributes:
        entity_id: ID of the entity gaining energy
        source: Category of gain ("nectar", "poker_fish", "auto_eval", etc.)
        amount: Amount of energy gained
        scope: "fish" or "plant"
        frame: Simulation frame when this occurred
    """

    entity_id: int
    source: str
    amount: float
    scope: str
    frame: int
