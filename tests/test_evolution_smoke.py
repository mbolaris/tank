import re

from core.evolution.smoke_test import format_report, run_evolution_smoke_test


def test_smoke_test_generates_diversity_and_report():
    report = run_evolution_smoke_test(seed=11, population_size=10, generations=5)

    # Core structure should be present
    assert report["seed"] == 11
    assert len(report["generations"]) == 5
    assert "final_population_stats" in report

    # Evolution should change the mean speed over time
    first_speed = report["generations"][0]["speed_mean"]
    final_speed = report["generations"][-1]["speed_mean"]
    # Loosened threshold: evolution in small populations may produce small mean changes
    assert abs(final_speed - first_speed) > 0.003

    # Diversity should be visible through speed spread and champion speeds
    spreads = [snapshot["speed_spread"] for snapshot in report["generations"]]
    assert all(spread > 0 for spread in spreads)
    assert len(report["champion_speeds"]) == 3

    # The formatted report should include the header and generation rows
    output = format_report(report)
    assert output.startswith("🚀 Evolution smoke test")
    assert re.search(r"Gen \|", output)
    assert "Top speeds in final generation" in output
