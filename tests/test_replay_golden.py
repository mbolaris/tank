from pathlib import Path

from backend.replay import replay_file


def test_golden_replay_replays_deterministically() -> None:
    fixture = Path(__file__).parent / "fixtures" / "replays" / "tank_petri_seed42_v1.jsonl"
    assert fixture.exists(), f"Missing fixture: {fixture}"
    replay_file(fixture)
