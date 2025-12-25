/**
 * Evolution Benchmark Display Component
 *
 * Displays comprehensive poker skill evolution metrics including:
 * - Population bb/100 (big blinds won per 100 hands)
 * - Performance vs baseline opponent tiers (trivial/weak/moderate/strong)
 * - Longitudinal trend charts
 * - Strategy distribution and improvement metrics
 */

import { useState, useEffect, useMemo, useId } from 'react';
import { colors } from '../styles/theme';
import type { BenchmarkSnapshot, BenchmarkImprovementMetrics, EvolutionBenchmarkData } from '../types/simulation';
import { CollapsibleSection } from './ui';

type ViewMode = 'overview' | 'vs_baselines' | 'longitudinal';
type LongitudinalMetric = 'confidence' | 'bb100' | 'elo';

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

/**
 * Prominent Poker Score display - the single number to focus on for poker skill.
 * Uses conf_strong (confidence vs strong opponents) as the metric.
 * - 50% = coin flip (average)
 * - 55% = can beat strong bots
 * - 70%+ = very good
 * - 90%+ = excellent
 */
function PokerScore({ confStrong, confExpert, confStrongEma, trend }: {
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
    const trendIcon = trend === 'improving' ? '↑' :
        trend === 'declining' ? '↓' : '';
    const trendColor = trend === 'improving' ? '#22c55e' :
        trend === 'declining' ? '#ef4444' : colors.textSecondary;

    const [showTooltip, setShowTooltip] = useState(false);

    const tooltipText = `Poker Score measures confidence that the population is PROFITABLE (not just winning hands) against ${useExpert ? 'expert' : 'strong'} AI opponents.

Based on bb/100 (big blinds won per 100 hands) — this accounts for amounts won/lost, not just hand count.

• 50% = Uncertain (break-even)
• 55%+ = Likely profitable
• 70%+ = Confidently profitable
• 90%+ = Strongly profitable`;

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
                {trend && trendIcon && (
                    <span style={{ color: trendColor, fontSize: '14px', fontWeight: 700 }}>
                        {trendIcon}
                    </span>
                )}
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
                <span style={{ color, fontSize: '42px', fontWeight: 700, lineHeight: 1 }}>
                    {Math.round(score)}
                </span>
                <span style={{ color, fontSize: '20px', fontWeight: 600 }}>%</span>
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

function LongitudinalChart({ history, metric }: { history: BenchmarkSnapshot[]; metric: LongitudinalMetric }) {
    const clipId = useId();
    const [selectedIndex, setSelectedIndex] = useState(1_000_000_000);

    useEffect(() => {
        setSelectedIndex(prev => {
            const lastIndex = Math.max(0, history.length - 1);
            const prevLastIndex = Math.max(0, lastIndex - 1);

            // Follow "latest" if we were already on the latest snapshot (or if this is the initial large sentinel value).
            if (prev >= lastIndex || prev === prevLastIndex) return lastIndex;
            return prev;
        });
    }, [history.length]);

    if (history.length < 2) {
        return <div style={styles.noData}>Need at least 2 snapshots for trend analysis</div>;
    }

    const sorted = [...history].sort((a, b) => a.frame - b.frame);

    const width = 580;
    const height = 200;
    const padding = { top: 16, right: 78, bottom: 44, left: 64 };
    const plotWidth = width - padding.left - padding.right;
    const plotHeight = height - padding.top - padding.bottom;

    const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));

    const formatCompact = (value: number) => {
        const abs = Math.abs(value);
        if (abs >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
        if (abs >= 10_000) return `${(value / 1_000).toFixed(0)}k`;
        if (abs >= 1_000) return `${(value / 1_000).toFixed(1)}k`;
        return `${Math.round(value)}`;
    };

    const percentile = (values: number[], p: number) => {
        if (values.length === 0) return 0;
        const sortedValues = [...values].sort((a, b) => a - b);
        const idx = clamp(Math.floor((sortedValues.length - 1) * p), 0, sortedValues.length - 1);
        return sortedValues[idx];
    };

    const ema = (values: number[], alpha = 0.3) => {
        const out: number[] = [];
        let last: number | null = null;
        for (const v of values) {
            last = last === null ? v : alpha * v + (1 - alpha) * last;
            out.push(last);
        }
        return out;
    };

    const pop = sorted.map(s => s.pop_bb_per_100);
    const weak = sorted.map(s => s.vs_weak);
    const strong = sorted.map(s => s.vs_strong);
    const confWeak = sorted.map(s => s.conf_weak ?? 0.5);
    const confStrong = sorted.map(s => s.conf_strong ?? 0.5);
    const elo = sorted.map(s => s.pop_mean_elo ?? 1200);

    const popEma = ema(pop);
    const weakEma = ema(weak);
    const strongEma = ema(strong);
    const confWeakEma = ema(confWeak, 0.35);
    const confStrongEma = ema(confStrong, 0.35);
    const eloEma = ema(elo, 0.25);

    let minVal = 0;
    let maxVal = 1;
    let clipped = false;

    if (metric === 'confidence') {
        minVal = 0;
        maxVal = 1;
    } else if (metric === 'elo') {
        const all = [...eloEma];
        minVal = Math.min(1100, percentile(all, 0.05));
        maxVal = Math.max(1300, percentile(all, 0.95));
        const pad = Math.max(20, (maxVal - minVal) * 0.12);
        minVal -= pad;
        maxVal += pad;
    } else {
        const allSmoothed = [...popEma, ...weakEma, ...strongEma];
        minVal = Math.min(-10, percentile(allSmoothed, 0.05));
        maxVal = Math.max(10, percentile(allSmoothed, 0.95));
        const pad = Math.max(5, (maxVal - minVal) * 0.12);
        minVal -= pad;
        maxVal += pad;
        minVal = Math.min(minVal, 0);
        maxVal = Math.max(maxVal, 0);

        if (maxVal - minVal > 400) {
            clipped = true;
            minVal = -200;
            maxVal = 200;
        }
    }

    const valRange = maxVal - minVal || 1;

    const minFrame = Math.min(...sorted.map(s => s.frame));
    const maxFrame = Math.max(...sorted.map(s => s.frame));
    const frameRange = maxFrame - minFrame || 1;

    const scaleX = (frame: number) =>
        padding.left + ((frame - minFrame) / frameRange) * plotWidth;

    const scaleY = (val: number) =>
        padding.top + (1 - (val - minVal) / valRange) * plotHeight;

    const points = sorted.map((s, i) => ({
        ...s,
        index: i,
        pop_ema: popEma[i],
        weak_ema: weakEma[i],
        strong_ema: strongEma[i],
        conf_weak_ema: confWeakEma[i],
        conf_strong_ema: confStrongEma[i],
        elo_ema: eloEma[i],
    }));

    const makePath = (getter: (s: typeof points[number]) => number) =>
        points.map((s, i) => `${i === 0 ? 'M' : 'L'}${scaleX(s.frame)},${scaleY(getter(s))}`).join(' ');

    const selected = points[clamp(selectedIndex, 0, points.length - 1)] ?? points[points.length - 1];

    const selectedX = selected ? scaleX(selected.frame) : padding.left;
    const safeY = (val: number) => clamp(scaleY(val), padding.top, height - padding.bottom);

    const labelX = width - padding.right + 6;
    const last = points[points.length - 1];

    const series =
        metric === 'confidence'
            ? [
                { id: 'confWeak', name: 'conf vs Weak (EMA)', color: '#22c55e', dash: '6 3', get: (p: typeof points[number]) => p.conf_weak_ema },
                { id: 'confStrong', name: 'conf vs Strong (EMA)', color: '#ef4444', dash: '3 3', get: (p: typeof points[number]) => p.conf_strong_ema },
            ]
            : metric === 'elo'
                ? [
                    { id: 'elo', name: 'Population Elo (EMA)', color: '#a78bfa', dash: undefined as string | undefined, get: (p: typeof points[number]) => p.elo_ema },
                ]
                : [
                    { id: 'pop', name: 'Population (EMA)', color: '#a78bfa', dash: undefined as string | undefined, get: (p: typeof points[number]) => p.pop_ema },
                    { id: 'weak', name: 'vs Weak (EMA)', color: '#22c55e', dash: '6 3', get: (p: typeof points[number]) => p.weak_ema },
                    { id: 'strong', name: 'vs Strong (EMA)', color: '#ef4444', dash: '3 3', get: (p: typeof points[number]) => p.strong_ema },
                ];

    const formatY = (v: number) => {
        if (metric === 'confidence') return `${Math.round(v * 100)}%`;
        if (metric === 'elo') return `${Math.round(v)}`;
        return `${v >= 0 ? '+' : ''}${v.toFixed(1)}`;
    };

    const outOfRangePrefix = (v: number) => {
        if (metric !== 'bb100') return '';
        if (v > maxVal) return '≥ ';
        if (v < minVal) return '≤ ';
        return '';
    };

    const clampForPlot = (v: number) => {
        if (metric !== 'bb100' || !clipped) return v;
        return clamp(v, minVal, maxVal);
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={styles.chartLegend}>
                {series.map(s => (
                    <div key={`legend-${s.id}`} style={styles.chartLegendItem}>
                        <span
                            style={{
                                ...styles.chartLegendSwatch,
                                borderTopColor: s.color,
                                borderTopStyle: s.dash ? 'dashed' : 'solid',
                            }}
                        />
                        <span>{s.name}</span>
                    </div>
                ))}
            </div>
            <svg width={width} height={height} style={{ overflow: 'hidden' }}>
                <defs>
                    <clipPath id={clipId}>
                        <rect x={padding.left} y={padding.top} width={plotWidth} height={plotHeight} />
                    </clipPath>
                </defs>

                {/* Win/Lose shading */}
                {(() => {
                    const zeroY = scaleY(0);
                    const topY = padding.top;
                    const bottomY = height - padding.bottom;
                    const clampedZero = clamp(zeroY, topY, bottomY);

                    if (metric === 'confidence') {
                        // Confidence bands around 50% / 55% (strong baseline threshold used elsewhere)
                        const y50 = scaleY(0.5);
                        const y55 = scaleY(0.55);
                        const y45 = scaleY(0.45);
                        const yTop = padding.top;
                        const yBot = height - padding.bottom;
                        return (
                            <>
                                <rect x={padding.left} y={yTop} width={plotWidth} height={Math.max(0, y45 - yTop)} fill="rgba(239,68,68,0.05)" />
                                <rect x={padding.left} y={y45} width={plotWidth} height={Math.max(0, y55 - y45)} fill="rgba(148,163,184,0.05)" />
                                <rect x={padding.left} y={y55} width={plotWidth} height={Math.max(0, yBot - y55)} fill="rgba(34,197,94,0.06)" />
                                <line x1={padding.left} y1={y50} x2={padding.left + plotWidth} y2={y50} stroke="rgba(148,163,184,0.25)" strokeDasharray="4 4" />
                            </>
                        );
                    }

                    if (metric === 'elo') {
                        const y1200 = scaleY(1200);
                        return (
                            <>
                                <rect x={padding.left} y={padding.top} width={plotWidth} height={plotHeight} fill="rgba(148,163,184,0.04)" />
                                <line x1={padding.left} y1={y1200} x2={padding.left + plotWidth} y2={y1200} stroke="rgba(148,163,184,0.25)" strokeDasharray="4 4" />
                            </>
                        );
                    }
                    return (
                        <>
                            <rect
                                x={padding.left}
                                y={topY}
                                width={plotWidth}
                                height={Math.max(0, clampedZero - topY)}
                                fill="rgba(34,197,94,0.06)"
                            />
                            <rect
                                x={padding.left}
                                y={clampedZero}
                                width={plotWidth}
                                height={Math.max(0, bottomY - clampedZero)}
                                fill="rgba(239,68,68,0.05)"
                            />
                        </>
                    );
                })()}

                {metric === 'bb100' && (
                    <line
                        x1={padding.left} y1={scaleY(0)}
                        x2={padding.left + plotWidth} y2={scaleY(0)}
                        stroke={colors.border} strokeDasharray="4 4"
                    />
                )}

                {/* Axes */}
                <line x1={padding.left} y1={padding.top} x2={padding.left} y2={height - padding.bottom} stroke={colors.border} />
                <line x1={padding.left} y1={height - padding.bottom} x2={padding.left + plotWidth} y2={height - padding.bottom} stroke={colors.border} />

                {/* Y-axis label */}
                <text x={16} y={height / 2} fill={colors.textSecondary} fontSize={11}
                    transform={`rotate(-90, 16, ${height / 2})`} textAnchor="middle">
                    {metric === 'confidence' ? 'Confidence (EMA)' : metric === 'elo' ? 'Elo (EMA)' : 'bb/100 (EMA)'}
                </text>

                {/* X-axis label */}
                <text x={padding.left + plotWidth / 2} y={height - 6} fill={colors.textSecondary} fontSize={11} textAnchor="middle">
                    Benchmark run (time)
                </text>

                {/* Y-axis ticks */}
                {(metric === 'confidence'
                    ? [0, 0.5, 1]
                    : metric === 'elo'
                        ? [minVal, 1200, maxVal]
                        : [minVal, 0, maxVal]
                ).map(val => (
                    <g key={val}>
                        <line
                            x1={padding.left - 5}
                            y1={scaleY(val)}
                            x2={padding.left + plotWidth}
                            y2={scaleY(val)}
                            stroke={(metric === 'bb100' && val === 0) || (metric === 'confidence' && val === 0.5) || (metric === 'elo' && val === 1200)
                                ? colors.border
                                : 'rgba(148,163,184,0.18)'}
                            strokeDasharray={(metric === 'bb100' && val === 0) || (metric === 'confidence' && val === 0.5) || (metric === 'elo' && val === 1200)
                                ? '4 4'
                                : '2 6'}
                        />
                        <text x={padding.left - 8} y={scaleY(val) + 4} fill={colors.textSecondary} fontSize={10} textAnchor="end">
                            {metric === 'confidence' ? `${Math.round(val * 100)}%` : metric === 'elo' ? `${Math.round(val)}` : `${val > 0 ? '+' : ''}${Math.round(val)}`}
                        </text>
                    </g>
                ))}

                {/* Data (clipped to plot area) */}
                <g clipPath={`url(#${clipId})`}>
                    {series.map(s => (
                        <path
                            key={s.id}
                            d={makePath(p => clampForPlot(s.get(p)))}
                            fill="none"
                            stroke={s.color}
                            strokeWidth={s.id === 'pop' || s.id === 'elo' ? 2.6 : 1.8}
                            strokeDasharray={s.dash}
                        />
                    ))}

                    {/* Selected vertical line */}
                    <line
                        x1={selectedX}
                        y1={padding.top}
                        x2={selectedX}
                        y2={height - padding.bottom}
                        stroke="rgba(148,163,184,0.35)"
                    />
                </g>

                {/* Click targets + selection */}
                {points.map(p => (
                    <circle
                        key={p.frame}
                        cx={scaleX(p.frame)}
                        cy={padding.top + plotHeight / 2}
                        r={10}
                        fill="transparent"
                        style={{ cursor: 'pointer' }}
                        onClick={() => setSelectedIndex(p.index)}
                    />
                ))}

                {/* Selected point markers */}
                {series.map(s => (
                    <circle
                        key={`sel-${s.id}`}
                        cx={selectedX}
                        cy={safeY(s.get(selected))}
                        r={4}
                        fill={s.color}
                        stroke="rgba(15,23,42,0.9)"
                        strokeWidth={2}
                    />
                ))}

                {/* Right-side last value labels */}
                {series.map(s => {
                    const v = s.get(last);
                    const prefix = outOfRangePrefix(v);
                    return (
                        <text
                            key={`last-${s.id}`}
                            x={labelX}
                            y={safeY(v) + 4}
                            fill={s.color}
                            fontSize={10}
                            fontFamily="monospace"
                        >
                            {prefix}{formatY(metric === 'bb100' ? clamp(v, minVal, maxVal) : v)}
                        </text>
                    );
                })}

                {/* X-axis endpoints */}
                <text x={padding.left} y={height - padding.bottom + 16} fill={colors.textSecondary} fontSize={10} textAnchor="start">
                    run 1
                </text>
                <text x={padding.left + plotWidth} y={height - padding.bottom + 16} fill={colors.textSecondary} fontSize={10} textAnchor="end">
                    run {points.length}
                </text>

                {clipped && (
                    <text x={padding.left + 6} y={padding.top + 12} fill={colors.textSecondary} fontSize={10}>
                        bb/100 is volatile; values clipped to ±200 (switch to Confidence for a clearer signal)
                    </text>
                )}
            </svg>

            {selected && (
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
                    <div style={{ color: colors.textSecondary, fontSize: '11px' }}>
                        Selected: run {selected.index + 1}/{points.length} • frame {formatCompact(selected.frame)} • gen ~{selected.generation}
                        {selected.timestamp ? ` • ${selected.timestamp.replace('T', ' ').slice(0, 19)}` : ''}
                    </div>
                    <div style={{ display: 'flex', gap: '12px', color: colors.textSecondary, fontSize: '11px' }}>
                        {selected.pop_mean_elo !== undefined && (
                            <span>Elo {Math.round(selected.pop_mean_elo)}</span>
                        )}
                        {selected.conf_strong !== undefined && (
                            <span>conf vs strong {(selected.conf_strong * 100).toFixed(0)}%</span>
                        )}
                        {selected.fish_evaluated !== undefined && (
                            <span>{selected.fish_evaluated} fish</span>
                        )}
                        {selected.total_hands !== undefined && (
                            <span>{selected.total_hands.toLocaleString()} hands</span>
                        )}
                    </div>
                </div>
            )}

            {points.length < 5 && (
                <div style={{ color: colors.textSecondary, fontSize: '11px' }}>
                    Tip: trends are noisy with &lt; 5 snapshots; focus on Confidence vs Strong (aim &gt; 55%).
                </div>
            )}
        </div>
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
                <span style={{ color: improvement.can_beat_expert ? '#22c55e' : '#ef4444' }}>
                    {improvement.can_beat_expert ? '✓' : '✗'} Expert
                </span>
            </div>
        </div>
    );
}

export function EvolutionBenchmarkDisplay({ tankId }: { tankId?: string }) {
    const [data, setData] = useState<EvolutionBenchmarkData | null>(null);
    const [viewMode, setViewMode] = useState<ViewMode>('overview');
    const [loading, setLoading] = useState(true);
    const [longitudinalMetric, setLongitudinalMetric] = useState<LongitudinalMetric>('confidence');

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
        let cancelled = false;
        const url = tankId ? `/api/tanks/${tankId}/evolution-benchmark` : '/api/evolution-benchmark';

        const fetchData = async () => {
            try {
                const response = await fetch(url);

                // Check content type
                const contentType = response.headers.get('content-type');
                if (!contentType?.includes('application/json')) {
                    // API not available - silently fail
                    if (!cancelled) setLoading(false);
                    return;
                }

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const json = await response.json();
                if (!cancelled) setData(json);
            } catch (e) {
                // Silently fail - API might not be implemented yet
                console.debug('Evolution benchmark API not available:', e);
            } finally {
                if (!cancelled) setLoading(false);
            }
        };

        setLoading(true);
        fetchData();
        const interval = setInterval(fetchData, 30000); // Refresh every 30s
        return () => {
            cancelled = true;
            clearInterval(interval);
        };
    }, [tankId]);

    const latest = data?.latest ?? null;
    const history = useMemo(() => data?.history ?? [], [data?.history]);
    const improvementValue = data?.improvement ?? {};
    const improvement: BenchmarkImprovementMetrics = isImprovementMetrics(improvementValue)
        ? (improvementValue as BenchmarkImprovementMetrics)
        : { status: 'insufficient_data', snapshots_collected: 0 };

    useEffect(() => {
        if (longitudinalMetric !== 'confidence') return;
        if (!history.length) return;
        const hasConfidence = history.some((h: BenchmarkSnapshot) => typeof h.conf_strong === 'number' || typeof h.conf_weak === 'number');
        if (!hasConfidence) setLongitudinalMetric('bb100');
    }, [history, longitudinalMetric]);

    if (loading) {
        return (
            <div className="glass-panel" style={{ padding: '16px' }}>
                <CollapsibleSection
                    title={
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', width: '100%' }}>
                            <span style={{ fontSize: '16px', fontWeight: 600, color: colors.primary }}>Poker Evolution Benchmark</span>
                        </div>
                    }
                    defaultExpanded={true}
                >
                    <div style={styles.noData}>Loading benchmark data...</div>
                </CollapsibleSection>
            </div>
        );
    }

    if (!data || data.status === 'not_available' || !latest) {
        return (
            <div className="glass-panel" style={{ padding: '16px' }}>
                <CollapsibleSection
                    title={
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', width: '100%' }}>
                            <span style={{ fontSize: '16px', fontWeight: 600, color: colors.primary }}>Poker Evolution Benchmark</span>
                        </div>
                    }
                    defaultExpanded={true}
                >
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
                </CollapsibleSection>
            </div>
        );
    }

    return (
        <div className="glass-panel" style={{ padding: '16px' }}>
            <CollapsibleSection
                title={
                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flex: 1, flexWrap: 'wrap' }}>
                        <span style={{ fontSize: '16px', fontWeight: 600, color: colors.primary }}>Poker Evolution Benchmark</span>
                    </div>
                }
                defaultExpanded={true}
            >
                {/* Tabs - Moved to body */}
                <div style={{ marginBottom: '16px' }}>
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

                <div style={{ marginTop: '0px' }}>

                    {viewMode === 'overview' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            {/* Top Row: Score + Metrics */}
                            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px, 1fr) 2fr', gap: '12px' }}>
                                {/* Left: Prominent Poker Score */}
                                <div>
                                    {latest.conf_strong !== undefined && (
                                        <PokerScore
                                            confStrong={latest.conf_strong}
                                            confExpert={latest.conf_expert}
                                            trend={improvement.status === 'tracked' ? improvement.trend_direction : undefined}
                                        />
                                    )}
                                </div>

                                {/* Right: Metrics Grid (2x2) */}
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', alignContent: 'start' }}>
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
                            </div>

                            {/* Bottom Row: Best Performer + Improvement */}
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: '12px', alignItems: 'center' }}>
                                <div style={{ ...styles.bestPerformer, marginBottom: 0, padding: '6px 12px' }}>
                                    <span style={{ color: colors.textSecondary, fontSize: '11px' }}>Best:</span>
                                    <span style={{ color: '#22c55e', fontWeight: 600 }}>
                                        +{latest.best_bb.toFixed(1)} bb/100
                                    </span>
                                    <span style={styles.strategyTag}>{latest.best_strategy ?? latest.dominant_strategy}</span>
                                </div>

                                <div>
                                    <ImprovementBanner improvement={improvement} />
                                </div>
                            </div>
                        </div>
                    )}

                    {viewMode === 'vs_baselines' && (
                        <BaselineBreakdown perBaseline={latest.per_baseline} />
                    )}

                    {viewMode === 'longitudinal' && (
                        <div style={styles.longitudinalView}>
                            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '8px' }}>
                                <div style={styles.miniTabs}>
                                    {(['confidence', 'elo', 'bb100'] as LongitudinalMetric[]).map(m => (
                                        <button
                                            key={m}
                                            onClick={() => setLongitudinalMetric(m)}
                                            style={longitudinalMetric === m ? styles.activeMiniTab : styles.miniTab}
                                        >
                                            {m === 'confidence' ? 'Confidence' : m === 'elo' ? 'Elo' : 'bb/100'}
                                        </button>
                                    ))}
                                </div>
                            </div>
                            <LongitudinalChart history={history} metric={longitudinalMetric} />
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

                </div>

                <div style={styles.footer}>
                    <span style={{ color: colors.textSecondary, fontSize: '10px' }}>
                        Gen {latest.generation} | bb/100 = big blinds won per 100 hands
                    </span>
                </div>
            </CollapsibleSection>
        </div>
    );
}

const styles = {
    // container removed - using glass-panel class
    // header removed - integrated into CollapsibleSection title
    // title removed - styled inline
    tabs: {
        display: 'flex',
        gap: '4px',
        marginLeft: 'auto', // Push tabs to the right
    },
    miniTabs: {
        display: 'flex',
        gap: '4px',
        padding: '3px',
        borderRadius: '8px',
        backgroundColor: 'rgba(15,23,42,0.6)',
        border: `1px solid ${colors.border}`,
    },
    miniTab: {
        padding: '4px 10px',
        borderRadius: '6px',
        border: 'none',
        backgroundColor: 'transparent',
        color: colors.textSecondary,
        cursor: 'pointer',
        fontSize: '12px',
        fontWeight: 600,
    },
    activeMiniTab: {
        padding: '4px 10px',
        borderRadius: '6px',
        border: 'none',
        backgroundColor: '#3b82f6',
        color: '#ffffff',
        cursor: 'pointer',
        fontSize: '12px',
        fontWeight: 700,
    },
    chartLegend: {
        display: 'flex',
        justifyContent: 'flex-end',
        gap: '12px',
        flexWrap: 'wrap' as const,
        padding: '4px 2px 0 2px',
        color: colors.textSecondary,
        fontSize: '11px',
    },
    chartLegendItem: {
        display: 'inline-flex',
        alignItems: 'center',
        gap: '8px',
        padding: '3px 8px',
        borderRadius: '999px',
        backgroundColor: 'rgba(15,23,42,0.45)',
        border: `1px solid rgba(148,163,184,0.18)`,
        userSelect: 'none' as const,
    },
    chartLegendSwatch: {
        width: '22px',
        borderTopWidth: '3px',
        borderTopStyle: 'solid',
        borderTopColor: colors.textSecondary,
        borderRadius: '2px',
        display: 'inline-block',
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
    pokerScoreContainer: {
        backgroundColor: colors.bgLight,
        borderRadius: '12px',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column' as const,
        alignItems: 'center',
        justifyContent: 'center',
        gap: '4px',
        height: '100%', // Fill height in grid
        boxSizing: 'border-box' as const,
        border: `2px solid rgba(59, 130, 246, 0.3)`,
    },
    pokerScoreHeader: {
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        marginBottom: '8px',
    },
    tooltipIcon: {
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: '16px',
        height: '16px',
        borderRadius: '50%',
        backgroundColor: 'rgba(148, 163, 184, 0.3)',
        color: colors.textSecondary,
        fontSize: '10px',
        fontWeight: 700,
        cursor: 'help',
        position: 'relative' as const,
    },
    tooltip: {
        position: 'absolute' as const,
        top: '24px',
        left: '50%',
        transform: 'translateX(-50%)',
        backgroundColor: 'rgba(15, 23, 42, 0.95)',
        border: `1px solid ${colors.border}`,
        borderRadius: '8px',
        padding: '12px 14px',
        fontSize: '11px',
        color: colors.text,
        whiteSpace: 'pre-line' as const,
        width: '260px',
        zIndex: 100,
        boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
        lineHeight: 1.5,
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
