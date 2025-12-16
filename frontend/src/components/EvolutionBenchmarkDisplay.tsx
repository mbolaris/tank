/**
 * Evolution Benchmark Display Component
 *
 * Displays comprehensive poker skill evolution metrics including:
 * - Population bb/100 (big blinds won per 100 hands)
 * - Performance vs baseline opponent tiers (trivial/weak/moderate/strong)
 * - Longitudinal trend charts
 * - Strategy distribution and improvement metrics
 */

import { useState, useEffect } from 'react';
import { colors } from '../styles/theme';
import type { BenchmarkSnapshot, BenchmarkImprovementMetrics, EvolutionBenchmarkData } from '../types/simulation';

type ViewMode = 'overview' | 'vs_baselines' | 'longitudinal';

function BbPer100Display({ value, label, showRating = true }: {
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

function LongitudinalChart({ history }: { history: BenchmarkSnapshot[] }) {
    if (history.length < 2) {
        return <div style={styles.noData}>Need at least 2 snapshots for trend analysis</div>;
    }

    const width = 580;
    const height = 200;
    const padding = { top: 20, right: 20, bottom: 40, left: 60 };

    const minGen = Math.min(...history.map(h => h.generation));
    const maxGen = Math.max(...history.map(h => h.generation));
    const genRange = maxGen - minGen || 1;

    const allValues = history.flatMap(h => [h.pop_bb_per_100, h.vs_weak, h.vs_strong]);
    const minVal = Math.min(-15, ...allValues);
    const maxVal = Math.max(15, ...allValues);
    const valRange = maxVal - minVal;

    const scaleX = (gen: number) =>
        padding.left + ((gen - minGen) / genRange) * (width - padding.left - padding.right);
    const scaleY = (val: number) =>
        height - padding.bottom - ((val - minVal) / valRange) * (height - padding.top - padding.bottom);

    const makePath = (getter: (s: BenchmarkSnapshot) => number) =>
        history.map((s, i) => `${i === 0 ? 'M' : 'L'}${scaleX(s.generation)},${scaleY(getter(s))}`).join(' ');

    return (
        <svg width={width} height={height}>
            {/* Zero line */}
            <line
                x1={padding.left} y1={scaleY(0)}
                x2={width - padding.right} y2={scaleY(0)}
                stroke={colors.border} strokeDasharray="4 4"
            />

            {/* Axes */}
            <line x1={padding.left} y1={padding.top} x2={padding.left} y2={height - padding.bottom} stroke={colors.border} />
            <line x1={padding.left} y1={height - padding.bottom} x2={width - padding.right} y2={height - padding.bottom} stroke={colors.border} />

            {/* Y-axis label */}
            <text x={15} y={height/2} fill={colors.textSecondary} fontSize={11}
                  transform={`rotate(-90, 15, ${height/2})`} textAnchor="middle">
                bb/100
            </text>

            {/* X-axis label */}
            <text x={width/2} y={height - 5} fill={colors.textSecondary} fontSize={11} textAnchor="middle">
                Generation
            </text>

            {/* Y-axis ticks */}
            {[minVal, 0, maxVal].map(val => (
                <g key={val}>
                    <line x1={padding.left - 5} y1={scaleY(val)} x2={padding.left} y2={scaleY(val)} stroke={colors.border} />
                    <text x={padding.left - 8} y={scaleY(val) + 4} fill={colors.textSecondary} fontSize={10} textAnchor="end">
                        {val > 0 ? '+' : ''}{Math.round(val)}
                    </text>
                </g>
            ))}

            {/* Population average line */}
            <path d={makePath(s => s.pop_bb_per_100)} fill="none" stroke="#a78bfa" strokeWidth={2.5} />

            {/* vs Weak line */}
            <path d={makePath(s => s.vs_weak)} fill="none" stroke="#22c55e" strokeWidth={1.5} strokeDasharray="6 3" />

            {/* vs Strong line */}
            <path d={makePath(s => s.vs_strong)} fill="none" stroke="#ef4444" strokeWidth={1.5} strokeDasharray="3 3" />

            {/* Legend */}
            <g transform={`translate(${width - padding.right - 140}, ${padding.top + 5})`}>
                <rect x={0} y={0} width={130} height={54} fill="rgba(15,23,42,0.9)" rx={4} />
                <line x1={8} y1={14} x2={28} y2={14} stroke="#a78bfa" strokeWidth={2.5} />
                <text x={34} y={18} fill={colors.text} fontSize={10}>Population Avg</text>
                <line x1={8} y1={28} x2={28} y2={28} stroke="#22c55e" strokeWidth={1.5} strokeDasharray="6 3" />
                <text x={34} y={32} fill={colors.text} fontSize={10}>vs Weak</text>
                <line x1={8} y1={42} x2={28} y2={42} stroke="#ef4444" strokeWidth={1.5} strokeDasharray="3 3" />
                <text x={34} y={46} fill={colors.text} fontSize={10}>vs Strong</text>
            </g>
        </svg>
    );
}

function BaselineBreakdown({ perBaseline }: { perBaseline: Record<string, number> }) {
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
                            <span style={styles.difficulty}>{'★'.repeat(baseline.difficulty)}</span>
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

function ImprovementBanner({ improvement }: { improvement: BenchmarkImprovementMetrics }) {
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
    const trendIcon = improvement.is_improving ? '📈' :
                      improvement.trend_direction === 'stable' ? '➡️' : '📉';

    return (
        <div style={styles.improvementBanner}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '16px' }}>{trendIcon}</span>
                <span style={{ color: changeColor, fontWeight: 600 }}>
                    {(improvement.bb_per_100_change ?? 0) >= 0 ? '+' : ''}
                    {(improvement.bb_per_100_change ?? 0).toFixed(1)} bb/100
                </span>
                <span style={{ color: colors.textSecondary, fontSize: '12px' }}>
                    since tracking began
                </span>
            </div>
            <div style={styles.checkmarks}>
                <span style={{ color: improvement.can_beat_trivial ? '#22c55e' : '#ef4444' }}>
                    {improvement.can_beat_trivial ? '✓' : '✗'} Trivial
                </span>
                <span style={{ color: improvement.can_beat_weak ? '#22c55e' : '#ef4444' }}>
                    {improvement.can_beat_weak ? '✓' : '✗'} Weak
                </span>
                <span style={{ color: improvement.can_beat_moderate ? '#22c55e' : '#ef4444' }}>
                    {improvement.can_beat_moderate ? '✓' : '✗'} Moderate
                </span>
                <span style={{ color: improvement.can_beat_strong ? '#22c55e' : '#ef4444' }}>
                    {improvement.can_beat_strong ? '✓' : '✗'} Strong
                </span>
            </div>
        </div>
    );
}

export function EvolutionBenchmarkDisplay() {
    const [data, setData] = useState<EvolutionBenchmarkData | null>(null);
    const [viewMode, setViewMode] = useState<ViewMode>('overview');
    const [loading, setLoading] = useState(true);

    const isImprovementMetrics = (
        value: EvolutionBenchmarkData['improvement'],
    ): value is BenchmarkImprovementMetrics => {
        return (
            typeof value === 'object' &&
            value !== null &&
            'status' in value &&
            (value as { status?: unknown }).status !== undefined
        );
    };

    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await fetch('/api/evolution-benchmark');

                // Check content type
                const contentType = response.headers.get('content-type');
                if (!contentType?.includes('application/json')) {
                    // API not available - silently fail
                    setLoading(false);
                    return;
                }

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const json = await response.json();
                setData(json);
            } catch (e) {
                // Silently fail - API might not be implemented yet
                console.debug('Evolution benchmark API not available:', e);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
        const interval = setInterval(fetchData, 30000); // Refresh every 30s
        return () => clearInterval(interval);
    }, []);

    if (loading) {
        return (
            <div style={styles.container}>
                <div style={styles.header}>
                    <h2 style={styles.title}>Poker Evolution Benchmark</h2>
                </div>
                <div style={styles.noData}>Loading benchmark data...</div>
            </div>
        );
    }

    if (!data || data.status === 'not_available' || !data.latest) {
        return (
            <div style={styles.container}>
                <div style={styles.header}>
                    <h2 style={styles.title}>Poker Evolution Benchmark</h2>
                </div>
                <div style={styles.noData}>
                    {data?.status === 'not_available'
                        ? 'Benchmark is disabled on the server.'
                        : 'No benchmark data available yet.'}
                    <br />
                    <span style={{ fontSize: '11px', color: colors.textSecondary }}>
                        {data?.status === 'not_available'
                            ? 'Set TANK_EVOLUTION_BENCHMARK_ENABLED=1 and restart the server.'
                            : 'Benchmarks run periodically to measure poker skill evolution.'}
                    </span>
                </div>
            </div>
        );
    }

    const latest = data.latest;
    const history = data.history;
    const improvement: BenchmarkImprovementMetrics = isImprovementMetrics(data.improvement)
        ? data.improvement
        : { status: 'insufficient_data', snapshots_collected: 0 };

    return (
        <div style={styles.container}>
            <div style={styles.header}>
                <h2 style={styles.title}>Poker Evolution Benchmark</h2>
                <div style={styles.tabs}>
                    {(['overview', 'vs_baselines', 'longitudinal'] as ViewMode[]).map(mode => (
                        <button
                            key={mode}
                            onClick={() => setViewMode(mode)}
                            style={viewMode === mode ? styles.activeTab : styles.tab}
                        >
                            {mode === 'overview' ? 'Overview' :
                             mode === 'vs_baselines' ? 'vs Baselines' :
                             'Evolution'}
                        </button>
                    ))}
                </div>
            </div>

            {viewMode === 'overview' && (
                <>
                    <div style={styles.overviewGrid}>
                        <BbPer100Display
                            value={latest.pop_bb_per_100}
                            label="Population bb/100"
                        />
                        <BbPer100Display
                            value={latest.vs_weak}
                            label="vs Weak"
                            showRating={false}
                        />
                        <BbPer100Display
                            value={latest.vs_moderate}
                            label="vs Moderate"
                            showRating={false}
                        />
                        <BbPer100Display
                            value={latest.vs_strong}
                            label="vs Strong"
                            showRating={false}
                        />
                    </div>

                    <div style={styles.bestPerformer}>
                        <span style={{ color: colors.textSecondary, fontSize: '11px' }}>Best Performer:</span>
                        <span style={{ color: '#22c55e', fontWeight: 600 }}>
                            +{latest.best_bb.toFixed(1)} bb/100
                        </span>
                        <span style={styles.strategyTag}>{latest.dominant_strategy}</span>
                    </div>

                    <ImprovementBanner improvement={improvement} />
                </>
            )}

            {viewMode === 'vs_baselines' && (
                <BaselineBreakdown perBaseline={latest.per_baseline} />
            )}

            {viewMode === 'longitudinal' && (
                <div style={styles.longitudinalView}>
                    <LongitudinalChart history={history} />
                    {improvement.status === 'tracked' && (
                        <div style={styles.trendSummary}>
                            <div>
                                <span style={{ color: colors.textSecondary }}>Strategy: </span>
                                {improvement.dominant_strategy_start} → {improvement.dominant_strategy_end}
                            </div>
                            <div>
                                <span style={{ color: colors.textSecondary }}>Generations: </span>
                                {improvement.generation_start} → {improvement.generation_end}
                            </div>
                            <div>
                                <span style={{ color: colors.textSecondary }}>Snapshots: </span>
                                {history.length}
                            </div>
                        </div>
                    )}
                </div>
            )}

            <div style={styles.footer}>
                <span style={{ color: colors.textSecondary, fontSize: '10px' }}>
                    Gen {latest.generation} | bb/100 = big blinds won per 100 hands
                </span>
            </div>
        </div>
    );
}

const styles = {
    container: {
        backgroundColor: colors.bgDark,
        borderRadius: '12px',
        padding: '12px',
        border: `1px solid ${colors.border}`,
        maxWidth: '620px',
    },
    header: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '12px',
        borderBottom: `1px solid ${colors.border}`,
        paddingBottom: '8px',
    },
    title: {
        margin: 0,
        fontSize: '14px',
        color: colors.primary,
    },
    tabs: {
        display: 'flex',
        gap: '4px',
    },
    tab: {
        background: 'transparent',
        border: `1px solid ${colors.border}`,
        color: colors.textSecondary,
        fontSize: '10px',
        padding: '3px 8px',
        borderRadius: '4px',
        cursor: 'pointer',
    },
    activeTab: {
        background: colors.primary,
        border: `1px solid ${colors.primary}`,
        color: '#fff',
        fontSize: '10px',
        padding: '3px 8px',
        borderRadius: '4px',
        cursor: 'pointer',
    },
    overviewGrid: {
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '8px',
        marginBottom: '12px',
    },
    metricCard: {
        backgroundColor: colors.bgLight,
        borderRadius: '8px',
        padding: '12px 8px',
        display: 'flex',
        flexDirection: 'column' as const,
        alignItems: 'center',
        gap: '4px',
    },
    metricLabel: {
        color: colors.textSecondary,
        fontSize: '10px',
        textTransform: 'uppercase' as const,
        textAlign: 'center' as const,
    },
    bestPerformer: {
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        padding: '8px 12px',
        backgroundColor: colors.bgLight,
        borderRadius: '6px',
        marginBottom: '8px',
    },
    strategyTag: {
        backgroundColor: 'rgba(167, 139, 250, 0.2)',
        color: '#a78bfa',
        fontSize: '10px',
        padding: '2px 8px',
        borderRadius: '4px',
    },
    improvementBanner: {
        backgroundColor: colors.bgLight,
        borderRadius: '6px',
        padding: '10px 12px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap' as const,
        gap: '8px',
    },
    checkmarks: {
        display: 'flex',
        gap: '12px',
        fontSize: '11px',
    },
    baselineGrid: {
        display: 'flex',
        flexDirection: 'column' as const,
        gap: '6px',
    },
    baselineRow: {
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
    },
    baselineName: {
        width: '120px',
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: '11px',
        color: colors.text,
    },
    difficulty: {
        color: '#eab308',
        fontSize: '9px',
    },
    baselineBar: {
        flex: 1,
        height: '16px',
        backgroundColor: colors.bgLight,
        borderRadius: '4px',
        position: 'relative' as const,
        overflow: 'hidden',
    },
    baselineZeroLine: {
        position: 'absolute' as const,
        left: '50%',
        top: 0,
        bottom: 0,
        width: '1px',
        backgroundColor: colors.border,
    },
    baselineValue: {
        width: '50px',
        textAlign: 'right' as const,
        fontSize: '12px',
        fontWeight: 600,
    },
    longitudinalView: {
        display: 'flex',
        flexDirection: 'column' as const,
        gap: '12px',
    },
    trendSummary: {
        display: 'flex',
        gap: '16px',
        fontSize: '11px',
        color: colors.text,
        flexWrap: 'wrap' as const,
    },
    noData: {
        padding: '24px',
        textAlign: 'center' as const,
        color: colors.textSecondary,
        fontSize: '13px',
    },
    footer: {
        marginTop: '8px',
        paddingTop: '8px',
        borderTop: `1px solid ${colors.border}`,
        textAlign: 'center' as const,
    },
} as const;
