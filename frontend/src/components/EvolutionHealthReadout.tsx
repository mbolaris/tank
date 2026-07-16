import type { MetricsHistory } from '../types/simulation';
import styles from './EvolutionHealthReadout.module.css';

interface EvolutionHealthReadoutProps {
    history: MetricsHistory | null;
    onOpenTrends: () => void;
}

function driftPercent(history: MetricsHistory): number | null {
    const samples = history.samples;
    const first = samples[0]?.traits?.pursuit_aggression;
    const last = samples[samples.length - 1]?.traits?.pursuit_aggression;
    if (!first || last === undefined) return null;
    return ((last - first) / Math.abs(first)) * 100;
}

export function EvolutionHealthReadout({ history, onOpenTrends }: EvolutionHealthReadoutProps) {
    const samples = history?.samples ?? [];
    const first = samples[0];
    const last = samples[samples.length - 1];

    if (!history || samples.length < 2 || !first || !last) {
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
    const populationTone = last.population >= 20 ? styles.good : styles.warning;
    const diversityTone = (last.diversity_score ?? 0) >= 0.15 ? styles.good : styles.warning;
    const selectionTone = pursuitDrift !== null && Math.abs(pursuitDrift) >= 5 ? styles.good : styles.neutral;

    return (
        <aside className={styles.readout} aria-label="Evolution health">
            <div className={styles.header}>Evolution health</div>
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
                    <strong>{last.population} fish</strong>
                </div>
                <div className={generationRate >= 5 ? styles.good : styles.warning}>
                    <span>Turnover</span>
                    <strong>{generationRate.toFixed(1)} gen / 10k</strong>
                </div>
            </div>
            <button className={styles.trendsButton} onClick={onOpenTrends}>Open Trends</button>
        </aside>
    );
}
