import type { StatsData, GeneDistributionEntry } from '../types/simulation';
import styles from './StandingPopulationPanel.module.css';

interface StandingPopulationPanelProps {
    stats: StatsData | null;
}

function renderHistogramSparkline(entry: GeneDistributionEntry) {
    const bins = entry.bins || [];
    if (bins.length === 0) return null;
    const maxCount = Math.max(...bins, 1);

    return (
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: '2px', height: '24px', marginTop: '6px' }}>
            {bins.map((count, idx) => {
                const heightPct = Math.max(8, (count / maxCount) * 100);
                return (
                    <div
                        key={idx}
                        title={`Bin ${idx + 1}: ${count} fish`}
                        style={{
                            flex: 1,
                            height: `${heightPct}%`,
                            background: count > 0 ? 'linear-gradient(180deg, #38bdf8, #818cf8)' : 'rgba(255, 255, 255, 0.08)',
                            borderRadius: '2px 2px 0 0',
                            transition: 'height 0.2s ease',
                        }}
                    />
                );
            })}
        </div>
    );
}

export function StandingPopulationPanel({ stats }: StandingPopulationPanelProps) {
    if (!stats) return null;

    const rawStats = stats as unknown as Record<string, unknown>;
    const fishCount = Number(rawStats.fish_count ?? rawStats.population ?? 0);
    const maxGen = Number(rawStats.max_generation ?? 0);

    const divStats = rawStats.diversity_stats as Record<string, unknown> | undefined;
    const diversityScore = Number(divStats?.diversity_score ?? rawStats.diversity_score ?? 0);
    const uniqueAlgos = Number(divStats?.unique_algorithms ?? 1);

    const geneDistributions = stats.gene_distributions;
    const physicalGenes = geneDistributions?.physical ?? [];
    const behavioralGenes = geneDistributions?.behavioral ?? [];
    const allDistributions: GeneDistributionEntry[] = [...behavioralGenes, ...physicalGenes];

    return (
        <div className={styles.panel} aria-label="Standing population details">
            <div className={styles.header}>
                <div className={styles.title}>
                    <span>🐟</span>
                    <span>Standing Population</span>
                </div>
                <div className={styles.subtitle}>
                    Living cohort trait distributions & standing variation
                </div>
            </div>

            <div className={styles.statsGrid}>
                <div className={styles.statCard}>
                    <div className={styles.statLabel}>Living Fish</div>
                    <div className={styles.statValue}>{fishCount}</div>
                    <div className={styles.statSub}>Contemporary cohort</div>
                </div>

                <div className={styles.statCard}>
                    <div className={styles.statLabel}>Max Generation</div>
                    <div className={styles.statValue}>Gen {maxGen}</div>
                    <div className={styles.statSub}>Highest generation</div>
                </div>

                <div className={styles.statCard}>
                    <div className={styles.statLabel}>Diversity Score</div>
                    <div className={styles.statValue}>
                        {(diversityScore * 100).toFixed(0)}%
                    </div>
                    <div className={styles.statSub}>
                        {uniqueAlgos} active algorithm{uniqueAlgos !== 1 ? 's' : ''}
                    </div>
                </div>
            </div>

            {allDistributions.length > 0 && (
                <div className={styles.distributionsSection}>
                    <div className={styles.sectionHeading}>Living Trait Distributions (Median & Histograms)</div>
                    <div className={styles.barGrid}>
                        {allDistributions.map((dist) => {
                            const label = dist.label || dist.key;
                            const medianVal = dist.median;
                            const rangeSpan = dist.max > dist.min ? dist.max - dist.min : 1.0;
                            const fillPct = Math.min(100, Math.max(0, ((medianVal - dist.min) / rangeSpan) * 100));

                            return (
                                <div key={dist.key} className={styles.barItem}>
                                    <div className={styles.barHeader}>
                                        <span className={styles.barTitle}>{label}</span>
                                        <span className={styles.barValue}>
                                            Med: {medianVal.toFixed(2)} [{dist.min.toFixed(2)} - {dist.max.toFixed(2)}]
                                        </span>
                                    </div>
                                    <div className={styles.barTrack}>
                                        <div className={styles.barFill} style={{ width: `${fillPct}%` }} />
                                    </div>
                                    {renderHistogramSparkline(dist)}
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}
        </div>
    );
}
