import type { MetricsHistory, MetricsSample } from '../../types/simulation';

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

export type XAxisMode = 'frames' | 'generations';

// Healthy-ecosystem thresholds (mirrors CLAUDE.md "Healthy Ecosystem Indicators").
export const STABLE_POPULATION = 20; // >20 fish = stable
export const HEALTHY_GEN_RATE = 5; // >5 generations per 10k frames
export const WARNING_GEN_RATE = 3; // <3 = evolution too slow
export const HEALTHY_REPRO_RATIO = 1.2; // births/deaths >120% = growing

// Heritable traits tracked for directional-selection (drift) visualization.
// Order/colors are stable; only keys actually present in the data are drawn.
// Palette validated for the dark surface (#0f172a): CVD-safe adjacent
// separation, 3:1 contrast, dark lightness band.
export const TRAIT_SERIES: { key: string; label: string; color: string }[] = [
    { key: 'pursuit_aggression', label: 'Pursuit', color: '#d97706' },
    { key: 'prediction_skill', label: 'Prediction', color: '#8b5cf6' },
    { key: 'hunting_stamina', label: 'Stamina', color: '#059669' },
    { key: 'aggression', label: 'Aggression', color: '#ef4444' },
    { key: 'speed', label: 'Speed', color: '#3b82f6' },
    { key: 'size', label: 'Size', color: '#ec4899' },
];

export interface AggregatedPoint {
    frame?: number;
    max_generation: number;
    population: number;
    fish_energy: number;
    births_total: number;
    deaths_total: number;
    poker: { auto_eval_elo: number };
    soccer: { goals_per_1k_frames: number };
    diversity_score: number;
    traits?: Record<string, number>;
    death_causes?: Record<string, number>;
}

export interface TrendPoint extends AggregatedPoint {
    births_interval: number;
    deaths_neg: number;
    mean_energy: number;
    // Trait means indexed to their first recorded value, as % change.
    traits_idx?: Record<string, number>;
    death_causes_interval?: Record<string, number>;
}

// Helper to calculate trend delta and percentage change between first and last quartiles
export function calculateTrend(values: number[]): { delta: number; pct: number } {
    if (values.length < 2) return { delta: 0, pct: 0 };
    const len = values.length;
    const qSize = Math.max(1, Math.floor(len / 4));

    const firstQuartile = values.slice(0, qSize);
    const lastQuartile = values.slice(len - qSize);

    const meanFirst = firstQuartile.reduce((a, b) => a + b, 0) / qSize;
    const meanLast = lastQuartile.reduce((a, b) => a + b, 0) / qSize;

    const delta = meanLast - meanFirst;
    const pct = meanFirst !== 0 ? (delta / Math.abs(meanFirst)) * 100 : 0;

    return { delta, pct };
}

/**
 * Aggregate raw samples into per-generation means (when xAxisMode is
 * 'generations') or pass them through frame-ordered (when 'frames'), then
 * derive interval deltas, per-fish energy, and trait drift indexed to the
 * first recorded value.
 */
export function buildTrendPoints(samples: MetricsSample[], xAxisMode: XAxisMode): TrendPoint[] {
    if (samples.length === 0) return [];

    let data: (MetricsSample | AggregatedPoint)[] = samples;
    if (xAxisMode === 'generations') {
        const genMap: Record<number, {
            count: number;
            populationSum: number;
            eloSum: number;
            goalsSum: number;
            fishEnergySum: number;
            birthsSum: number;
            deathsSum: number;
            diversitySum: number;
            traitsSum: Record<string, number>;
            traitsCount: Record<string, number>;
            deathCausesSum: Record<string, number>;
        }> = {};

        samples.forEach(s => {
            const gen = s.max_generation;
            if (!genMap[gen]) {
                genMap[gen] = {
                    count: 0,
                    populationSum: 0,
                    eloSum: 0,
                    goalsSum: 0,
                    fishEnergySum: 0,
                    birthsSum: 0,
                    deathsSum: 0,
                    diversitySum: 0,
                    traitsSum: {},
                    traitsCount: {},
                    deathCausesSum: {},
                };
            }
            const g = genMap[gen];
            g.count++;
            g.populationSum += s.population;
            g.eloSum += s.poker?.auto_eval_elo ?? 0;
            g.goalsSum += s.soccer?.goals_per_1k_frames ?? 0;
            g.fishEnergySum += s.fish_energy;
            g.birthsSum += s.births_total;
            g.deathsSum += s.deaths_total;
            g.diversitySum += s.diversity_score ?? 0;
            if (s.traits) {
                for (const [k, v] of Object.entries(s.traits)) {
                    g.traitsSum[k] = (g.traitsSum[k] ?? 0) + v;
                    g.traitsCount[k] = (g.traitsCount[k] ?? 0) + 1;
                }
            }
            if (s.death_causes) {
                for (const [k, v] of Object.entries(s.death_causes)) {
                    g.deathCausesSum[k] = (g.deathCausesSum[k] ?? 0) + v;
                }
            }
        });

        data = Object.keys(genMap)
            .map(Number)
            .sort((a, b) => a - b)
            .map(gen => {
                const g = genMap[gen];
                return {
                    max_generation: gen,
                    population: Number((g.populationSum / g.count).toFixed(2)),
                    poker: { auto_eval_elo: Number((g.eloSum / g.count).toFixed(2)) },
                    soccer: { goals_per_1k_frames: Number((g.goalsSum / g.count).toFixed(4)) },
                    fish_energy: Number((g.fishEnergySum / g.count).toFixed(2)),
                    births_total: Number((g.birthsSum / g.count).toFixed(2)),
                    deaths_total: Number((g.deathsSum / g.count).toFixed(2)),
                    diversity_score: Number((g.diversitySum / g.count).toFixed(4)),
                    traits: Object.fromEntries(
                        Object.keys(g.traitsSum).map(k => [
                            k,
                            Number((g.traitsSum[k] / g.traitsCount[k]).toFixed(5)),
                        ])
                    ),
                    death_causes: Object.fromEntries(
                        Object.keys(g.deathCausesSum).map(k => [
                            k,
                            Number((g.deathCausesSum[k] / g.count).toFixed(2)),
                        ])
                    ),
                };
            });
    }

    // Baseline for trait indexing: first non-zero value seen per trait, so
    // drift reads as "% change since start" on one comparable axis.
    const traitBaselines: Record<string, number> = {};
    data.forEach(d => {
        if (!d.traits) return;
        for (const [k, v] of Object.entries(d.traits)) {
            if (traitBaselines[k] === undefined && v !== 0) traitBaselines[k] = v;
        }
    });

    // Interval deltas (births/deaths per sample or per generation) and per-fish energy
    return data.map((d, idx) => {
        const prev = data[idx - 1];
        const birthsInterval = prev ? Math.max(0, d.births_total - prev.births_total) : 0;
        const deathsInterval = prev ? Math.max(0, d.deaths_total - prev.deaths_total) : 0;

        let traitsIdx: Record<string, number> | undefined;
        if (d.traits) {
            traitsIdx = {};
            for (const [k, v] of Object.entries(d.traits)) {
                const base = traitBaselines[k];
                if (base) traitsIdx[k] = Number((((v - base) / base) * 100).toFixed(2));
            }
        }

        const causesInterval: Record<string, number> = {};
        const keys = ['starvation', 'old_age', 'predation', 'migration', 'unknown'];
        keys.forEach(k => {
            const curVal = d.death_causes?.[k] ?? 0;
            const prevVal = prev?.death_causes?.[k] ?? 0;
            causesInterval[k] = Math.max(0, curVal - prevVal);
        });

        return {
            ...d,
            births_interval: birthsInterval,
            deaths_neg: -deathsInterval,
            mean_energy: d.population > 0 ? Number((d.fish_energy / d.population).toFixed(1)) : 0,
            traits_idx: traitsIdx,
            death_causes_interval: causesInterval,
        };
    });
}

/** Next frame at which the trend history will receive its first sample. */
export function nextSampleFrame(history: MetricsHistory | null): number {
    return history?.sample_interval_frames || 500;
}
