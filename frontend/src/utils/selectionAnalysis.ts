import type { MetricsHistory, MetricsSample } from '../types/simulation';

export interface SelectionAnalysisResult {
    /** Main display string for selection in the UI pill/readout */
    selectionText: string;
    /** Quantitative detail string (e.g., "+15% prediction" or "Uncertain (insufficient samples)") */
    detailText: string;
    /** Status tone for styling */
    tone: 'good' | 'neutral' | 'warning';
    /** Confidence label matching backend metrics_history.selection_quality */
    confidence: 'high' | 'high_confidence_selection' | 'high_confidence_no_selection' | 'bottleneck_confounded' | 'epoch_confounded' | 'insufficient_stable_samples';
    /** Name of the top drifting heritable trait, if any */
    topTrait?: string;
    /** Relative percentage change of top trait, if any */
    topDriftPct?: number;
    /** Number of stable samples used in assessment */
    stableSampleCount: number;
}

const TRAIT_LABELS: Record<string, string> = {
    pursuit_aggression: 'pursuit',
    prediction_skill: 'prediction',
    hunting_stamina: 'stamina',
    aggression: 'aggression',
    speed: 'speed',
    size: 'size',
};

const TRAIT_BOUNDS: Record<string, [number, number]> = {
    pursuit_aggression: [0.0, 1.0],
    prediction_skill: [0.0, 1.0],
    hunting_stamina: [0.0, 1.0],
    aggression: [0.0, 1.0],
    speed: [0.5, 3.0],
    size: [0.5, 3.0],
};

const POP_STABLE_MIN = 20.0;
const POP_CV_UNSTABLE = 0.35;
const MIN_SAMPLES_FOR_TREND = 3;
const TRAIT_DRIFT_SELECTION_PCT = 5.0;

function computeCV(values: number[]): number {
    if (values.length < 2) return 0;
    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    if (mean === 0) return 0;
    const variance = values.reduce((sq, v) => sq + Math.pow(v - mean, 2), 0) / values.length;
    return Math.sqrt(variance) / Math.abs(mean);
}

function isDirectionalTrend(series: number[], minConsistency: number = 0.45): boolean {
    if (series.length < 2) return false;
    const netDelta = Math.abs(series[series.length - 1] - series[0]);
    if (netDelta === 0) return false;
    let pathLength = 0;
    for (let i = 0; i < series.length - 1; i++) {
        pathLength += Math.abs(series[i + 1] - series[i]);
    }
    if (pathLength === 0) return false;
    return (netDelta / pathLength) >= minConsistency;
}

function filterStableSamples(samples: MetricsSample[]): MetricsSample[] {
    const pops = samples.map((s) => Number(s.population || 0));
    const window = 20;

    return samples.filter((s, i) => {
        const pop = Number(s.population || 0);
        if (pop < POP_STABLE_MIN) return false;

        const half = Math.floor(window / 2);
        const start = Math.max(0, i - half);
        const end = Math.min(pops.length, i + half + 1);
        const cv = computeCV(pops.slice(start, end));
        return cv < POP_CV_UNSTABLE;
    });
}

export function analyzeSelectionQuality(history: MetricsHistory | null): SelectionAnalysisResult {
    if (!history || !history.samples || history.samples.length < 2) {
        return {
            selectionText: 'Collecting history',
            detailText: 'Needs at least 2 samples',
            tone: 'neutral',
            confidence: 'insufficient_stable_samples',
            stableSampleCount: 0,
        };
    }

    // 1. Use backend pre-computed selection_quality if available
    const sq = history.selection_quality;
    if (sq) {
        const conf = (sq.confidence || 'high') as SelectionAnalysisResult['confidence'];
        const stableCount = sq.stable_sample_count ?? 0;

        const isHighConfidence = conf === 'high' || conf === 'high_confidence_selection' || conf === 'high_confidence_no_selection';
        if (!isHighConfidence) {
            return {
                selectionText: 'Uncertain',
                detailText: conf === 'bottleneck_confounded' ? 'Bottleneck confounded' : conf === 'epoch_confounded' ? 'Epoch confounded' : 'Low stable population',
                tone: 'warning',
                confidence: conf,
                stableSampleCount: stableCount,
            };
        }

        // Check conditioned drift for top trait (ranked by range-normalized drift)
        const condDrift = sq.conditioned_drift || {};
        const rnDrift = sq.range_normalized_drift || {};
        let topTraitKey: string | undefined;
        let topDriftPct: number | undefined;
        let maxNormDrift = -1;

        for (const [key, item] of Object.entries(condDrift)) {
            if (item.selection) {
                const bounds = TRAIT_BOUNDS[key] || [0, 1];
                const span = bounds[1] > bounds[0] ? bounds[1] - bounds[0] : 1;
                const norm = rnDrift[key] ?? (Math.abs(item.delta) / span);
                if (norm > maxNormDrift) {
                    maxNormDrift = norm;
                    topTraitKey = key;
                    topDriftPct = item.pct;
                }
            }
        }

        if (topTraitKey && topDriftPct !== undefined) {
            const label = TRAIT_LABELS[topTraitKey] || topTraitKey;
            const sign = topDriftPct >= 0 ? '+' : '';
            return {
                selectionText: `${sign}${topDriftPct.toFixed(0)}% ${label}`,
                detailText: `${sign}${topDriftPct.toFixed(1)}% ${topTraitKey}`,
                tone: 'good',
                confidence: 'high',
                topTrait: topTraitKey,
                topDriftPct,
                stableSampleCount: stableCount,
            };
        }

        return {
            selectionText: 'No drift',
            detailText: 'No directional drift >= 5%',
            tone: 'neutral',
            confidence: 'high',
            stableSampleCount: stableCount,
        };
    }

    // 2. Client-side fallback calculation matching tools/evolution_report_analyzer.py
    const samples = history.samples;
    const bootIds = new Set(samples.map((s) => s.boot_id).filter((id): id is number => typeof id === 'number'));
    const epochMixed = bootIds.size > 1;

    const stable = filterStableSamples(samples);
    const stableCount = stable.length;

    if (stableCount < MIN_SAMPLES_FOR_TREND) {
        return {
            selectionText: 'Uncertain',
            detailText: epochMixed ? 'Epoch confounded' : 'Low stable population',
            tone: 'warning',
            confidence: epochMixed ? 'epoch_confounded' : 'insufficient_stable_samples',
            stableSampleCount: stableCount,
        };
    }

    // Trait drift calculation on stable samples
    const samplesWithTraits = stable.filter((s) => s.traits && Object.keys(s.traits).length > 0);
    if (samplesWithTraits.length < 2) {
        return {
            selectionText: 'Uncertain',
            detailText: 'Insufficient trait samples',
            tone: 'warning',
            confidence: 'insufficient_stable_samples',
            stableSampleCount: stableCount,
        };
    }

    const first = samplesWithTraits[0].traits!;
    const last = samplesWithTraits[samplesWithTraits.length - 1].traits!;

    let topTraitKey: string | undefined;
    let topDriftPct: number | undefined;
    let maxNormDrift = -1;

    for (const key of Object.keys(first)) {
        if (key in last) {
            const series = samplesWithTraits.map((s) => s.traits![key]).filter((v): v is number => typeof v === 'number');
            const start = first[key];
            const end = last[key];
            if (start > 0) {
                const delta = end - start;
                const pct = (delta / start) * 100.0;
                const bounds = TRAIT_BOUNDS[key] || [0, 1];
                const span = bounds[1] > bounds[0] ? bounds[1] - bounds[0] : 1;
                const norm = Math.abs(delta) / span;
                const directional = series.length >= 3 ? isDirectionalTrend(series) : true;
                if (Math.abs(pct) >= TRAIT_DRIFT_SELECTION_PCT && directional && norm > maxNormDrift) {
                    maxNormDrift = norm;
                    topTraitKey = key;
                    topDriftPct = pct;
                }
            }
        }
    }

    if (epochMixed) {
        return {
            selectionText: 'Uncertain',
            detailText: 'Epoch confounded',
            tone: 'warning',
            confidence: 'epoch_confounded',
            stableSampleCount: stableCount,
        };
    }

    if (topTraitKey && topDriftPct !== undefined) {
        const label = TRAIT_LABELS[topTraitKey] || topTraitKey;
        const sign = topDriftPct >= 0 ? '+' : '';
        return {
            selectionText: `${sign}${topDriftPct.toFixed(0)}% ${label}`,
            detailText: `${sign}${topDriftPct.toFixed(1)}% ${topTraitKey}`,
            tone: 'good',
            confidence: 'high',
            topTrait: topTraitKey,
            topDriftPct,
            stableSampleCount: stableCount,
        };
    }

    return {
        selectionText: 'No drift',
        detailText: 'No directional drift >= 5%',
        tone: 'neutral',
        confidence: 'high',
        stableSampleCount: stableCount,
    };
}
