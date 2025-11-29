from __future__ import annotations

from core.ecosystem_stats import AlgorithmStats


def _get_report_header(ecosystem) -> list[str]:
    return [
        "=" * 80,
        "ALGORITHM PERFORMANCE REPORT",
        "=" * 80,
        "",
        f"Total Simulation Time: {ecosystem.frame_count} frames",
        f"Total Population Births: {ecosystem.total_births}",
        f"Total Population Deaths: {ecosystem.total_deaths}",
        f"Current Generation: {ecosystem.current_generation}",
        "",
    ]


def _get_top_performers_section(
    algorithms_with_data: list[tuple[int, AlgorithmStats]]
) -> list[str]:
    algorithms_sorted = sorted(
        algorithms_with_data, key=lambda item: item[1].get_reproduction_rate(), reverse=True
    )

    lines = ["-" * 80, "TOP PERFORMING ALGORITHMS (by reproduction rate)", "-" * 80, ""]

    for i, (algo_id, stats) in enumerate(algorithms_sorted[:10], 1):
        lines.extend(
            [
                f"#{i} - {stats.algorithm_name} (ID: {algo_id})",
                f"  Births: {stats.total_births}",
                f"  Deaths: {stats.total_deaths}",
                f"  Current Population: {stats.current_population}",
                f"  Reproductions: {stats.total_reproductions}",
                f"  Reproduction Rate: {stats.get_reproduction_rate():.2%}",
                f"  Survival Rate: {stats.get_survival_rate():.2%}",
                f"  Avg Lifespan: {stats.get_avg_lifespan():.1f} frames",
                f"  Food Eaten: {stats.total_food_eaten}",
                f"  Deaths - Starvation: {stats.deaths_starvation}, "
                f"Old Age: {stats.deaths_old_age}, Predation: {stats.deaths_predation}",
                "",
            ]
        )

    return lines


def _get_survival_section(
    algorithms_with_data: list[tuple[int, AlgorithmStats]]
) -> list[str]:
    algorithms_sorted = sorted(
        algorithms_with_data, key=lambda item: item[1].get_survival_rate(), reverse=True
    )

    lines = ["-" * 80, "TOP SURVIVING ALGORITHMS (by current survival rate)", "-" * 80, ""]

    for i, (algo_id, stats) in enumerate(algorithms_sorted[:10], 1):
        lines.extend(
            [
                f"#{i} - {stats.algorithm_name} (ID: {algo_id})",
                f"  Survival Rate: {stats.get_survival_rate():.2%}",
                f"  Current Population: {stats.current_population}",
                f"  Avg Lifespan: {stats.get_avg_lifespan():.1f} frames",
                "",
            ]
        )

    return lines


def _get_longevity_section(
    algorithms_with_data: list[tuple[int, AlgorithmStats]]
) -> list[str]:
    algorithms_sorted = sorted(
        algorithms_with_data, key=lambda item: item[1].get_avg_lifespan(), reverse=True
    )

    lines = ["-" * 80, "LONGEST-LIVED ALGORITHMS (by average lifespan)", "-" * 80, ""]

    for i, (algo_id, stats) in enumerate(algorithms_sorted[:10], 1):
        starvation_pct = (
            stats.deaths_starvation / stats.total_deaths * 100 if stats.total_deaths > 0 else 0
        )
        lines.extend(
            [
                f"#{i} - {stats.algorithm_name} (ID: {algo_id})",
                f"  Avg Lifespan: {stats.get_avg_lifespan():.1f} frames",
                f"  Deaths: {stats.total_deaths}",
                f"  Starvation Deaths: {stats.deaths_starvation} ({starvation_pct:.1f}%)",
                "",
            ]
        )

    return lines


def _get_worst_performers_section(
    algorithm_stats: dict[int, AlgorithmStats], min_sample_size: int
) -> list[str]:
    algorithms_with_deaths = [
        (algo_id, stats)
        for algo_id, stats in algorithm_stats.items()
        if stats.total_deaths >= min_sample_size
    ]
    algorithms_with_deaths.sort(
        key=lambda item: (
            item[1].deaths_starvation / item[1].total_deaths if item[1].total_deaths > 0 else 0
        ),
        reverse=True,
    )

    lines = ["-" * 80, "WORST PERFORMERS (highest starvation rate)", "-" * 80, ""]

    for i, (algo_id, stats) in enumerate(algorithms_with_deaths[:10], 1):
        starvation_rate = stats.deaths_starvation / stats.total_deaths if stats.total_deaths > 0 else 0
        lines.extend(
            [
                f"#{i} - {stats.algorithm_name} (ID: {algo_id})",
                f"  Starvation Rate: {starvation_rate:.2%}",
                f"  Deaths: {stats.total_deaths}",
                f"  Avg Lifespan: {stats.get_avg_lifespan():.1f} frames",
                f"  Reproduction Rate: {stats.get_reproduction_rate():.2%}",
                "",
            ]
        )

    return lines


def _get_recommendations_section(
    algorithm_stats: dict[int, AlgorithmStats], algorithms_with_data: list[tuple[int, AlgorithmStats]]
) -> list[str]:
    lines = ["-" * 80, "RECOMMENDATIONS FOR NEXT GENERATION", "-" * 80, ""]

    if algorithms_with_data:
        best_algo_id, best_stats = algorithms_with_data[0]
        lines.extend(
            [
                f"1. The most successful algorithm is '{best_stats.algorithm_name}'",
                f"   with a reproduction rate of {best_stats.get_reproduction_rate():.2%}.",
                "",
            ]
        )

    algorithms_by_starvation = sorted(
        [(algo_id, stats) for algo_id, stats in algorithm_stats.items() if stats.total_deaths > 0],
        key=lambda item: (
            item[1].deaths_starvation / item[1].total_deaths if item[1].total_deaths > 0 else 0
        ),
        reverse=True,
    )

    if algorithms_by_starvation:
        worst_algo_id, worst_stats = algorithms_by_starvation[0]
        starvation_rate = (
            worst_stats.deaths_starvation / worst_stats.total_deaths
            if worst_stats.total_deaths > 0
            else 0
        )
        lines.extend(
            [
                f"2. The algorithm '{worst_stats.algorithm_name}' has the highest starvation rate",
                f"   at {starvation_rate:.2%}, indicating poor food-seeking behavior.",
                "",
            ]
        )

    total_starvation = sum(stats.deaths_starvation for stats in algorithm_stats.values())
    total_deaths_all = sum(stats.total_deaths for stats in algorithm_stats.values())
    if total_deaths_all > 0:
        overall_starvation_rate = total_starvation / total_deaths_all
        lines.append(f"3. Overall starvation rate: {overall_starvation_rate:.2%}")
        if overall_starvation_rate > 0.5:
            lines.extend(
                [
                    "   RECOMMENDATION: High starvation indicates resource scarcity.",
                    "   Focus on food-seeking and energy conservation algorithms.",
                ]
            )
        lines.append("")

    return lines


def get_algorithm_performance_report(ecosystem, min_sample_size: int = 5) -> str:
    algorithms_with_data = [
        (algo_id, stats)
        for algo_id, stats in ecosystem.algorithm_stats.items()
        if stats.total_births >= min_sample_size
    ]

    algorithms_with_data.sort(key=lambda item: item[1].get_reproduction_rate(), reverse=True)

    report_lines: list[str] = []
    report_lines.extend(_get_report_header(ecosystem))
    report_lines.extend(_get_top_performers_section(algorithms_with_data))
    report_lines.extend(_get_survival_section(algorithms_with_data))
    report_lines.extend(_get_longevity_section(algorithms_with_data))
    report_lines.extend(_get_worst_performers_section(ecosystem.algorithm_stats, min_sample_size))
    report_lines.extend(
        _get_recommendations_section(ecosystem.algorithm_stats, algorithms_with_data)
    )
    report_lines.append("=" * 80)

    return "\n".join(report_lines)
