/**
 * Static poker benchmark display component
 */

import type {
    AutoEvaluateStats,
    PokerPerformanceSnapshot,
} from '../types/simulation';
import { colors } from '../styles/theme';

function PerformanceChart({
    history,
}: {
    history: PokerPerformanceSnapshot[];
}) {
    if (!history || history.length === 0) {
        return null;
    }

    const sortedHistory = [...history].sort((a, b) => a.hand - b.hand);
    const width = 1088;
    const height = 400;
    const padding = 50;
    const maxHand = Math.max(...sortedHistory.map((h) => h.hand), 1);
    const minHand = Math.min(...sortedHistory.map((h) => h.hand));
    const handRange = maxHand - minHand || 1;

    // Calculate fish average and standard values for each hand
    const chartData = sortedHistory.map((snapshot) => {
        const fishPlayers = snapshot.players.filter((p) => !p.is_standard);
        const standardPlayer = snapshot.players.find((p) => p.is_standard);

        const fishAvg = fishPlayers.length > 0
            ? fishPlayers.reduce((sum, p) => sum + p.net_energy, 0) / fishPlayers.length
            : 0;

        return {
            hand: snapshot.hand,
            fishAvg,
            standard: standardPlayer?.net_energy || 0,
        };
    });

    const allValues = chartData.flatMap((d) => [d.fishAvg, d.standard]);
    const minValue = Math.min(0, ...allValues);
    const maxValue = Math.max(0, ...allValues);
    const range = maxValue - minValue || 1;

    const scaleX = (hand: number) =>
        padding + ((hand - minHand) / handRange) * (width - padding * 2);
    const scaleY = (value: number) =>
        height - padding - ((value - minValue) / range) * (height - padding * 2);

    // Generate paths for fish average and standard
    const fishPath = chartData
        .map((point, i) => {
            const x = scaleX(point.hand);
            const y = scaleY(point.fishAvg);
            return `${i === 0 ? 'M' : 'L'}${x},${y}`;
        })
        .join(' ');

    const standardPath = chartData
        .map((point, i) => {
            const x = scaleX(point.hand);
            const y = scaleY(point.standard);
            return `${i === 0 ? 'M' : 'L'}${x},${y}`;
        })
        .join(' ');

    return (
        <div style={styles.chartWrapper}>
            <div style={styles.chartHeader}>
                <div>
                    <div style={styles.chartTitle}>
                        Top 3 Fish vs Static Algorithm
                    </div>
                    <div style={styles.chartSubtitle}>
                        Average net energy over time - tracking evolution improvement
                    </div>
                </div>
                <div style={styles.chartLegend}>
                    <div style={styles.legendItem}>
                        <span
                            style={{
                                ...styles.legendSwatch,
                                backgroundColor: '#22c55e',
                            }}
                        />
                        <span>Top 3 Fish (Average)</span>
                    </div>
                    <div style={styles.legendItem}>
                        <span
                            style={{
                                ...styles.legendSwatch,
                                backgroundColor: '#ef4444',
                            }}
                        />
                        <span>Static Algorithm</span>
                    </div>
                </div>
            </div>
            <svg width={width} height={height} style={styles.chartSvg}>
                {/* Zero line */}
                <line
                    x1={padding}
                    y1={scaleY(0)}
                    x2={width - padding}
                    y2={scaleY(0)}
                    stroke={colors.border}
                    strokeDasharray="4 4"
                />

                {/* Fish average line */}
                <path
                    d={fishPath}
                    fill="none"
                    stroke="#22c55e"
                    strokeWidth={3}
                />

                {/* Standard algorithm line */}
                <path
                    d={standardPath}
                    fill="none"
                    stroke="#ef4444"
                    strokeWidth={3}
                    strokeDasharray="5 5"
                />
            </svg>
        </div>
    );
}

export function AutoEvaluateDisplay({
    stats,
    loading,
}: {
    stats: AutoEvaluateStats | null;
    loading: boolean;
}) {
    if (loading && !stats) {
        return (
            <div style={styles.container}>
                <div style={styles.header}>
                    <h2 style={styles.title}>Running benchmark...</h2>
                </div>
                <div style={styles.loading}>
                    <p>
                        Playing poker with the top 3 fish vs static algorithm to track evolution progress.
                    </p>
                    <p style={styles.loadingSubtext}>This may take a moment...</p>
                </div>
            </div>
        );
    }

    if (!stats || !stats.players) {
        return null;
    }

    return (
        <div style={styles.container}>
            <div style={styles.header}>
                <h2 style={styles.title}>Static Poker Benchmark</h2>
            </div>

            <p style={styles.helperText}>
                Tracking how the top 3 fish perform on average versus the static evaluation algorithm.
                This helps visualize improvement as the population evolves over time.
            </p>

            <PerformanceChart history={stats.performance_history ?? []} />
        </div>
    );
}

const styles = {
    container: {
        backgroundColor: colors.bgDark,
        borderRadius: '12px',
        padding: '20px',
        border: `2px solid ${colors.primary}`,
        boxShadow: '0 0 20px rgba(0, 255, 0, 0.2)',
        width: '100%',
        maxWidth: '1088px',
    },
    header: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '20px',
        borderBottom: `1px solid ${colors.border}`,
        paddingBottom: '12px',
    },
    title: {
        margin: 0,
        fontSize: '24px',
        color: colors.primary,
    },
    helperText: {
        margin: '0 0 20px 0',
        color: colors.textSecondary,
        lineHeight: 1.5,
        fontSize: '14px',
    },
    loading: {
        padding: '40px',
        textAlign: 'center' as const,
        fontSize: '16px',
    },
    loadingSubtext: {
        marginTop: '12px',
        color: colors.textSecondary,
        fontSize: '14px',
    },
    chartWrapper: {
        backgroundColor: colors.bgLight,
        border: `1px solid ${colors.border}`,
        borderRadius: '8px',
        padding: '16px',
        marginBottom: '24px',
    },
    chartHeader: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '16px',
    },
    chartTitle: {
        color: colors.primary,
        fontWeight: 700,
        fontSize: '18px',
    },
    chartSubtitle: {
        color: colors.textSecondary,
        fontSize: '13px',
        marginTop: '4px',
    },
    chartSvg: {
        width: '100%',
    },
    chartLegend: {
        display: 'flex',
        gap: '16px',
        flexWrap: 'wrap' as const,
        justifyContent: 'flex-end',
    },
    legendItem: {
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        color: colors.text,
        fontSize: '14px',
    },
    legendSwatch: {
        width: '16px',
        height: '16px',
        borderRadius: '4px',
        display: 'inline-block',
        border: `1px solid ${colors.border}`,
    },
} as const;
