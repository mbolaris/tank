import { useState, useMemo } from 'react';
import type { StatsData, GeneDistributionEntry } from '../types/simulation';
import SizeSummaryGraph from './ui/SizeSummaryGraph';
import styles from './StandingPopulationPanel.module.css';

interface StandingPopulationPanelProps {
    stats: StatsData | null;
}

const DISCRETE_LABEL_MAPS: Record<string, string[]> = {
    template_id: ['Round', 'Torpedo', 'Flat', 'Angular', 'Chubby', 'Eel'],
    pattern_type: ['Stripe', 'Spots', 'Solid', 'Grad', 'Chevron', 'Scale'],
    threat_response: ['Panic', 'Stealth', 'Freeze', 'Erratic'],
    food_approach: ['Direct', 'Predict', 'Circle', 'Ambush', 'Zigzag', 'Patrol'],
    energy_style: ['Conserv', 'Burst', 'Balance'],
    social_mode: ['Solo', 'Loose', 'Tight', 'Follow'],
    poker_engagement: ['Avoid', 'Passive', 'Opport', 'Aggro'],
    poker_hand_selection: ['Tight', 'Medium', 'Loose', 'Any'],
    poker_betting_style: ['Passive', 'Balanced', 'Aggressive', 'Hyper'],
    poker_bluffing_approach: ['Never', 'Rare', 'Occasional', 'Frequent'],
};

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
    const [selectedCategory, setSelectedCategory] = useState<'all' | 'physical' | 'behavioral'>('all');
    const [searchQuery, setSearchQuery] = useState('');
    const [viewMode, setViewMode] = useState<'graphs' | 'compact'>('graphs');

    const geneDistributions = stats?.gene_distributions;
    const physicalGenes = geneDistributions?.physical ?? [];
    const behavioralGenes = geneDistributions?.behavioral ?? [];

    const allDistributions: GeneDistributionEntry[] = useMemo(() => {
        const physicalWithCat = physicalGenes.map(g => ({ ...g, category: 'physical' as const }));
        const behavioralWithCat = behavioralGenes.map(g => ({ ...g, category: 'behavioral' as const }));
        return [...physicalWithCat, ...behavioralWithCat];
    }, [physicalGenes, behavioralGenes]);

    const filteredDistributions = useMemo(() => {
        return allDistributions.filter(dist => {
            const matchesCategory =
                selectedCategory === 'all' || dist.category === selectedCategory;
            const matchesSearch =
                !searchQuery ||
                dist.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
                dist.key.toLowerCase().includes(searchQuery.toLowerCase());
            return matchesCategory && matchesSearch;
        });
    }, [allDistributions, selectedCategory, searchQuery]);

    if (!stats) {
        return (
            <div className={styles.panel} aria-label="Standing population details loading">
                <div className={styles.header}>
                    <div className={styles.title}>
                        <span>🐟</span>
                        <span>Living Trait Distributions (Median & Histograms)</span>
                    </div>
                </div>
                <div style={{ padding: '24px', textAlign: 'center', color: '#94a3b8', fontSize: '13px' }}>
                    Connecting to telemetry for trait distribution stats...
                </div>
            </div>
        );
    }

    const rawStats = stats as unknown as Record<string, unknown>;
    const fishCount = Number(rawStats.fish_count ?? rawStats.population ?? 0);
    const maxGen = Number(rawStats.max_generation ?? 0);

    const divStats = rawStats.diversity_stats as Record<string, unknown> | undefined;
    const diversityScore = Number(divStats?.diversity_score ?? rawStats.diversity_score ?? 0);
    const uniqueAlgos = Number(divStats?.unique_algorithms ?? 1);

    return (
        <div className={styles.panel} aria-label="Standing population details">
            {/* Header */}
            <div className={styles.header}>
                <div>
                    <div className={styles.title}>
                        <span style={{ fontSize: '18px' }}>🧬</span>
                        <span>Living Trait Distributions (Median & Histograms)</span>
                    </div>
                    <div className={styles.subtitle}>
                        Standing genetic variation & allele frequency histograms across active cohort
                    </div>
                </div>

                <div className={styles.controlsRow}>
                    <div className={styles.viewToggle}>
                        <button
                            type="button"
                            className={`${styles.toggleBtn} ${viewMode === 'graphs' ? styles.activeToggle : ''}`}
                            onClick={() => setViewMode('graphs')}
                            title="Detailed Graph View"
                        >
                            📊 Graphs
                        </button>
                        <button
                            type="button"
                            className={`${styles.toggleBtn} ${viewMode === 'compact' ? styles.activeToggle : ''}`}
                            onClick={() => setViewMode('compact')}
                            title="Compact Sparkline View"
                        >
                            ⚡ Compact
                        </button>
                    </div>
                </div>
            </div>

            {/* Quick Stat Cards */}
            <div className={styles.statsGrid}>
                <div className={styles.statCard}>
                    <div className={styles.statLabel}>Living Fish</div>
                    <div className={styles.statValue}>{fishCount}</div>
                    <div className={styles.statSub}>Active cohort</div>
                </div>

                <div className={styles.statCard}>
                    <div className={styles.statLabel}>Max Generation</div>
                    <div className={styles.statValue}>Gen {maxGen}</div>
                    <div className={styles.statSub}>Lineage depth</div>
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

                <div className={styles.statCard}>
                    <div className={styles.statLabel}>Tracked Traits</div>
                    <div className={styles.statValue}>{allDistributions.length}</div>
                    <div className={styles.statSub}>Physical & behavioral</div>
                </div>
            </div>

            {/* Filter Bar */}
            {allDistributions.length > 0 && (
                <div className={styles.filterBar}>
                    <div className={styles.categoryPills}>
                        <button
                            type="button"
                            className={`${styles.pillBtn} ${selectedCategory === 'all' ? styles.activePill : ''}`}
                            onClick={() => setSelectedCategory('all')}
                        >
                            All ({allDistributions.length})
                        </button>
                        <button
                            type="button"
                            className={`${styles.pillBtn} ${selectedCategory === 'physical' ? styles.activePill : ''}`}
                            onClick={() => setSelectedCategory('physical')}
                        >
                            🧬 Physical ({physicalGenes.length})
                        </button>
                        <button
                            type="button"
                            className={`${styles.pillBtn} ${selectedCategory === 'behavioral' ? styles.activePill : ''}`}
                            onClick={() => setSelectedCategory('behavioral')}
                        >
                            🧠 Behavioral ({behavioralGenes.length})
                        </button>
                    </div>

                    <input
                        type="text"
                        placeholder="Search gene traits..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className={styles.searchInput}
                    />
                </div>
            )}

            {/* Graphs Grid View */}
            {filteredDistributions.length > 0 ? (
                viewMode === 'graphs' ? (
                    <div className={styles.graphsGrid}>
                        {filteredDistributions.map((g) => {
                            const integerValues = g.discrete === true;
                            const labels = DISCRETE_LABEL_MAPS[g.key];
                            const meta = g.meta;
                            const isBehavioral = g.category === 'behavioral';

                            return (
                                <div
                                    key={g.key}
                                    className={`${styles.graphCard} ${isBehavioral ? styles.behavioralCard : styles.physicalCard}`}
                                >
                                    <div className={styles.graphCardHeader}>
                                        <div className={styles.graphTitleGroup}>
                                            <span className={styles.graphTitle}>{g.label || g.key}</span>
                                            <span className={styles.categoryBadge}>
                                                {isBehavioral ? '🧠 Behavior' : '🧬 Physical'}
                                            </span>
                                        </div>
                                        <div className={styles.medianTag}>
                                            Med: <strong style={{ color: isBehavioral ? '#e879f9' : '#38bdf8' }}>{g.median.toFixed(2)}</strong>
                                        </div>
                                    </div>

                                    <div className={styles.graphBody}>
                                        <SizeSummaryGraph
                                            bins={g.bins}
                                            binEdges={g.bin_edges}
                                            min={g.min}
                                            median={g.median}
                                            max={g.max}
                                            allowedMin={g.allowed_min}
                                            allowedMax={g.allowed_max}
                                            width={280}
                                            height={90}
                                            xLabel={g.label}
                                            yLabel="Fish"
                                            integerValues={integerValues}
                                            labels={labels}
                                            theme={g.category}
                                            mutationRateMean={meta?.mut_rate_mean}
                                            mutationRateStd={meta?.mut_rate_std}
                                            mutationStrengthMean={meta?.mut_strength_mean}
                                            mutationStrengthStd={meta?.mut_strength_std}
                                            hgtProbMean={meta?.hgt_prob_mean}
                                            hgtProbStd={meta?.hgt_prob_std}
                                        />
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                ) : (
                    /* Compact Sparkline View */
                    <div className={styles.barGrid}>
                        {filteredDistributions.map((dist) => {
                            const label = dist.label || dist.key;
                            const medianVal = dist.median;
                            const rangeSpan = dist.max > dist.min ? dist.max - dist.min : 1.0;
                            const fillPct = Math.min(100, Math.max(0, ((medianVal - dist.min) / rangeSpan) * 100));
                            const isBehavioral = dist.category === 'behavioral';

                            return (
                                <div key={dist.key} className={styles.barItem}>
                                    <div className={styles.barHeader}>
                                        <span className={styles.barTitle}>
                                            {label}
                                            <span className={styles.miniTag}>
                                                {isBehavioral ? '🧠' : '🧬'}
                                            </span>
                                        </span>
                                        <span className={styles.barValue}>
                                            Med: {medianVal.toFixed(2)} [{dist.min.toFixed(2)} - {dist.max.toFixed(2)}]
                                        </span>
                                    </div>
                                    <div className={styles.barTrack}>
                                        <div
                                            className={styles.barFill}
                                            style={{
                                                width: `${fillPct}%`,
                                                background: isBehavioral
                                                    ? 'linear-gradient(90deg, #c084fc, #e879f9)'
                                                    : 'linear-gradient(90deg, #38bdf8, #818cf8)'
                                            }}
                                        />
                                    </div>
                                    {renderHistogramSparkline(dist)}
                                </div>
                            );
                        })}
                    </div>
                )
            ) : (
                <div style={{ padding: '20px', textAlign: 'center', color: '#94a3b8', fontSize: '12px' }}>
                    {searchQuery ? `No gene traits match "${searchQuery}"` : 'No trait distribution data available'}
                </div>
            )}
        </div>
    );
}

