from backend.replay import ReplayPlan, record_file, replay_file


def test_replay_record_then_replay_roundtrip(tmp_path) -> None:
    path = tmp_path / "roundtrip.replay.jsonl"
    record_file(
        path,
        seed=42,
        initial_mode="tank",
        steps=6,
        record_every=3,
        plan=ReplayPlan({2: "petri", 4: "tank"}),
    )
    replay_file(path)
