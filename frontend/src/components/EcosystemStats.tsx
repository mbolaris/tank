/**
 * Ecosystem statistics component
 * Displays non-poker stats below the tank simulation
 */

import type { StatsData, EntityData } from '../types/simulation';
import styles from './EcosystemStats.module.css';

interface EcosystemStatsProps {
    stats: StatsData | null;
    entities?: EntityData[] | null;
}

export function EcosystemStats({ stats, entities }: EcosystemStatsProps) {
    if (!stats) {
        return null;
    }

    const deathCauseEntries = Object.entries(stats.death_causes);

    return (
        <div className={styles.container}>
            <div className={styles.section}>
                <div className={styles.sectionTitle}>Ecosystem</div>
                <div className={styles.statsGrid}>
                    <div className={styles.statItem}>
                        <span className={styles.label}>Food:</span>
                        <span className={styles.value}>{stats.food_count}</span>
                    </div>
                    <div className={styles.statItem}>
                        <span className={styles.label}>Live Food:</span>
                        <span className={styles.value}>
                            {stats.live_food_count} ({Math.round(stats.live_food_energy)}E)
                        </span>
                    </div>

                </div>
            </div>

            <div className={styles.section}>
                <div className={styles.sectionTitle}>Population</div>
                <div className={styles.statsGrid}>
                    <div className={styles.statItem}>
                        <span className={styles.label}>Fish Alive:</span>
                        <span className={styles.value}>{stats.fish_count}</span>
                    </div>
                    <div className={styles.statItem}>
                        <span className={styles.label}>Total Births:</span>
                        <span className={styles.value}>{stats.births}</span>
                    </div>
                    <div className={styles.statItem}>
                        <span className={styles.label}>Total Deaths:</span>
                        <span className={styles.value}>{stats.deaths}</span>
                    </div>
                </div>
            </div>

            {deathCauseEntries.length > 0 && (
                <div className={styles.section}>
                    <div className={styles.sectionTitle}>Death Causes</div>
                    <div className={styles.statsGrid}>
                        {deathCauseEntries.map(([cause, count]) => (
                            <div key={cause} className={styles.statItem}>
                                <span className={styles.label}>{cause}:</span>
                                <span className={styles.value}>{count}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            <div className={styles.section}>
                <div className={styles.sectionTitle}>Gene Distribution</div>
                <div className={styles.geneGrid}>
                    <GeneHistogram label="Adult Size" values={collectTrait('size', entities)} min={0.5} max={2} />
                    <GeneHistogram label="Eye Size" values={collectTrait('eye_size', entities)} min={0.5} max={2} />
                    <GeneHistogram label="Tail Size" values={collectTrait('tail_size', entities)} min={0} max={2} />
                    <GeneHistogram label="Fin Size" values={collectTrait('fin_size', entities)} min={0} max={2} />
                    <GeneHistogram label="Body Aspect" values={collectTrait('body_aspect', entities)} min={0.5} max={2} />
                    <GeneHistogram label="Template ID" values={collectTrait('template_id', entities)} min={0} max={10} discrete />
                </div>
            </div>
        </div>
    );
}

// Helper: collect trait values from stats entities
function collectTrait(trait: string, entities?: EntityData[] | null) {
    const vals: number[] = [];
    // Prefer passed entities when available
    const list = Array.isArray(entities) ? entities : (window as any).__lastEntities;
    if (!Array.isArray(list)) return vals;
    for (const e of list) {
        const g: any = e.genome_data || e.genome || e;
        if (!g) continue;
        const v = g[trait];
        if (typeof v === 'number') vals.push(v);
    }
    return vals;
}

interface GeneHistogramProps {
    label: string;
    values: number[];
    min: number;
    max: number;
    discrete?: boolean;
}

function GeneHistogram({ label, values, min, max, discrete }: GeneHistogramProps) {
    const bins = discrete ? Math.max(4, Math.ceil(max - min + 1)) : 6;
    const counts = new Array(bins).fill(0);
    for (const v of values) {
        if (v == null || isNaN(v)) continue;
        let idx = 0;
        if (discrete) {
            idx = Math.min(bins - 1, Math.max(0, Math.round(v - min)));
        } else {
            const t = (v - min) / (max - min);
            idx = Math.min(bins - 1, Math.max(0, Math.floor(t * bins)));
        }
        counts[idx]++;
    }
    const maxCount = Math.max(1, ...counts);

    return (
        <div className={styles.histogramCard}>
            <div className={styles.histogramLabel}>{label}</div>
            <div className={styles.histogram}>
                {counts.map((c, i) => (
                    <div key={i} className={styles.histBarWrap}>
                        <div className={styles.histBar} style={{ height: `${(c / maxCount) * 80}%` }} />
                    </div>
                ))}
            </div>
        </div>
    );
}
