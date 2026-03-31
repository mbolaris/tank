from __future__ import annotations

import json
from pathlib import Path

from tools import demo


def test_run_demo_writes_bundle(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(demo, "_timestamp_slug", lambda: "20260331_120000")
    monkeypatch.setattr(demo, "_iso_now", lambda: "2026-03-31T12:00:00-07:00")
    monkeypatch.setattr(
        demo,
        "_git_metadata",
        lambda: {
            "commit": "abc123",
            "branch": "main",
            "is_dirty": False,
        },
    )
    monkeypatch.setattr(
        demo,
        "run_tank_simulation",
        lambda config, run_dir: {
            "total_population": 12,
            "max_generation": 4,
            "total_births": 20,
            "total_deaths": 8,
            "death_causes": {"starvation": 5, "predation": 2, "old_age": 1},
            "total_energy": 321.0,
        },
    )

    def fake_replay(config, run_dir: Path) -> Path:
        replay_path = run_dir / "tank.replay.jsonl"
        replay_path.write_text('{"type":"header"}\n', encoding="utf-8")
        return replay_path

    monkeypatch.setattr(demo, "record_tank_replay", fake_replay)
    monkeypatch.setattr(
        demo,
        "run_soccer_episode",
        lambda config, run_dir: {
            "winner": "left",
            "score_left": 2,
            "score_right": 1,
            "average_fitness": 13.5,
            "best_agent": {"player_id": "left_1", "fitness": 30.0},
        },
    )
    monkeypatch.setattr(
        demo,
        "run_benchmark",
        lambda config, run_dir: {
            "benchmark_id": "soccer/training_3k",
            "score": 9.25,
            "runtime_seconds": 1.2,
            "metadata": {"frames": 3000, "team_size": 3, "n_seeds": 5},
        },
    )

    config = demo.DemoConfig(
        seed=42,
        output_root=tmp_path,
        tank_frames=100,
        tank_stats_interval=25,
        replay_frames=30,
        replay_every=5,
        soccer_frames=60,
        soccer_team_size=3,
        benchmark_path=demo.ROOT / "benchmarks" / "soccer" / "training_3k.py",
    )

    run_dir = demo.run_demo(config)

    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["seed"] == 42
    assert manifest["git"]["commit"] == "abc123"
    assert manifest["scores"]["tank"]["population"] == 12
    assert manifest["scores"]["soccer_episode"]["winner"] == "left"
    assert manifest["scores"]["benchmark"]["benchmark_id"] == "soccer/training_3k"

    summary = (run_dir / "summary.md").read_text(encoding="utf-8")
    assert "Tank World Demo" in summary
    assert "soccer/training_3k" in summary
    assert "tank.replay.jsonl" in summary
    assert (run_dir / "demo.log").exists()
    assert (run_dir / "tank.replay.jsonl").exists()


def test_render_summary_includes_key_metrics(tmp_path: Path) -> None:
    config = demo.DemoConfig(
        seed=42,
        output_root=tmp_path,
        tank_frames=1500,
        tank_stats_interval=500,
        replay_frames=300,
        replay_every=10,
        soccer_frames=600,
        soccer_team_size=3,
        benchmark_path=demo.ROOT / "benchmarks" / "soccer" / "training_3k.py",
    )

    summary = demo.render_summary(
        run_dir=tmp_path / "demo_20260331_120000",
        created_at="2026-03-31T12:00:00-07:00",
        config=config,
        git_info={"commit": "abc123", "branch": "main", "is_dirty": True},
        tank_stats={
            "total_population": 14,
            "max_generation": 6,
            "total_births": 30,
            "total_deaths": 18,
            "death_causes": {"starvation": 9, "predation": 6, "old_age": 3},
            "total_energy": 999.0,
        },
        soccer_episode={
            "winner": "right",
            "score_left": 0,
            "score_right": 3,
            "average_fitness": 7.125,
            "best_agent": {"player_id": "right_2", "fitness": 15.0},
        },
        benchmark_result={
            "benchmark_id": "soccer/training_3k",
            "score": 12.75,
            "runtime_seconds": 4.2,
            "metadata": {"frames": 3000, "team_size": 3, "n_seeds": 5},
        },
    )

    assert "Tank population: `14`" in summary
    assert "Soccer scoreline: `0-3` winner `right`" in summary
    assert "Benchmark `soccer/training_3k` score: `12.750000`" in summary
