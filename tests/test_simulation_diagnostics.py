import json
from types import SimpleNamespace

from core.simulation import diagnostics


class _FakeEngine:
    frame_count = 300
    ecosystem = SimpleNamespace(max_population=120)

    def get_stats(self) -> dict:
        return {
            "frame_count": 300,
            "total_population": 42,
            "fish_count": 20,
            "food_count": 15,
            "plant_count": 7,
            "total_births": 11,
            "total_deaths": 3,
            "reproduction_stats": {
                "total_mating_attempts": 12,
                "success_rate_pct": "91.7%",
            },
            "death_causes": {
                "starvation": 2,
                "old_age": 1,
            },
        }


def test_format_simulation_stats_uses_engine_stats(monkeypatch) -> None:
    monkeypatch.setattr(diagnostics.time, "time", lambda: 110.0)

    lines = diagnostics.format_simulation_stats(_FakeEngine(), start_time=100.0)

    assert "Frame: 300 | Time: 10.0s" in lines
    assert "FPS: 30.0" in lines
    assert "Population:      42/120" in lines
    assert "Fish/Food/Plant: 20 / 15 / 7" in lines
    assert "Births (Total):  11" in lines
    assert "Mating Attempts: 12" in lines
    assert "Success Rate:    91.7%" in lines
    assert "Deaths (3): starvation: 2, old_age: 1" in lines


def test_print_simulation_stats_uses_injected_emitter(monkeypatch) -> None:
    monkeypatch.setattr(diagnostics.time, "time", lambda: 110.0)
    emitted: list[str] = []

    diagnostics.print_simulation_stats(_FakeEngine(), start_time=100.0, emit=emitted.append)

    assert emitted == diagnostics.format_simulation_stats(_FakeEngine(), start_time=100.0)


def test_export_stats_json_writes_elapsed_time(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(diagnostics.time, "time", lambda: 110.0)
    output_path = tmp_path / "stats.json"

    diagnostics.export_stats_json(_FakeEngine(), str(output_path), start_time=100.0)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["frame_count"] == 300
    assert payload["elapsed_time"] == 10.0


def test_export_stats_json_logs_serialization_failures(tmp_path, monkeypatch, caplog) -> None:
    class _BadStatsEngine(_FakeEngine):
        def get_stats(self) -> dict:
            stats = super().get_stats()
            stats["not_json"] = object()
            return stats

    monkeypatch.setattr(diagnostics.time, "time", lambda: 110.0)

    diagnostics.export_stats_json(_BadStatsEngine(), str(tmp_path / "bad.json"), start_time=100.0)

    assert "Failed to export stats" in caplog.text
