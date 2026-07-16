import type { MetricsSample } from '../../types/simulation';

export function recentDeathStats(start: MetricsSample, end: MetricsSample): {
    starvationDeaths: number;
    totalDeaths: number;
} {
    const total = (sample: MetricsSample) => Object.values(sample.death_causes ?? {}).reduce((sum, value) => sum + value, 0);
    return {
        starvationDeaths: Math.max(0, (end.death_causes?.starvation ?? 0) - (start.death_causes?.starvation ?? 0)),
        totalDeaths: Math.max(0, total(end) - total(start)),
    };
}
