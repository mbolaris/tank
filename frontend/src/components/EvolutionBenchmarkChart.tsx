/**
 * Longitudinal trend chart for the Evolution Benchmark display. Extracted
 * from EvolutionBenchmarkDisplay.tsx (god-class ratchet harvest); behavior
 * is unchanged.
 */

import { useState, useEffect, useId } from 'react';
import { colors } from '../styles/theme';
import type { BenchmarkSnapshot } from '../types/simulation';
import { evolutionBenchmarkStyles as styles } from './evolutionBenchmarkStyles';

export type LongitudinalMetric = 'confidence' | 'bb100' | 'elo';

export function LongitudinalChart({ history, metric }: { history: BenchmarkSnapshot[]; metric: LongitudinalMetric }) {
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
    const confExpert = sorted.map(s => s.conf_expert ?? 0.5);
    const elo = sorted.map(s => s.pop_mean_elo ?? 1200);

    const popEma = ema(pop);
    const weakEma = ema(weak);
    const strongEma = ema(strong);
    const confWeakEma = ema(confWeak, 0.35);
    const confStrongEma = ema(confStrong, 0.35);
    const confExpertEma = ema(confExpert, 0.35);
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
        conf_expert_ema: confExpertEma[i],
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
                { id: 'confExpert', name: 'conf vs Expert (EMA)', color: '#a78bfa', dash: '2 2', get: (p: typeof points[number]) => p.conf_expert_ema },
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
        if (v > maxVal) return '>= ';
        if (v < minVal) return '<= ';
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
            <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 'auto', display: 'block', overflow: 'hidden' }}>
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
                        bb/100 is volatile; values clipped to +/-200 (switch to Confidence for a clearer signal)
                    </text>
                )}
            </svg>

            {selected && (
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
                    <div style={{ color: colors.textSecondary, fontSize: '11px' }}>
                        Selected: run {selected.index + 1}/{points.length} | frame {formatCompact(selected.frame)} | gen ~{selected.generation}
                        {selected.timestamp ? ` | ${selected.timestamp.replace('T', ' ').slice(0, 19)}` : ''}
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
