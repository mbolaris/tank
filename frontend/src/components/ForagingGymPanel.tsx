import { useEffect, useState } from 'react';
import { colors } from '../styles/theme';
import type { ForagingGymSummary } from '../types/skill';
import { styles } from './ForagingGymPanel.styles';

function percent(value: number): string {
    return `${(value * 100).toFixed(1)}%`;
}

function getSkillDescriptor(score: number): { label: string; description: string } {
    const val = score * 100;
    if (val >= 90) {
        return { label: 'EXPERT', description: 'Perfect or near-optimal route selection' };
    } else if (val >= 75) {
        return { label: 'ADVANCED', description: 'Highly efficient foraging and pathing' };
    } else if (val >= 60) {
        return { label: 'SKILLED', description: 'Efficiently finds most available food' };
    } else if (val >= 45) {
        return { label: 'BASIC', description: 'Basic target selection and food capture' };
    } else {
        return { label: 'POOR', description: 'Inefficient or struggling to locate food' };
    }
}

export function ForagingGymPanel() {
    const [summary, setSummary] = useState<ForagingGymSummary | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let active = true;
        async function fetchSummary() {
            setLoading(true);
            setError(null);
            try {
                const response = await fetch('/api/skill/foraging-gym/summary');
                if (!response.ok) throw new Error(`Failed to load summary (${response.status})`);
                const data: ForagingGymSummary = await response.json();
                if (active) {
                    setSummary(data);
                }
            } catch (cause) {
                if (active) {
                    setError(cause instanceof Error ? cause.message : 'Foraging summary unavailable');
                }
            } finally {
                if (active) {
                    setLoading(false);
                }
            }
        }
        fetchSummary();
        return () => {
            active = false;
        };
    }, []);

    if (loading) {
        return (
            <section style={styles.panel} aria-label="Foraging gym evaluator">
                <div style={styles.titleContainer}>
                    <div style={styles.title}>FORAGING SKILL</div>
                </div>
                <div style={styles.skeletonContainer} data-testid="skeleton">
                    <div style={styles.skeletonRow}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            <div style={styles.skeletonScore} />
                            <div style={styles.skeletonDescription} />
                        </div>
                        <div style={styles.skeletonBadge} />
                    </div>
                    <div style={styles.skeletonTrack} />
                    <div style={styles.skeletonText} />
                </div>
            </section>
        );
    }

    if (error || !summary) {
        return (
            <section style={styles.panel} aria-label="Foraging gym evaluator">
                <div style={styles.titleContainer}>
                    <div style={styles.title}>FORAGING SKILL</div>
                </div>
                <div style={styles.error}>{error || 'Failed to load summary'}</div>
            </section>
        );
    }

    return <ForagingGymSummaryDisplay summary={summary} />;
}

export function ForagingGymSummaryDisplay({ summary }: { summary: ForagingGymSummary }) {
    const [measuredOpen, setMeasuredOpen] = useState(false);
    const [techOpen, setTechOpen] = useState(false);

    const { mean, wandering_mean, perfect_mean, confidence_interval, range, average_food, average_energy } = summary;
    const descriptor = getSkillDescriptor(mean);

    const wPct = wandering_mean * 100;
    const cPct = mean * 100;
    const pPct = perfect_mean * 100;

    return (
        <section style={styles.panel} aria-label="Foraging gym evaluator">
            <div style={styles.titleContainer}>
                <div style={styles.title}>FORAGING SKILL</div>
            </div>

            <div style={styles.scoreRow}>
                <div style={styles.scoreLeft}>
                    <div style={styles.score}>
                        {Math.round(cPct)} <span style={styles.scoreDenom}>/ 100</span>
                    </div>
                    <div style={styles.descriptorText}>{descriptor.description}</div>
                </div>
                <div style={styles.badge}>{descriptor.label}</div>
            </div>

            {/* Comparison Scale */}
            <div style={styles.scaleContainer} aria-label="Comparison scale with three markers">
                {/* Labels Row */}
                <div style={styles.scaleLabels}>
                    <div style={{ ...styles.markerLabel, left: `${wPct}%` }}>
                        <span style={styles.markerName}>Wandering</span>
                    </div>
                    <div style={{ ...styles.markerLabel, left: `${cPct}%` }}>
                        <span style={{ ...styles.markerName, color: colors.success, fontWeight: 700 }}>Current behavior</span>
                    </div>
                    <div style={{ ...styles.markerLabel, left: `${pPct}%` }}>
                        <span style={styles.markerName}>Perfect route</span>
                    </div>
                </div>

                {/* Track Line */}
                <div style={styles.trackLineContainer}>
                    <div style={styles.trackBackground} />
                    <div style={{ ...styles.trackDot, left: `${wPct}%` }} />
                    <div style={{ ...styles.trackDotActive, left: `${cPct}%` }} />
                    <div style={{ ...styles.trackDot, left: `${pPct}%` }} />
                </div>

                {/* Values Row */}
                <div style={styles.scaleValues}>
                    <div style={{ ...styles.markerValueLabel, left: `${wPct}%` }}>
                        <span style={styles.markerValue}>{Math.round(wPct)}</span>
                    </div>
                    <div style={{ ...styles.markerValueLabel, left: `${cPct}%` }}>
                        <span style={{ ...styles.markerValue, color: colors.success, fontWeight: 800 }}>
                            ● {Math.round(cPct)}
                        </span>
                    </div>
                    <div style={{ ...styles.markerValueLabel, left: `${pPct}%` }}>
                        <span style={styles.markerValue}>{Math.round(pPct)}</span>
                    </div>
                </div>
            </div>

            {/* Averages Summary */}
            <div style={styles.averagesInfo}>
                <div style={styles.averagesTitle}>Average across {summary.metadata.seeds.length} standardized trials</div>
                <div style={styles.averagesDetail}>
                    {average_food.toFixed(1)} of 12 food collected · Typical range {Math.round(range[0] * 100)}–{Math.round(range[1] * 100)}
                </div>
            </div>

            {/* How this is measured details */}
            <details
                style={styles.details}
                open={measuredOpen}
                onToggle={(e) => setMeasuredOpen((e.target as HTMLDetailsElement).open)}
                data-testid="details-measurement"
            >
                <summary style={styles.summary}>
                    <span style={styles.arrowIcon}>{measuredOpen ? '▼' : '▶'}</span>
                    How this is measured
                </summary>
                <div style={styles.detailsContent}>
                    The foraging gym measures target selection, target prediction, and physical pathing algorithms
                    under strict day/night and movement cost bounds. It runs a standardized scenario where a single
                    neutral-policy fish chases scripted spawns. Score represents the ratio of food energy captured
                    relative to an omniscient greedy oracle.
                </div>
            </details>

            {/* Technical details */}
            <details
                style={styles.details}
                open={techOpen}
                onToggle={(e) => setTechOpen((e.target as HTMLDetailsElement).open)}
                data-testid="details-technical"
            >
                <summary style={styles.summary}>
                    <span style={styles.arrowIcon}>{techOpen ? '▼' : '▶'}</span>
                    Test details
                </summary>
                <div style={styles.detailsContent}>
                    <div style={styles.techRow}>
                        <span style={styles.techLabel}>Subject:</span>
                        <span style={styles.techVal}>{summary.subject}</span>
                    </div>
                    <div style={styles.techRow}>
                        <span style={styles.techLabel}>Benchmark ID:</span>
                        <span style={styles.techVal}>tank/foraging_gym</span>
                    </div>
                    <div style={styles.techRow}>
                        <span style={styles.techLabel}>Config Hash:</span>
                        <span style={styles.techVal}>{summary.config_hash}</span>
                    </div>
                    <div style={styles.techRow}>
                        <span style={styles.techLabel}>Confidence Interval (95%):</span>
                        <span style={styles.techVal}>
                            {percent(confidence_interval[0])} to {percent(confidence_interval[1])}
                        </span>
                    </div>
                    <div style={styles.techRow}>
                        <span style={styles.techLabel}>Average Energy Captured:</span>
                        <span style={styles.techVal}>{Math.round(average_energy).toLocaleString()}</span>
                    </div>

                    <div style={{ ...styles.averagesTitle, marginTop: '12px', marginBottom: '6px' }}>Per-Seed Trials</div>
                    <table style={styles.table}>
                        <thead>
                            <tr>
                                <th style={styles.th}>Seed</th>
                                <th style={styles.th}>Score</th>
                                <th style={styles.th}>Food</th>
                                <th style={styles.th}>Energy</th>
                            </tr>
                        </thead>
                        <tbody>
                            {summary.metadata.seeds.map(seed => {
                                const seedStr = String(seed);
                                const seedData = summary.metadata.per_seed[seedStr];
                                if (!seedData) return null;
                                return (
                                    <tr key={seed} style={styles.tr}>
                                        <td style={styles.td}>{seed}</td>
                                        <td style={styles.td}>{percent(seedData.score)}</td>
                                        <td style={styles.td}>
                                            {seedData.metadata.composable.food_collected} / {seedData.metadata.oracle.food_collected}
                                        </td>
                                        <td style={styles.td}>
                                            {Math.round(seedData.metadata.composable.energy_collected)} / {Math.round(seedData.metadata.oracle_energy)}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </details>
        </section>
    );
}
