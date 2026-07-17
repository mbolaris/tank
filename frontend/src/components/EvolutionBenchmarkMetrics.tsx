/**
 * Small metric-display components for the Evolution Benchmark display
 * (score cards, baseline breakdown, improvement banner, certainty panel).
 * Extracted from EvolutionBenchmarkDisplay.tsx (god-class ratchet harvest);
 * behavior is unchanged.
 */

import { useState } from 'react';
import { colors } from '../styles/theme';
import type { BenchmarkSnapshot, BenchmarkImprovementMetrics } from '../types/simulation';
import { evolutionBenchmarkStyles as styles } from './evolutionBenchmarkStyles';

export function BbPer100Display({ value, label, showRating = true }: {
    value: number;
    label: string;
    showRating?: boolean;
}) {
    const color = value > 10 ? '#22c55e' : value > 5 ? '#84cc16' : value > 0 ? '#a3e635' :
        value > -5 ? '#eab308' : value > -10 ? '#f97316' : '#ef4444';
    const rating = value > 20 ? 'Crushing' : value > 10 ? 'Strong' : value > 5 ? 'Winning' :
        value > 0 ? 'Break-even' : value > -5 ? 'Losing' : 'Fish';

    return (
        <div style={styles.metricCard}>
            <div style={styles.metricLabel}>{label}</div>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px' }}>
                <span style={{ color, fontSize: '24px', fontWeight: 700 }}>
                    {value >= 0 ? '+' : ''}{value.toFixed(1)}
                </span>
                <span style={{ color: colors.textSecondary, fontSize: '10px' }}>bb/100</span>
                {showRating && (
                    <span style={{ color: colors.textSecondary, fontSize: '10px', fontStyle: 'italic' }}>
                        {rating}
                    </span>
                )}
            </div>
        </div>
    );
}

/**
 * Prominent Poker Score display - the single number to focus on for poker skill.
 * Uses conf_strong (confidence vs strong opponents) as the metric.
 * - 50% = coin flip (average)
 * - 55% = can beat strong bots
 * - 70%+ = very good
 * - 90%+ = excellent
 */
export function PokerScore({ confStrong, confExpert, confStrongEma, trend }: {
    confStrong: number;
    confExpert?: number;
    confStrongEma?: number;
    trend?: 'improving' | 'stable' | 'declining';
}) {
    // Prefer Expert score if available and non-zero
    const useExpert = confExpert !== undefined && confExpert > 0;
    const confValue = useExpert ? confExpert : confStrong;
    const tierLabel = useExpert ? 'vs Expert Opponents' : 'vs Strong Opponents';

    // Color based on score
    const score = confValue * 100;
    const color = score >= 70 ? '#22c55e' :  // Green - very good
        score >= 55 ? '#84cc16' :  // Lime - good (beating strong)
            score >= 50 ? '#eab308' :  // Yellow - average
                score >= 40 ? '#f97316' :  // Orange - below average
                    '#ef4444';                  // Red - poor

    // Rating description
    const rating = score >= 90 ? 'Excellent' :
        score >= 70 ? 'Very Good' :
            score >= 55 ? 'Good' :
                score >= 50 ? 'Average' :
                    score >= 40 ? 'Below Average' :
                        'Needs Work';

    // Trend indicator
    const trendLabel = trend === 'improving' ? 'Improving' :
        trend === 'declining' ? 'Declining' : '';
    const trendColor = trend === 'improving' ? '#22c55e' :
        trend === 'declining' ? '#ef4444' : colors.textSecondary;

    const [showTooltip, setShowTooltip] = useState(false);

    const tooltipText = `Poker Score measures confidence that the population is PROFITABLE (not just winning hands) against ${useExpert ? 'expert' : 'strong'} AI opponents.

Based on bb/100 (big blinds won per 100 hands) - this accounts for amounts won/lost, not just hand count.

- 50% = Uncertain (break-even)
- 55%+ = Likely profitable
- 70%+ = Confidently profitable
- 90%+ = Strongly profitable`;

    return (
        <div style={styles.pokerScoreContainer}>
            <div style={styles.pokerScoreHeader}>
                <span style={{ color: colors.textSecondary, fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    Poker Score
                </span>
                <span
                    style={styles.tooltipIcon}
                    onMouseEnter={() => setShowTooltip(true)}
                    onMouseLeave={() => setShowTooltip(false)}
                >
                    ?
                    {showTooltip && (
                        <div style={styles.tooltip}>
                            {tooltipText}
                        </div>
                    )}
                </span>
                {trendLabel && (
                    <span style={{ color: trendColor, fontSize: '14px', fontWeight: 700 }}>
                        {trendLabel}
                    </span>
                )}
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
                <span style={{ color, fontSize: '32px', fontWeight: 700, lineHeight: 1 }}>
                    {Math.round(score)}
                </span>
                <span style={{ color, fontSize: '16px', fontWeight: 600 }}>%</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px' }}>
                <span style={{ color, fontSize: '12px', fontWeight: 600 }}>
                    {rating}
                </span>
                <span style={{ color: colors.textSecondary, fontSize: '10px' }}>
                    {tierLabel}
                </span>
                {confStrongEma !== undefined && Math.abs(confStrongEma - confStrong) > 0.02 && (
                    <span style={{ color: colors.textSecondary, fontSize: '10px' }}>
                        (EMA: {Math.round(confStrongEma * 100)}%)
                    </span>
                )}
            </div>
        </div>
    );
}

export function BaselineBreakdown({ perBaseline }: { perBaseline: Record<string, number> }) {
    const baselines = [
        { id: 'always_fold', name: 'Always Fold', difficulty: 1 },
        { id: 'random', name: 'Random', difficulty: 1 },
        { id: 'loose_passive', name: 'Calling Station', difficulty: 2 },
        { id: 'tight_passive', name: 'Rock', difficulty: 2 },
        { id: 'tight_aggressive', name: 'TAG Bot', difficulty: 3 },
        { id: 'loose_aggressive', name: 'LAG Bot', difficulty: 3 },
        { id: 'balanced', name: 'Balanced', difficulty: 4 },
        { id: 'maniac', name: 'Maniac', difficulty: 4 },
    ];

    // Filter to only show baselines we have data for
    const availableBaselines = baselines.filter(b => perBaseline[b.id] !== undefined);

    if (availableBaselines.length === 0) {
        return <div style={styles.noData}>No baseline data available</div>;
    }

    return (
        <div style={styles.baselineGrid}>
            {availableBaselines.map(baseline => {
                const bb = perBaseline[baseline.id] ?? 0;
                const barWidth = Math.min(Math.abs(bb) * 2, 100);
                const isPositive = bb >= 0;

                return (
                    <div key={baseline.id} style={styles.baselineRow}>
                        <div style={styles.baselineName}>
                            <span>{baseline.name}</span>
                            <span style={styles.difficulty}>{'*'.repeat(baseline.difficulty)}</span>
                        </div>
                        <div style={styles.baselineBar}>
                            <div style={{
                                position: 'absolute' as const,
                                top: '2px',
                                bottom: '2px',
                                borderRadius: '2px',
                                width: `${barWidth}%`,
                                backgroundColor: isPositive ? '#22c55e' : '#ef4444',
                                left: isPositive ? '50%' : `${50 - barWidth}%`,
                            }} />
                            <div style={styles.baselineZeroLine} />
                        </div>
                        <div style={{
                            ...styles.baselineValue,
                            color: isPositive ? '#22c55e' : '#ef4444',
                        }}>
                            {bb >= 0 ? '+' : ''}{bb.toFixed(1)}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

export function ImprovementBanner({ improvement }: { improvement: BenchmarkImprovementMetrics }) {
    if (improvement.status !== 'tracked') {
        return (
            <div style={styles.improvementBanner}>
                <span style={{ color: colors.textSecondary }}>
                    Collecting data... ({improvement.snapshots_collected} snapshots)
                </span>
            </div>
        );
    }

    const changeColor = (improvement.bb_per_100_change ?? 0) >= 0 ? '#22c55e' : '#ef4444';
    const trendLabel = improvement.is_improving ? 'Improving' :
        improvement.trend_direction === 'stable' ? 'Stable' : 'Declining';
    const trendLabelColor = improvement.is_improving ? '#22c55e' :
        improvement.trend_direction === 'declining' ? '#ef4444' : colors.textSecondary;
    const benchmarkStatuses = [
        { label: 'Trivial', active: improvement.can_beat_trivial },
        { label: 'Weak', active: improvement.can_beat_weak },
        { label: 'Moderate', active: improvement.can_beat_moderate },
        { label: 'Strong', active: improvement.can_beat_strong },
        { label: 'Expert', active: improvement.can_beat_expert },
    ];

    return (
        <div style={styles.improvementBanner}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ color: trendLabelColor, fontSize: '14px', fontWeight: 600 }}>
                    {trendLabel}
                </span>
                <span style={{ color: changeColor, fontWeight: 600 }}>
                    {(improvement.bb_per_100_change ?? 0) >= 0 ? '+' : ''}
                    {(improvement.bb_per_100_change ?? 0).toFixed(1)} bb/100
                </span>
                <span style={{ color: colors.textSecondary, fontSize: '12px' }}>
                    since tracking began
                </span>
            </div>
            <div style={styles.checkmarks}>
                {benchmarkStatuses.map(status => (
                    <span
                        key={status.label}
                        style={{ color: status.active ? '#22c55e' : '#ef4444' }}
                    >
                        {status.label}: {status.active ? 'Yes' : 'No'}
                    </span>
                ))}
            </div>
        </div>
    );
}

function formatSignedBb(value: number): string {
    return `${value >= 0 ? '+' : ''}${value.toFixed(1)}`;
}

function formatCi(ci?: [number, number]): string {
    if (!ci) return 'waiting for next benchmark';
    return `[${formatSignedBb(ci[0])}, ${formatSignedBb(ci[1])}]`;
}

export function BenchmarkCertainty({ latest }: { latest: BenchmarkSnapshot }) {
    const hasUncertainty = latest.pop_bb_per_100_ci_95 || latest.pop_weighted_bb_ci_95;

    return (
        <div style={styles.certaintyPanel}>
            <div style={styles.certaintyHeader}>
                <span style={styles.certaintyTitle}>Benchmark Certainty</span>
                <span style={styles.certaintyMeta}>
                    {latest.total_hands?.toLocaleString() ?? 0} hands · {latest.fish_evaluated ?? 0} fish
                </span>
            </div>
            {hasUncertainty ? (
                <div style={styles.certaintyGrid}>
                    <div style={styles.certaintyMetric}>
                        <span style={styles.certaintyLabel}>Population 95% CI</span>
                        <span style={styles.certaintyValue}>
                            {formatCi(latest.pop_bb_per_100_ci_95)}
                        </span>
                        <span style={styles.certaintySub}>
                            SE {(latest.pop_bb_per_100_se ?? 0).toFixed(2)}
                        </span>
                    </div>
                    <div style={styles.certaintyMetric}>
                        <span style={styles.certaintyLabel}>Weighted 95% CI</span>
                        <span style={styles.certaintyValue}>
                            {formatCi(latest.pop_weighted_bb_ci_95)}
                        </span>
                        <span style={styles.certaintySub}>
                            SE {(latest.pop_weighted_bb_se ?? 0).toFixed(2)}
                        </span>
                    </div>
                </div>
            ) : (
                <div style={styles.certaintyEmpty}>
                    Waiting for a fresh benchmark snapshot with uncertainty fields.
                </div>
            )}
        </div>
    );
}
