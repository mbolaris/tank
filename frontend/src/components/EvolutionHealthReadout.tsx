import { useState } from 'react';
import type { MetricsHistory } from '../types/simulation';
import styles from './EvolutionHealthReadout.module.css';

interface EvolutionHealthReadoutProps {
    history: MetricsHistory | null;
    onOpenTrends: () => void;
    /** Renders a small floating pill instead of the full side panel (Watch Mode). */
    compact?: boolean;
    /** Current live fish count, from the per-tick stats payload. Preferred over
     * the last history sample's `population` field, which only updates every
     * `sample_interval_frames` (500) and otherwise visibly disagrees with the
     * stats bar's live count between samples. Falls back to the last sample
     * when omitted (e.g. in isolation/tests). */
    livePopulation?: number | null;
}

function driftPercent(history: MetricsHistory): number | null {
    const samples = history.samples;
    const first = samples[0]?.traits?.pursuit_aggression;
    const last = samples[samples.length - 1]?.traits?.pursuit_aggression;
    if (!first || last === undefined) return null;
    return ((last - first) / Math.abs(first)) * 100;
}

export function EvolutionHealthReadout({ history, onOpenTrends, compact = false, livePopulation = null }: EvolutionHealthReadoutProps) {
    const [expanded, setExpanded] = useState(false);
    const samples = history?.samples ?? [];
    const first = samples[0];
    const last = samples[samples.length - 1];

    if (!history || samples.length < 2 || !first || !last) {
        if (compact) {
            return (
                <button className={styles.badge} onClick={onOpenTrends} title="Open Trends">
                    <span className={styles.badgeDot} style={{ background: '#94a3b8' }} />
                    Collecting history…
                </button>
            );
        }
        return (
            <aside className={styles.readout} aria-label="Evolution health">
                <div className={styles.header}>Evolution health</div>
                <p className={styles.empty}>Collecting enough history to assess selection.</p>
                <button className={styles.trendsButton} onClick={onOpenTrends}>Open Trends</button>
            </aside>
        );
    }

    const frames = Math.max(1, last.frame - first.frame);
    const generationRate = ((last.max_generation - first.max_generation) / frames) * 10000;
    const pursuitDrift = driftPercent(history);
    const population = livePopulation ?? last.population;
    const populationTone = population >= 20 ? styles.good : styles.warning;
    const diversityTone = (last.diversity_score ?? 0) >= 0.15 ? styles.good : styles.warning;
    const selectionTone = pursuitDrift !== null && Math.abs(pursuitDrift) >= 5 ? styles.good : styles.neutral;

    if (compact) {
        return (
            <button className={styles.badge} onClick={onOpenTrends} title="Open Trends">
                <span
                    className={styles.badgeDot}
                    style={{ background: population >= 20 ? '#4ade80' : '#fbbf24' }}
                />
                <span className={styles.badgeText}>
                    <strong>{population}</strong> fish · {generationRate.toFixed(1)} gen/10k
                </span>
            </button>
        );
    }

    return (
        <aside className={`${styles.readout} ${expanded ? styles.expanded : styles.collapsed}`} aria-label="Evolution health">
            <div className={styles.summaryRow}>
                <button className={styles.summaryToggle} onClick={() => setExpanded((value) => !value)} aria-expanded={expanded}>
                    <span className={styles.header}>🧬 Evolution</span>
                    <span className={styles.summary}>Selection {pursuitDrift === null ? 'pending' : `${pursuitDrift >= 0 ? '+' : ''}${pursuitDrift.toFixed(0)}%`} · Diversity {((last.diversity_score ?? 0) * 100).toFixed(0)}%</span>
                </button>
                <button className={styles.chevron} onClick={() => setExpanded((value) => !value)} aria-label={expanded ? 'Collapse evolution health' : 'Expand evolution health'}>{expanded ? '⌃' : '⌄'}</button>
            </div>
            {expanded && <>
            <div className={styles.window}>Since frame {first.frame.toLocaleString()} · {frames.toLocaleString()} frames</div>
            <div className={styles.metrics}>
                <div className={selectionTone}>
                    <span>Selection</span>
                    <strong>{pursuitDrift === null ? 'Waiting' : `${pursuitDrift >= 0 ? '+' : ''}${pursuitDrift.toFixed(0)}% pursuit`}</strong>
                </div>
                <div className={diversityTone}>
                    <span>Diversity</span>
                    <strong>{((last.diversity_score ?? 0) * 100).toFixed(0)}%</strong>
                </div>
                <div className={populationTone}>
                    <span>Population</span>
                    <strong>{population} fish</strong>
                </div>
                <div className={generationRate >= 5 ? styles.good : styles.warning}>
                    <span>Turnover</span>
                    <strong>{generationRate.toFixed(1)} gen / 10k</strong>
                </div>
            </div>
            <button className={styles.trendsButton} onClick={onOpenTrends}>Open Trends</button>
            </>}
        </aside>
    );
}
