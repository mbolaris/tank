"""Deeply isolated, deterministic soccer roster snapshots.

Snapshots are the boundary between the aquarium and a match.  They contain
only immutable values.  A detached execution participant/genome may be
reconstructed from one, but the snapshot never owns a Fish, policy callable,
world object, or mutable policy dictionary.
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

from core.minigames.soccer.participant import SoccerParticipant


FrozenValue = None | bool | int | float | str | tuple["FrozenValue", ...]


def _freeze(value: Any) -> FrozenValue:
    """Convert JSON-like values to recursively immutable values."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if callable(value):
        raise TypeError("soccer roster snapshots cannot contain callables")
    if isinstance(value, Mapping):
        return tuple(
            (str(key), _freeze(item))
            for key, item in sorted(value.items(), key=lambda kv: str(kv[0]))
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    # Genome serialization and policy params are JSON value objects.  Reject
    # arbitrary objects rather than accidentally retaining a live reference.
    raise TypeError(f"unsupported mutable snapshot value: {type(value).__name__}")


def _thaw(value: FrozenValue) -> Any:
    if isinstance(value, tuple):
        tuple_value = cast(tuple[Any, ...], value)
        if all(
            isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str)
            for item in tuple_value
        ):
            return {str(item[0]): _thaw(cast(FrozenValue, item[1])) for item in tuple_value}
        return [_thaw(cast(FrozenValue, item)) for item in tuple_value]
    return value


@dataclass(frozen=True)
class SoccerParticipantSnapshot:
    """Immutable serialized identity and policy state for one player."""

    participant_id: str
    side: str
    team_id: str
    uniform_number: int
    avatar_kind: str
    fish_id: int | None = None
    tank_id: str | None = None
    generation: int | None = None
    parent_id: int | None = None
    policy_label: str | None = None
    policy_id: str | None = None
    policy_params: FrozenValue = None
    genome_data: FrozenValue = None
    render_hint: FrozenValue = None
    repro_credit_capable: bool = False
    energy: float | None = None
    max_energy: float | None = None
    display_name: str | None = None

    @classmethod
    def from_participant(cls, participant: SoccerParticipant) -> SoccerParticipantSnapshot:
        genome = participant.genome_ref
        policy_id = None
        policy_params: Any = None
        genome_data: Any = None
        if genome is not None:
            to_dict = getattr(genome, "to_dict", None)
            if callable(to_dict):
                candidate = to_dict()
                if isinstance(candidate, Mapping):
                    genome_data = dict(candidate)
            behavioral = getattr(genome, "behavioral", None)
            policy_trait = getattr(behavioral, "soccer_policy_id", None)
            params_trait = getattr(behavioral, "soccer_policy_params", None)
            candidate_policy_id = getattr(policy_trait, "value", None)
            policy_id = (
                candidate_policy_id
                if isinstance(candidate_policy_id, (str, int, float, bool))
                else None
            )
            candidate_params = getattr(params_trait, "value", None)
            policy_params = (
                dict(candidate_params) if isinstance(candidate_params, Mapping) else None
            )

        return cls(
            participant_id=str(participant.participant_id),
            side=str(participant.team),
            team_id=str(participant.team_id or participant.team),
            uniform_number=int(participant.uniform_number or 0),
            avatar_kind=str(participant.avatar_kind),
            fish_id=participant.fish_id,
            tank_id=participant.tank_id,
            generation=participant.generation,
            parent_id=participant.parent_id,
            policy_label=participant.policy_label,
            policy_id=str(policy_id) if policy_id is not None else None,
            policy_params=_freeze(policy_params),
            genome_data=_freeze(genome_data),
            render_hint=_freeze(participant.render_hint),
            repro_credit_capable=bool(participant.repro_credit_capable),
            energy=participant.energy,
            max_energy=participant.max_energy,
            display_name=participant.display_name,
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "participant_id": self.participant_id,
            "side": self.side,
            "team_id": self.team_id,
            "uniform_number": self.uniform_number,
            "avatar_kind": self.avatar_kind,
            "repro_credit_capable": self.repro_credit_capable,
        }
        for key in (
            "fish_id",
            "tank_id",
            "generation",
            "parent_id",
            "policy_label",
            "policy_id",
            "display_name",
        ):
            value = getattr(self, key)
            if value is not None:
                data[key] = value
        if self.policy_params is not None:
            data["policy_params"] = _thaw(self.policy_params)
        if self.genome_data is not None:
            data["genome_data"] = _thaw(self.genome_data)
        if self.render_hint is not None:
            data["render_hint"] = _thaw(self.render_hint)
        return data

    def to_wire_dict(self) -> dict[str, Any]:
        """Return only the public §10.1 participant identity contract."""
        data: dict[str, Any] = {
            "participant_id": self.participant_id,
            "side": self.side,
            "team_id": self.team_id,
            "uniform_number": self.uniform_number,
            "avatar_kind": self.avatar_kind,
        }
        for key in (
            "fish_id",
            "tank_id",
            "generation",
            "parent_id",
            "policy_label",
            "display_name",
        ):
            value = getattr(self, key)
            if value is not None:
                data[key] = value
        return data

    def detached_participant(self) -> SoccerParticipant:
        """Reconstruct a participant detached from aquarium state."""
        genome = None
        if self.genome_data is not None:
            from core.genetics import Genome

            genome = Genome.from_dict(
                _thaw(self.genome_data), rng=random.Random(0), use_algorithm=True
            )
        return SoccerParticipant(
            participant_id=self.participant_id,
            team=self.side,
            genome_ref=genome,
            render_hint=_thaw(self.render_hint),
            team_id=self.team_id,
            uniform_number=self.uniform_number,
            avatar_kind=self.avatar_kind,
            fish_id=self.fish_id,
            tank_id=self.tank_id,
            generation=self.generation,
            parent_id=self.parent_id,
            policy_label=self.policy_label,
            repro_credit_capable=self.repro_credit_capable,
            energy=self.energy,
            max_energy=self.max_energy,
            display_name=self.display_name,
        )


@dataclass(frozen=True)
class SoccerRosterSnapshot:
    """Ordered immutable roster snapshot."""

    participants: tuple[SoccerParticipantSnapshot, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"participants": [participant.to_dict() for participant in self.participants]}

    def detached_participants(self) -> list[SoccerParticipant]:
        return [participant.detached_participant() for participant in self.participants]


def snapshot_roster(participants: Sequence[SoccerParticipant | Any]) -> SoccerRosterSnapshot:
    """Snapshot an already ordered roster without consuming RNG."""
    if participants and not all(isinstance(item, SoccerParticipant) for item in participants):
        from core.minigames.soccer.participant import create_participants

        participants, _ = create_participants(list(participants))
    return SoccerRosterSnapshot(
        tuple(SoccerParticipantSnapshot.from_participant(p) for p in participants)
    )


def snapshot_participant(participant: SoccerParticipant) -> SoccerParticipantSnapshot:
    return SoccerParticipantSnapshot.from_participant(participant)


# Explicit names used by callers and by the contract tests.
build_roster_snapshot = snapshot_roster
RosterSnapshot = SoccerRosterSnapshot
