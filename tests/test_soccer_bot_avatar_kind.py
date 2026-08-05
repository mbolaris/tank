"""Bots must not be announced to the arena as tank fish.

`BotEntity` carries a `fish_id` so it can flow through the same match plumbing
as a real fish, which sends it down `fish_to_participant`. That id is
`abs(hash(bot_id))` - stable for the match, but a synthetic 19-digit number
with no aquarium behind it. Presenting it as a fish let the live arena label a
bot "Fish #4882397523792860000" and gave it a genome avatar it does not have.
"""

from __future__ import annotations

from core.minigames.soccer.league_runtime import BotEntity
from core.minigames.soccer.participant import create_participants, fish_to_participant


class _TankFish:
    """The minimum a real fish needs to reach the participant adapter."""

    def __init__(self, fish_id: int) -> None:
        self.fish_id = fish_id
        self.genome = None
        self.tank_id = "tank-a"
        self.generation = 12
        self.parent_id = 4


def test_a_bot_declares_itself_a_bot() -> None:
    participant = fish_to_participant(BotEntity("Bot:Balanced#1", "Bot:Balanced"), "left", 1)
    assert participant.avatar_kind == "bot"


def test_a_tank_fish_is_still_a_fish() -> None:
    participant = fish_to_participant(_TankFish(4242), "left", 1)
    assert participant.avatar_kind == "fish"
    assert participant.fish_id == 4242


def test_the_kind_survives_onto_the_wire() -> None:
    payload = fish_to_participant(BotEntity("Bot:Balanced#1", "Bot:Balanced"), "right", 3).to_dict()
    assert payload["avatar_kind"] == "bot"


def test_a_mixed_match_keeps_the_two_kinds_apart() -> None:
    entities = [
        _TankFish(1),
        _TankFish(2),
        BotEntity("Bot:Balanced#1", "Bot:Balanced"),
        BotEntity("Bot:Balanced#2", "Bot:Balanced"),
    ]
    participants, _ = create_participants(entities)
    kinds = {p.participant_id: p.avatar_kind for p in participants}  # type: ignore[attr-defined]
    assert kinds == {"left_1": "fish", "left_2": "fish", "right_1": "bot", "right_2": "bot"}


def test_a_bot_carries_no_aquarium_lineage() -> None:
    # It has no tank and no parent, so those fields stay off the wire rather
    # than being filled with placeholders.
    payload = fish_to_participant(BotEntity("Bot:Balanced#1", "Bot:Balanced"), "left", 1).to_dict()
    assert "tank_id" not in payload
    assert "generation" not in payload
    assert "parent_id" not in payload
