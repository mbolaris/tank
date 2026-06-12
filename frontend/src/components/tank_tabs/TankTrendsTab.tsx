import { useState } from 'react';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    Tooltip,
    ReferenceLine,
    ResponsiveContainer,
    CartesianGrid
} from 'recharts';
import type { MetricsHistory } from '../../types/simulation';

interface TankTrendsTabProps {
    history: MetricsHistory | null;
}

type XAxisMode = 'frames' | 'generations';

interface AggregatedPoint {
    max_generation: number;
    population: number;
    fish_energy: number;
    births_total: number;
    deaths_total: number;
    poker: {
        auto_eval_elo: number;
    };
    soccer: {
        goals_per_1k_frames: number;
    };
}

// Helper to calculate trend delta and percentage change between first and last quartiles
function calculateTrend(values: number[]): { delta: number; pct: number } {
    if (values.length < 2) return { delta: 0, pct: 0 };
    const len = values.length;
    const qSize = Math.max(1, Math.floor(len / 4));

    const firstQuartile = values.slice(0, qSize);
    const lastQuartile = values.slice(len - qSize);

    const meanFirst = firstQuartile.reduce((a, b) => a + b, 0) / qSize;
    const meanLast = lastQuartile.reduce((a, b) => a + b, 0) / qSize;

    const delta = meanLast - meanFirst;
    const pct = meanFirst !== 0 ? (delta / Math.abs(meanFirst)) * 100 : 0;

    return { delta, pct };
}

interface TrendBadgeProps {
    values: number[];
    formatter?: (v: number) => string;
}

function TrendBadge({ values, formatter }: TrendBadgeProps) {
    const { delta, pct } = calculateTrend(values);
    const formatVal = formatter ? formatter(delta) : delta.toFixed(1);
    const sign = delta > 0 ? '+' : '';

    // Deem neutral if absolute delta is extremely close to 0 or percentage change is less than 0.1%
    const isNeutral = Math.abs(delta) < 0.0001 || Math.abs(pct) < 0.1;

    if (isNeutral) {
        return (
            <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                padding: '2px 8px',
                borderRadius: '4px',
                fontSize: '10px',
                fontWeight: 600,
                background: 'rgba(148, 163, 184, 0.15)',
                color: '#94a3b8',
                fontFamily: 'var(--font-mono)'
            }}>
                ◆ {sign}{formatVal} (0.0%)
            </span>
        );
    }

    const isPositive = delta > 0;
    return (
        <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            padding: '2px 8px',
            borderRadius: '4px',
            fontSize: '10px',
            fontWeight: 600,
            background: isPositive ? 'rgba(74, 222, 128, 0.15)' : 'rgba(248, 113, 113, 0.15)',
            color: isPositive ? '#4ade80' : '#f87171',
            fontFamily: 'var(--font-mono)'
        }}>
            {isPositive ? '▲' : '▼'} {sign}{formatVal} ({isPositive ? '+' : ''}{pct.toFixed(1)}%)
        </span>
    );
}

interface TooltipPayloadItem {
    name: string;
    value: number;
    color?: string;
}

interface CustomTooltipProps {
    active?: boolean;
    payload?: TooltipPayloadItem[];
    label?: number | string;
    xAxisMode: XAxisMode;
}

// Custom Tooltip component for high-quality dark theme styling
const CustomTooltip = ({ active, payload, label, xAxisMode }: CustomTooltipProps) => {
    if (active && payload && payload.length && label !== undefined) {
        return (
            <div style={{
                background: 'rgba(15, 23, 42, 0.95)',
                border: '1px solid var(--card-border)',
                borderRadius: '8px',
                padding: '8px 12px',
                boxShadow: '0 4px 20px rgba(0, 0, 0, 0.4)',
                fontSize: '12px'
            }}>
                <div style={{
                    color: 'var(--color-text-dim)',
                    marginBottom: '4px',
                    fontWeight: 600,
                    fontFamily: 'var(--font-mono)'
                }}>
                    {xAxisMode === 'frames' ? `Frame: ${label.toLocaleString()}` : `Generation: ${label}`}
                </div>
                {payload.map((p, idx) => (
                    <div key={idx} style={{
                        color: p.color || 'var(--color-text-main)',
                        display: 'flex',
                        gap: '12px',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        fontFamily: 'var(--font-mono)',
                        marginTop: idx > 0 ? '2px' : 0
                    }}>
                        <span>{p.name}:</span>
                        <span style={{ fontWeight: 600 }}>{p.value.toLocaleString()}</span>
                    </div>
                ))}
            </div>
        );
    }
    return null;
};

export function TankTrendsTab({ history }: TankTrendsTabProps) {
    const [xAxisMode, setXAxisMode] = useState<XAxisMode>('frames');

    // Handle null or empty history state
    if (!history || !history.samples || history.samples.length === 0) {
        const nextSampleFrame = history?.sample_interval_frames || 500;
        return (
            <div style={{
                background: 'var(--card-bg)',
                border: '1px solid var(--card-border)',
                borderRadius: 'var(--radius-md)',
                padding: '32px',
                textAlign: 'center',
                color: 'var(--color-text-muted)',
                fontFamily: 'var(--font-main)'
            }}>
                <div style={{ fontSize: '24px', marginBottom: '8px' }}>📈</div>
                <div style={{ fontWeight: 600, color: 'var(--color-text-main)', marginBottom: '4px' }}>
                    Collecting Trend Samples...
                </div>
                <div style={{ fontSize: '12px' }}>
                    First data point will be collected at frame {nextSampleFrame.toLocaleString()}.
                </div>
            </div>
        );
    }

    const { samples } = history;

    // Aggregate samples by max_generation if in generations mode
    let data: (import('../../types/simulation').MetricsSample | AggregatedPoint)[] = samples;
    if (xAxisMode === 'generations') {
        const genMap: Record<number, {
            count: number;
            populationSum: number;
            eloSum: number;
            goalsSum: number;
            fishEnergySum: number;
            birthsSum: number;
            deathsSum: number;
        }> = {};

        samples.forEach(s => {
            const gen = s.max_generation;
            if (!genMap[gen]) {
                genMap[gen] = {
                    count: 0,
                    populationSum: 0,
                    eloSum: 0,
                    goalsSum: 0,
                    fishEnergySum: 0,
                    birthsSum: 0,
                    deathsSum: 0,
                };
            }
            const g = genMap[gen];
            g.count++;
            g.populationSum += s.population;
            g.eloSum += s.poker?.auto_eval_elo ?? 0;
            g.goalsSum += s.soccer?.goals_per_1k_frames ?? 0;
            g.fishEnergySum += s.fish_energy;
            g.birthsSum += s.births_total;
            g.deathsSum += s.deaths_total;
        });

        data = Object.keys(genMap)
            .map(Number)
            .sort((a, b) => a - b)
            .map(gen => {
                const g = genMap[gen];
                return {
                    max_generation: gen,
                    population: Number((g.populationSum / g.count).toFixed(2)),
                    poker: {
                        auto_eval_elo: Number((g.eloSum / g.count).toFixed(2)),
                    },
                    soccer: {
                        goals_per_1k_frames: Number((g.goalsSum / g.count).toFixed(4)),
                    },
                    fish_energy: Number((g.fishEnergySum / g.count).toFixed(2)),
                    births_total: Number((g.birthsSum / g.count).toFixed(2)),
                    deaths_total: Number((g.deathsSum / g.count).toFixed(2)),
                };
            });
    }

    // Determine the starting Elo reference line
    const startingElo = data[0]?.poker?.auto_eval_elo ?? 1200;

    // Identify generation boundary markers for vertical reference lines (only in frames mode)
    const genMarkers: { frame: number; gen: number }[] = [];
    if (xAxisMode === 'frames') {
        for (let i = 1; i < samples.length; i++) {
            if (samples[i].max_generation > samples[i - 1].max_generation) {
                genMarkers.push({
                    frame: samples[i].frame,
                    gen: samples[i].max_generation
                });
            }
        }
    }

    // Styles for the cards and layout
    const gridStyle: React.CSSProperties = {
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
        gap: '16px',
        marginTop: '8px'
    };

    const cardStyle: React.CSSProperties = {
        background: 'var(--card-bg)',
        border: '1px solid var(--card-border)',
        borderRadius: 'var(--radius-md)',
        padding: 'var(--spacing-md)',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        height: '240px'
    };

    const cardHeaderStyle: React.CSSProperties = {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
    };

    const cardTitleStyle: React.CSSProperties = {
        fontSize: '12px',
        fontWeight: 600,
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        color: 'var(--color-text-muted)'
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {/* Toggle Bar */}
            <div style={{ display: 'flex', gap: '8px' }}>
                <button
                    onClick={() => setXAxisMode('frames')}
                    aria-pressed={xAxisMode === 'frames'}
                    style={{
                        padding: '6px 12px',
                        fontSize: '11px',
                        fontWeight: 600,
                        borderRadius: '6px',
                        border: '1px solid',
                        cursor: 'pointer',
                        background: xAxisMode === 'frames' ? 'rgba(6, 182, 212, 0.15)' : 'rgba(30, 41, 59, 0.5)',
                        color: xAxisMode === 'frames' ? '#22d3ee' : 'var(--color-text-muted)',
                        borderColor: xAxisMode === 'frames' ? 'rgba(6, 182, 212, 0.4)' : 'rgba(71, 85, 105, 0.5)',
                        fontFamily: 'var(--font-main)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        transition: 'all 0.2s'
                    }}
                >
                    Frames
                </button>
                <button
                    onClick={() => setXAxisMode('generations')}
                    aria-pressed={xAxisMode === 'generations'}
                    style={{
                        padding: '6px 12px',
                        fontSize: '11px',
                        fontWeight: 600,
                        borderRadius: '6px',
                        border: '1px solid',
                        cursor: 'pointer',
                        background: xAxisMode === 'generations' ? 'rgba(6, 182, 212, 0.15)' : 'rgba(30, 41, 59, 0.5)',
                        color: xAxisMode === 'generations' ? '#22d3ee' : 'var(--color-text-muted)',
                        borderColor: xAxisMode === 'generations' ? 'rgba(6, 182, 212, 0.4)' : 'rgba(71, 85, 105, 0.5)',
                        fontFamily: 'var(--font-main)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        transition: 'all 0.2s'
                    }}
                >
                    Generations
                </button>
            </div>

            {/* Charts Grid */}
            <div style={gridStyle}>
                {/* 1. Poker ELO vs baseline */}
                <div style={cardStyle}>
                    <div style={cardHeaderStyle}>
                        <span style={cardTitleStyle}>♠ Poker ELO (vs Baseline)</span>
                        <TrendBadge
                            values={data.map(d => d.poker?.auto_eval_elo ?? 1200)}
                            formatter={(v) => `${v > 0 ? '+' : ''}${v.toFixed(1)}`}
                        />
                    </div>
                    <div style={{ flex: 1, minHeight: 0 }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart
                                data={data}
                                margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                            >
                                <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
                                <XAxis
                                    dataKey={xAxisMode === 'frames' ? 'frame' : 'max_generation'}
                                    stroke="rgba(255,255,255,0.3)"
                                    fontSize={10}
                                    tickFormatter={(v) => xAxisMode === 'frames' ? `${(v/1000).toFixed(0)}k` : `${v}`}
                                />
                                <YAxis
                                    stroke="rgba(255,255,255,0.3)"
                                    fontSize={10}
                                    domain={['auto', 'auto']}
                                />
                                <Tooltip
                                    content={<CustomTooltip xAxisMode={xAxisMode} />}
                                />
                                <ReferenceLine
                                    y={startingElo}
                                    stroke="var(--color-text-dim)"
                                    strokeDasharray="3 3"
                                    label={{
                                        value: 'starting skill',
                                        position: 'insideBottomLeft',
                                        fill: 'var(--color-text-dim)',
                                        fontSize: 9
                                    }}
                                />
                                {xAxisMode === 'frames' && genMarkers.map((m, idx) => (
                                    <ReferenceLine
                                        key={idx}
                                        x={m.frame}
                                        stroke="rgba(255,255,255,0.15)"
                                        strokeDasharray="2 2"
                                    />
                                ))}
                                <Line
                                    type="monotone"
                                    dataKey="poker.auto_eval_elo"
                                    stroke="var(--color-secondary)"
                                    strokeWidth={2}
                                    name="Poker ELO"
                                    dot={false}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* 2. Soccer goals / 1k frames */}
                <div style={cardStyle}>
                    <div style={cardHeaderStyle}>
                        <span style={cardTitleStyle}>⚽ Soccer Goals per 1k Frames</span>
                        <TrendBadge
                            values={data.map(d => d.soccer?.goals_per_1k_frames ?? 0)}
                            formatter={(v) => `${v > 0 ? '+' : ''}${v.toFixed(2)}`}
                        />
                    </div>
                    <div style={{ flex: 1, minHeight: 0 }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart
                                data={data}
                                margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                            >
                                <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
                                <XAxis
                                    dataKey={xAxisMode === 'frames' ? 'frame' : 'max_generation'}
                                    stroke="rgba(255,255,255,0.3)"
                                    fontSize={10}
                                    tickFormatter={(v) => xAxisMode === 'frames' ? `${(v/1000).toFixed(0)}k` : `${v}`}
                                />
                                <YAxis
                                    stroke="rgba(255,255,255,0.3)"
                                    fontSize={10}
                                    domain={[0, 'auto']}
                                />
                                <Tooltip
                                    content={<CustomTooltip xAxisMode={xAxisMode} />}
                                />
                                {xAxisMode === 'frames' && genMarkers.map((m, idx) => (
                                    <ReferenceLine
                                        key={idx}
                                        x={m.frame}
                                        stroke="rgba(255,255,255,0.15)"
                                        strokeDasharray="2 2"
                                    />
                                ))}
                                <Line
                                    type="monotone"
                                    dataKey="soccer.goals_per_1k_frames"
                                    stroke="var(--color-success)"
                                    strokeWidth={2}
                                    name="Goals/1k Frames"
                                    dot={false}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* 3. Population & Generation */}
                <div style={cardStyle}>
                    <div style={cardHeaderStyle}>
                        <span style={cardTitleStyle}>🐟 Population & Generation</span>
                        <TrendBadge
                            values={data.map(d => d.population)}
                            formatter={(v) => `${v > 0 ? '+' : ''}${v.toFixed(1)}`}
                        />
                    </div>
                    <div style={{ flex: 1, minHeight: 0 }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart
                                data={data}
                                margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                            >
                                <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
                                <XAxis
                                    dataKey={xAxisMode === 'frames' ? 'frame' : 'max_generation'}
                                    stroke="rgba(255,255,255,0.3)"
                                    fontSize={10}
                                    tickFormatter={(v) => xAxisMode === 'frames' ? `${(v/1000).toFixed(0)}k` : `${v}`}
                                />
                                <YAxis
                                    yAxisId="left"
                                    stroke="var(--color-primary)"
                                    fontSize={10}
                                    domain={[0, 'auto']}
                                />
                                <YAxis
                                    yAxisId="right"
                                    orientation="right"
                                    stroke="rgba(255,255,255,0.4)"
                                    fontSize={10}
                                    domain={[0, 'auto']}
                                    tickFormatter={(v) => `G${v}`}
                                />
                                <Tooltip
                                    content={<CustomTooltip xAxisMode={xAxisMode} />}
                                />
                                {xAxisMode === 'frames' && genMarkers.map((m, idx) => (
                                    <ReferenceLine
                                        key={idx}
                                        yAxisId="left"
                                        x={m.frame}
                                        stroke="rgba(255,255,255,0.15)"
                                        strokeDasharray="2 2"
                                    />
                                ))}
                                <Line
                                    yAxisId="left"
                                    type="monotone"
                                    dataKey="population"
                                    stroke="var(--color-primary)"
                                    strokeWidth={2}
                                    name="Population"
                                    dot={false}
                                />
                                {xAxisMode === 'frames' && (
                                    <Line
                                        yAxisId="right"
                                        type="stepAfter"
                                        dataKey="max_generation"
                                        stroke="rgba(255, 255, 255, 0.3)"
                                        strokeDasharray="4 4"
                                        name="Max Gen"
                                        dot={false}
                                    />
                                )}
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>
        </div>
    );
}
