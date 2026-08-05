"""The 11v11 RCSS fixture is a contract shared with the frontend.

`frontend/src/components/__fixtures__/rcss_11v11_show.json` is consumed by
`SoccerArenaRcss.test.tsx` to prove an RCSS-shaped match state renders end to
end. A checked-in fixture that nothing regenerates rots silently, so this test
rebuilds it from `fake_server` and fails if the committed copy has drifted.

Regenerate with::

    python tests/test_rcss_fixture_contract.py
"""

from __future__ import annotations

import json
from pathlib import Path

from core.minigames.soccer.adapters import rcss_participants, rcss_show_to_canonical
from core.minigames.soccer.fake_server import FakeRCSSServer

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "frontend" / "src" / "components" / "__fixtures__" / "rcss_11v11_show.json"

TEAM_SIZE = 11
SEED = 42


def build_fixture() -> dict:
    server = FakeRCSSServer(seed=SEED, team_size=TEAM_SIZE)
    server.setup_teams()
    show = server.get_monitor_message()
    state = rcss_show_to_canonical(show)
    return {
        "generated_by": "tests/test_rcss_fixture_contract.py",
        "show_message": show,
        "canonical": {
            "coord_space": state["coord_space"],
            "play_mode": state["play_mode"],
            "ball": state["ball"],
            "players": state["players"],
        },
        "participants": rcss_participants(state),
    }


def _serialise(fixture: dict) -> str:
    return json.dumps(fixture, indent=2, sort_keys=True) + "\n"


def test_the_committed_fixture_matches_what_the_server_emits() -> None:
    assert FIXTURE.exists(), f"missing shared fixture: {FIXTURE}"
    assert FIXTURE.read_text(encoding="utf-8") == _serialise(build_fixture()), (
        "The RCSS fixture has drifted from fake_server's output. Regenerate it "
        "with `python tests/test_rcss_fixture_contract.py` and review the diff - "
        "the frontend renders this exact state."
    )


def test_the_fixture_is_a_full_11v11_with_distinct_participants() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    participants = fixture["participants"]
    assert len(participants) == TEAM_SIZE * 2
    assert len({p["participant_id"] for p in participants}) == TEAM_SIZE * 2
    # Uniform numbers are unique only within a side (§10.2).
    assert len({p["uniform_number"] for p in participants}) == TEAM_SIZE
    assert {p["avatar_kind"] for p in participants} == {"external"}


def test_the_fixture_is_in_canonical_space() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert fixture["canonical"]["coord_space"] == "canonical"


if __name__ == "__main__":  # pragma: no cover - regeneration entry point
    FIXTURE.write_text(_serialise(build_fixture()), encoding="utf-8")
    print(f"wrote {FIXTURE}")
