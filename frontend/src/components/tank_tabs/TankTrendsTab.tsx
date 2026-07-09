import { memo, useMemo, useState } from 'react';
import {
    Area,
    Bar,
    CartesianGrid,
    ComposedChart,
    Line,
    LineChart,
    ReferenceLine,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis
} from 'recharts';
import type { MetricsHistory, MetricsSample } from '../../types/simulation';

interface TankTrendsTabProps {
    history: MetricsHistory | null;
}

type XAxisMode = 'frames' | 'generations';

// Healthy-ecosystem thresholds (mirrors CLAUDE.md "Healthy Ecosystem Indicators").
const STABLE_POPULATION = 20; // >20 fish = stable
const HEALTHY_GEN_RATE = 5; // >5 generations per 10k frames
const WARNING_GEN_RATE = 3; // <3 = evolution too slow
const HEALTHY_REPRO_RATIO = 1.2; // births/deaths >120% = growing

// Heritable traits tracked for directional-selection (drift) visualization.
// Order/colors are stable; only keys actually present in the data are drawn.
// Palette validated for the dark surface (#0f172a): CVD-safe adjacent
// separation, 3:1 contrast, dark lightness band.
const TRAIT_SERIES: { key: string; label: string; color: string }[] = [
    { key: 'pursuit_aggression', label: 'Pursuit', color: '#d97706' },
    { key: 'prediction_skill', label: 'Prediction', color: '#8b5cf6' },
    { key: 'hunting_stamina', label: 'Stamina', color: '#059669' },
    { key: 'aggression', label: 'Aggression', color: '#ef4444' },
    { key: 'speed', label: 'Speed', color: '#3b82f6' },
    { key: 'size', label: 'Size', color: '#ec4899' },
];

interface AggregatedPoint {
    frame?: number;
    max_generation: number;
    population: number;
    fish_energy: number;
    births_total: number;
    deaths_total: number;
    poker: { auto_eval_elo: number };
    soccer: { goals_per_1k_frames: number };
    diversity_score: number;
    traits?: Record<string, number>;
    death_causes?: Record<string, number>;
}

interface TrendPoint extends AggregatedPoint {
    births_interval: number;
    deaths_neg: number;
    mean_energy: number;
    // Trait means indexed to their first recorded value, as % change.
    traits_idx?: Record<string, number>;
    death_causes_interval?: Record<string, number>;
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
    const isPositive = delta > 0;

    const palette = isNeutral
        ? { bg: 'rgba(148, 163, 184, 0.15)', fg: '#94a3b8' }
        : isPositive
            ? { bg: 'rgba(74, 222, 128, 0.15)', fg: '#4ade80' }
            : { bg: 'rgba(248, 113, 113, 0.15)', fg: '#f87171' };
    const arrow = isNeutral ? '◆' : isPositive ? '▲' : '▼';

    return (
        <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            padding: '2px 8px',
            borderRadius: '4px',
            fontSize: '10px',
            fontWeight: 600,
            background: palette.bg,
            color: palette.fg,
            fontFamily: 'var(--font-mono)',
            whiteSpace: 'nowrap'
        }}>
            {arrow} {sign}{formatVal} ({isNeutral ? '0.0' : `${isPositive ? '+' : ''}${pct.toFixed(1)}`}%)
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
    valueFormatter?: (name: string, value: number) => string;
}

// Custom Tooltip component for high-quality dark theme styling
const CustomTooltip = ({ active, payload, label, xAxisMode, valueFormatter }: CustomTooltipProps) => {
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
                        display: 'flex',
                        gap: '12px',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        fontFamily: 'var(--font-mono)',
                        marginTop: idx > 0 ? '2px' : 0
                    }}>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: 'var(--color-text-muted)' }}>
                            <span style={{
                                width: '10px',
                                height: '2px',
                                borderRadius: '1px',
                                background: p.color || 'var(--color-text-main)',
                                display: 'inline-block'
                            }} />
                            {p.name}
                        </span>
                        <span style={{ fontWeight: 600, color: 'var(--color-text-main)' }}>
                            {valueFormatter ? valueFormatter(p.name, p.value) : p.value.toLocaleString()}
                        </span>
                    </div>
                ))}
            </div>
        );
    }
    return null;
};

// ---------------------------------------------------------------------------
// Stat tiles (KPI row)
// ---------------------------------------------------------------------------

interface SparklineProps {
    values: number[];
    color: string;
}

function Sparkline({ values, color }: SparklineProps) {
    const data = values.map((v, i) => ({ i, v }));
    return (
        <div style={{ width: '100%', height: '28px' }}>
            <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
                    <Line
                        type="monotone"
                        dataKey="v"
                        stroke={color}
                        strokeWidth={1.5}
                        dot={false}
                        isAnimationActive={false}
                    />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}

interface StatTileProps {
    label: string;
    value: string;
    sub?: string;
    subColor?: string;
    spark?: number[];
    sparkColor?: string;
}

function StatTile({ label, value, sub, subColor, spark, sparkColor }: StatTileProps) {
    return (
        <div style={{
            background: 'var(--card-bg)',
            border: '1px solid var(--card-border)',
            borderRadius: 'var(--radius-md)',
            padding: '10px 14px',
            display: 'flex',
            flexDirection: 'column',
            gap: '4px',
            minWidth: 0
        }}>
            <span style={{
                fontSize: '10px',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                color: 'var(--color-text-muted)',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
            }}>
                {label}
            </span>
            <span style={{
                fontSize: '22px',
                fontWeight: 600,
                color: 'var(--color-text-main)',
                lineHeight: 1.1,
                fontFamily: 'var(--font-main)'
            }}>
                {value}
            </span>
            {sub && (
                <span style={{
                    fontSize: '10px',
                    fontWeight: 600,
                    color: subColor ?? 'var(--color-text-muted)',
                    fontFamily: 'var(--font-mono)',
                    whiteSpace: 'nowrap'
                }}>
                    {sub}
                </span>
            )}
            {spark && spark.length > 1 && (
                <Sparkline values={spark} color={sparkColor ?? 'var(--color-primary)'} />
            )}
        </div>
    );
}

// ---------------------------------------------------------------------------
// Chart card wrapper
// ---------------------------------------------------------------------------

interface ChartCardProps {
    title: string;
    subtitle?: string;
    right?: React.ReactNode;
    children: React.ReactNode;
}

function ChartCard({ title, subtitle, right, children }: ChartCardProps) {
    return (
        <div style={{
            background: 'var(--card-bg)',
            border: '1px solid var(--card-border)',
            borderRadius: 'var(--radius-md)',
            padding: 'var(--spacing-md)',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            height: '250px'
        }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', minWidth: 0 }}>
                    <span style={{
                        fontSize: '12px',
                        fontWeight: 600,
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        color: 'var(--color-text-muted)'
                    }}>
                        {title}
                    </span>
                    {subtitle && (
                        <span style={{ fontSize: '10px', color: 'var(--color-text-dim)' }}>
                            {subtitle}
                        </span>
                    )}
                </div>
                {right}
            </div>
            <div style={{ flex: 1, minHeight: 0 }}>
                {children}
            </div>
        </div>
    );
}

function LegendKey({ items }: { items: { label: string; color: string }[] }) {
    return (
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
            {items.map(item => (
                <span key={item.label} style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontSize: '10px',
                    fontWeight: 600,
                    color: 'var(--color-text-muted)'
                }}>
                    <span style={{
                        width: '10px',
                        height: '3px',
                        borderRadius: '2px',
                        background: item.color,
                        display: 'inline-block'
                    }} />
                    {item.label}
                </span>
            ))}
        </div>
    );
}

type ReadoutTone = 'positive' | 'neutral' | 'warning' | 'danger';

interface ReadoutCardProps {
    label: string;
    value: string;
    detail: string;
    tone: ReadoutTone;
}

function ReadoutCard({ label, value, detail, tone }: ReadoutCardProps) {
    const palette: Record<ReadoutTone, { accent: string; background: string }> = {
        positive: { accent: '#4ade80', background: 'rgba(74, 222, 128, 0.08)' },
        neutral: { accent: '#94a3b8', background: 'rgba(148, 163, 184, 0.08)' },
        warning: { accent: '#fbbf24', background: 'rgba(251, 191, 36, 0.08)' },
        danger: { accent: '#f87171', background: 'rgba(248, 113, 113, 0.08)' },
    };
    const colors = palette[tone];

    return (
        <div style={{
            padding: '12px 14px',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--card-border)',
            borderTop: `2px solid ${colors.accent}`,
            background: `linear-gradient(135deg, ${colors.background}, var(--card-bg))`,
            minWidth: 0,
        }}>
            <div style={{
                color: 'var(--color-text-dim)',
                fontSize: '10px',
                fontWeight: 700,
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
                marginBottom: '5px',
            }}>
                {label}
            </div>
            <div style={{
                color: colors.accent,
                fontSize: '15px',
                fontWeight: 700,
                lineHeight: 1.2,
                marginBottom: '5px',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
            }}>
                {value}
            </div>
            <div style={{
                color: 'var(--color-text-muted)',
                fontSize: '11px',
                lineHeight: 1.35,
            }}>
                {detail}
            </div>
        </div>
    );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

function TankTrendsTabComponent({ history }: TankTrendsTabProps) {
    const [xAxisMode, setXAxisMode] = useState<XAxisMode>('generations');

    const samples = history?.samples;

    const processedData: TrendPoint[] = useMemo(() => {
        if (!samples || samples.length === 0) return [];

        // Aggregate samples by max_generation if in generations mode
        let data: (MetricsSample | AggregatedPoint)[] = samples;
        if (xAxisMode === 'generations') {
            const genMap: Record<number, {
                count: number;
                populationSum: number;
                eloSum: number;
                goalsSum: number;
                fishEnergySum: number;
                birthsSum: number;
                deathsSum: number;
                diversitySum: number;
                traitsSum: Record<string, number>;
                traitsCount: Record<string, number>;
                deathCausesSum: Record<string, number>;
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
                        diversitySum: 0,
                        traitsSum: {},
                        traitsCount: {},
                        deathCausesSum: {},
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
                g.diversitySum += s.diversity_score ?? 0;
                if (s.traits) {
                    for (const [k, v] of Object.entries(s.traits)) {
                        g.traitsSum[k] = (g.traitsSum[k] ?? 0) + v;
                        g.traitsCount[k] = (g.traitsCount[k] ?? 0) + 1;
                    }
                }
                if (s.death_causes) {
                    for (const [k, v] of Object.entries(s.death_causes)) {
                        g.deathCausesSum[k] = (g.deathCausesSum[k] ?? 0) + v;
                    }
                }
            });

            data = Object.keys(genMap)
                .map(Number)
                .sort((a, b) => a - b)
                .map(gen => {
                    const g = genMap[gen];
                    return {
                        max_generation: gen,
                        population: Number((g.populationSum / g.count).toFixed(2)),
                        poker: { auto_eval_elo: Number((g.eloSum / g.count).toFixed(2)) },
                        soccer: { goals_per_1k_frames: Number((g.goalsSum / g.count).toFixed(4)) },
                        fish_energy: Number((g.fishEnergySum / g.count).toFixed(2)),
                        births_total: Number((g.birthsSum / g.count).toFixed(2)),
                        deaths_total: Number((g.deathsSum / g.count).toFixed(2)),
                        diversity_score: Number((g.diversitySum / g.count).toFixed(4)),
                        traits: Object.fromEntries(
                            Object.keys(g.traitsSum).map(k => [
                                k,
                                Number((g.traitsSum[k] / g.traitsCount[k]).toFixed(5)),
                            ])
                        ),
                        death_causes: Object.fromEntries(
                            Object.keys(g.deathCausesSum).map(k => [
                                k,
                                Number((g.deathCausesSum[k] / g.count).toFixed(2)),
                            ])
                        ),
                    };
                });
        }

        // Baseline for trait indexing: first non-zero value seen per trait, so
        // drift reads as "% change since start" on one comparable axis.
        const traitBaselines: Record<string, number> = {};
        data.forEach(d => {
            if (!d.traits) return;
            for (const [k, v] of Object.entries(d.traits)) {
                if (traitBaselines[k] === undefined && v !== 0) traitBaselines[k] = v;
            }
        });

        // Interval deltas (births/deaths per sample or per generation) and per-fish energy
        return data.map((d, idx) => {
            const prev = data[idx - 1];
            const birthsInterval = prev ? Math.max(0, d.births_total - prev.births_total) : 0;
            const deathsInterval = prev ? Math.max(0, d.deaths_total - prev.deaths_total) : 0;

            let traitsIdx: Record<string, number> | undefined;
            if (d.traits) {
                traitsIdx = {};
                for (const [k, v] of Object.entries(d.traits)) {
                    const base = traitBaselines[k];
                    if (base) traitsIdx[k] = Number((((v - base) / base) * 100).toFixed(2));
                }
            }

            const causesInterval: Record<string, number> = {};
            const keys = ['starvation', 'old_age', 'predation', 'migration', 'unknown'];
            keys.forEach(k => {
                const curVal = d.death_causes?.[k] ?? 0;
                const prevVal = prev?.death_causes?.[k] ?? 0;
                causesInterval[k] = Math.max(0, curVal - prevVal);
            });

            return {
                ...d,
                births_interval: birthsInterval,
                deaths_neg: -deathsInterval,
                mean_energy: d.population > 0 ? Number((d.fish_energy / d.population).toFixed(1)) : 0,
                traits_idx: traitsIdx,
                death_causes_interval: causesInterval,
            };
        });
    }, [samples, xAxisMode]);

    // Handle null or empty history state
    if (!history || !samples || samples.length === 0) {
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

    // --------------------------------------------------------------------
    // Headline stats (always computed over the raw frame-ordered samples so
    // the KPI row doesn't change meaning when the x-axis toggle flips)
    // --------------------------------------------------------------------
    const first = samples[0];
    const last = samples[samples.length - 1];
    const frameSpan = last.frame - first.frame;

    // Generation rate per 10k frames over the visible history
    const genRate = frameSpan > 0
        ? ((last.max_generation - first.max_generation) / frameSpan) * 10000
        : 0;
    const genRateColor = genRate >= HEALTHY_GEN_RATE
        ? 'var(--color-success)'
        : genRate < WARNING_GEN_RATE ? 'var(--color-danger)' : 'var(--color-warning)';

    // Reproduction ratio (births vs deaths) over the most recent quarter of history
    const recentStart = samples[Math.max(0, samples.length - Math.max(2, Math.floor(samples.length / 4)))];
    const recentBirths = last.births_total - recentStart.births_total;
    const recentDeaths = last.deaths_total - recentStart.deaths_total;
    const reproRatio = recentDeaths > 0 ? recentBirths / recentDeaths : null;
    const reproLabel = reproRatio === null
        ? (recentBirths > 0 ? '∞' : '—')
        : `${reproRatio.toFixed(2)}×`;
    const reproColor = reproRatio === null
        ? 'var(--color-text-muted)'
        : reproRatio >= HEALTHY_REPRO_RATIO
            ? 'var(--color-success)'
            : reproRatio < 1 ? 'var(--color-danger)' : 'var(--color-warning)';

    const sparkWindow = samples.slice(-40);
    const popTrend = calculateTrend(samples.map(s => s.population));
    const divTrend = calculateTrend(samples.map(s => s.diversity_score ?? 0));

    // --------------------------------------------------------------------
    // Chart-level derived data
    // --------------------------------------------------------------------

    // Identify generation boundary markers for vertical reference lines (only in frames mode)
    const genMarkers: { frame: number; gen: number }[] = [];
    if (xAxisMode === 'frames') {
        for (let i = 1; i < samples.length; i++) {
            if (samples[i].max_generation > samples[i - 1].max_generation) {
                genMarkers.push({ frame: samples[i].frame, gen: samples[i].max_generation });
            }
        }
    }

    // Only draw trait lines for keys that actually appear (pre-schema-v2 history
    // has no trait means, so the card is hidden entirely in that case).
    const presentTraitSeries = TRAIT_SERIES.filter(t =>
        processedData.some(d => d.traits_idx && d.traits_idx[t.key] !== undefined)
    );
    const hasTraitData = presentTraitSeries.length > 0;

    // A small diagnosis layer makes the charts easier to read at a glance. It
    // deliberately treats trait drift as the selection signal: generation
    // count alone can rise through churn without improving the population.
    const strongestTrait = presentTraitSeries
        .map(trait => ({
            ...trait,
            drift: processedData[processedData.length - 1]?.traits_idx?.[trait.key] ?? 0,
        }))
        .sort((a, b) => Math.abs(b.drift) - Math.abs(a.drift))[0];
    const strongestDrift = strongestTrait?.drift ?? 0;
    const selectionReadout = !hasTraitData
        ? { value: 'Waiting for signal', detail: 'Trait telemetry is not in this history yet.', tone: 'neutral' as ReadoutTone }
        : samples.length < 4
            ? { value: 'Collecting signal', detail: 'A few more samples will make drift meaningful.', tone: 'neutral' as ReadoutTone }
            : Math.abs(strongestDrift) >= 5
                ? {
                    value: 'Directional drift',
                    detail: `${strongestTrait?.label ?? 'Trait'} is ${strongestDrift >= 0 ? 'up' : 'down'} ${Math.abs(strongestDrift).toFixed(1)}% since the first sample.`,
                    tone: 'positive' as ReadoutTone,
                }
                : {
                    value: 'Mostly churn',
                    detail: 'Trait means are under 5% from start; turnover is not yet a clear quality signal.',
                    tone: 'warning' as ReadoutTone,
                };

    const diversityValue = last.diversity_score ?? 0;
    const diversityReadout = diversityValue >= 0.15
        ? {
            value: 'Room to explore',
            detail: `Diversity is ${(diversityValue * 100).toFixed(0)}% — above the 15% healthy floor.`,
            tone: 'positive' as ReadoutTone,
        }
        : diversityValue >= 0.1
            ? {
                value: 'Watch convergence',
                detail: `Diversity is ${(diversityValue * 100).toFixed(0)}% — keep an eye on the next generations.`,
                tone: 'warning' as ReadoutTone,
            }
            : {
                value: 'Converging',
                detail: `Diversity is only ${(diversityValue * 100).toFixed(0)}% — novelty may be getting squeezed out.`,
                tone: 'danger' as ReadoutTone,
            };

    const momentumReadout = {
        value: `${genRate.toFixed(1)} gen / 10k`,
        detail: genRate >= HEALTHY_GEN_RATE
            ? 'Fast turnover; check trait drift before calling it progress.'
            : genRate >= WARNING_GEN_RATE
                ? 'Moderate turnover; the trend needs more runway.'
                : 'Slow turnover; this history may be too short for selection to act.',
        tone: genRate >= HEALTHY_GEN_RATE
            ? 'positive' as ReadoutTone
            : genRate < WARNING_GEN_RATE
                ? 'danger' as ReadoutTone
                : 'warning' as ReadoutTone,
    };

    // Poker/soccer charts only earn a slot when those systems have produced signal;
    // otherwise they're flat lines crowding out the ecosystem story.
    const hasPokerSignal = samples.some(s => (s.poker?.total_games ?? 0) > 0);
    const hasSoccerSignal = (last.soccer?.goals_total ?? 0) > 0;

    const startingElo = processedData[0]?.poker?.auto_eval_elo ?? 1200;

    const xAxisProps = {
        dataKey: xAxisMode === 'frames' ? 'frame' : 'max_generation',
        stroke: 'rgba(255,255,255,0.3)',
        fontSize: 10,
        tickFormatter: (v: number) => xAxisMode === 'frames' ? `${(v / 1000).toFixed(0)}k` : `${v}`,
    } as const;

    const chartMargin = { top: 10, right: 10, left: -20, bottom: 0 };
    const gridStroke = 'rgba(255,255,255,0.05)';
    const genMarkerLines = (yAxisId?: string) => (
        xAxisMode === 'frames' && genMarkers.map((m, idx) => (
            <ReferenceLine
                key={`gen-${idx}`}
                {...(yAxisId ? { yAxisId } : {})}
                x={m.frame}
                stroke="rgba(255,255,255,0.12)"
                strokeDasharray="2 2"
            />
        ))
    );

    const toggleButtonStyle = (active: boolean): React.CSSProperties => ({
        padding: '6px 12px',
        fontSize: '11px',
        fontWeight: 600,
        borderRadius: '6px',
        border: '1px solid',
        cursor: 'pointer',
        background: active ? 'rgba(6, 182, 212, 0.15)' : 'rgba(30, 41, 59, 0.5)',
        color: active ? '#22d3ee' : 'var(--color-text-muted)',
        borderColor: active ? 'rgba(6, 182, 212, 0.4)' : 'rgba(71, 85, 105, 0.5)',
        fontFamily: 'var(--font-main)',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        transition: 'all 0.2s'
    });

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{
                padding: '14px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--card-border)',
                background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.08), var(--card-bg) 45%)',
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '12px', marginBottom: '10px', flexWrap: 'wrap' }}>
                    <div>
                        <div style={{ color: 'var(--color-text-main)', fontSize: '13px', fontWeight: 700 }}>
                            Evolution readout
                        </div>
                        <div style={{ color: 'var(--color-text-muted)', fontSize: '11px', marginTop: '3px' }}>
                            Fast generations are not automatically better generations — trait drift is the quality signal.
                        </div>
                    </div>
                    <span style={{ color: 'var(--color-text-dim)', fontSize: '10px', fontFamily: 'var(--font-mono)' }}>
                        {frameSpan.toLocaleString()} frames observed
                    </span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(175px, 1fr))', gap: '8px' }}>
                    <ReadoutCard label="Selection" {...selectionReadout} />
                    <ReadoutCard label="Diversity" {...diversityReadout} />
                    <ReadoutCard label="Momentum" {...momentumReadout} />
                </div>
            </div>

            {/* Toggle Bar */}
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <button
                    onClick={() => setXAxisMode('frames')}
                    aria-pressed={xAxisMode === 'frames'}
                    style={toggleButtonStyle(xAxisMode === 'frames')}
                >
                    Frames
                </button>
                <button
                    onClick={() => setXAxisMode('generations')}
                    aria-pressed={xAxisMode === 'generations'}
                    style={toggleButtonStyle(xAxisMode === 'generations')}
                >
                    Generations
                </button>
                <span style={{
                    marginLeft: 'auto',
                    fontSize: '10px',
                    color: 'var(--color-text-dim)',
                    fontFamily: 'var(--font-mono)'
                }}>
                    {samples.length.toLocaleString()} samples · every {history.sample_interval_frames.toLocaleString()} frames
                </span>
            </div>

            {/* KPI Row */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
                gap: '12px'
            }}>
                <StatTile
                    label="Generation"
                    value={`G${last.max_generation}`}
                    sub={`${genRate.toFixed(1)} / 10k frames`}
                    subColor={genRateColor}
                    spark={sparkWindow.map(s => s.max_generation)}
                    sparkColor="#94a3b8"
                />
                <StatTile
                    label="Population"
                    value={`${last.population}`}
                    sub={`${popTrend.delta >= 0 ? '+' : ''}${popTrend.delta.toFixed(1)} vs start`}
                    subColor={last.population >= STABLE_POPULATION ? 'var(--color-success)' : 'var(--color-danger)'}
                    spark={sparkWindow.map(s => s.population)}
                    sparkColor="#06b6d4"
                />
                <StatTile
                    label="Births : Deaths (recent)"
                    value={reproLabel}
                    sub={reproRatio === null ? 'no recent deaths' : reproRatio >= 1 ? 'growing' : 'declining'}
                    subColor={reproColor}
                    spark={sparkWindow.map(s => s.births_total - s.deaths_total)}
                    sparkColor="#059669"
                />
                <StatTile
                    label="Diversity"
                    value={(last.diversity_score ?? 0).toFixed(2)}
                    sub={`${divTrend.delta >= 0 ? '+' : ''}${divTrend.delta.toFixed(3)} vs start`}
                    subColor={Math.abs(divTrend.delta) < 0.005
                        ? 'var(--color-text-muted)'
                        : divTrend.delta > 0 ? 'var(--color-success)' : 'var(--color-warning)'}
                    spark={sparkWindow.map(s => s.diversity_score ?? 0)}
                    sparkColor="#8b5cf6"
                />
                <StatTile
                    label="Starvation Rate"
                    value={`${(() => {
                        const starvationCount = last.death_causes?.starvation ?? 0;
                        const totalDeathCount = Object.values(last.death_causes ?? {}).reduce((a, b) => a + b, 0);
                        return totalDeathCount > 0 ? ((starvationCount / totalDeathCount) * 100).toFixed(1) : '0.0';
                    })()}%`}
                    sub={`${(last.death_causes?.starvation ?? 0).toLocaleString()} / ${Object.values(last.death_causes ?? {}).reduce((a, b) => a + b, 0).toLocaleString()} deaths`}
                    subColor={(() => {
                        const starvationCount = last.death_causes?.starvation ?? 0;
                        const totalDeathCount = Object.values(last.death_causes ?? {}).reduce((a, b) => a + b, 0);
                        const starvationPct = totalDeathCount > 0 ? (starvationCount / totalDeathCount) * 100 : 0;
                        return starvationPct >= 90 ? 'var(--color-danger)' : starvationPct < 80 ? 'var(--color-success)' : 'var(--color-warning)';
                    })()}
                    spark={sparkWindow.map(s => {
                        const sc = s.death_causes?.starvation ?? 0;
                        const tc = Object.values(s.death_causes ?? {}).reduce((a, b) => a + b, 0);
                        return tc > 0 ? (sc / tc) * 100 : 0;
                    })}
                    sparkColor="#ef4444"
                />
            </div>

            {/* Charts Grid */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(min(450px, 100%), 1fr))',
                gap: '16px'
            }}>
                {/* Population */}
                <ChartCard
                    title="🐟 Population"
                    subtitle={`stable above ${STABLE_POPULATION} fish`}
                    right={<TrendBadge
                        values={processedData.map(d => d.population)}
                        formatter={(v) => v.toFixed(1)}
                    />}
                >
                    <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={processedData} margin={chartMargin}>
                            <CartesianGrid stroke={gridStroke} vertical={false} />
                            <XAxis {...xAxisProps} />
                            <YAxis stroke="rgba(255,255,255,0.3)" fontSize={10} domain={[0, 'auto']} />
                            <Tooltip content={<CustomTooltip xAxisMode={xAxisMode} />} />
                            <ReferenceLine
                                y={STABLE_POPULATION}
                                stroke="rgba(148,163,184,0.5)"
                                strokeDasharray="3 3"
                                label={{
                                    value: 'stable floor',
                                    position: 'insideBottomLeft',
                                    fill: 'var(--color-text-dim)',
                                    fontSize: 9
                                }}
                            />
                            {genMarkerLines()}
                            <Area
                                type="monotone"
                                dataKey="population"
                                stroke="#06b6d4"
                                strokeWidth={2}
                                fill="#06b6d4"
                                fillOpacity={0.1}
                                name="Population"
                                dot={false}
                                isAnimationActive={false}
                            />
                        </ComposedChart>
                    </ResponsiveContainer>
                </ChartCard>

                {/* Births vs Deaths (diverging) */}
                <ChartCard
                    title="🐣 Births vs Deaths"
                    subtitle={xAxisMode === 'frames' ? 'per sample interval · asymmetry = net growth' : 'per generation · asymmetry = net growth'}
                    right={<LegendKey items={[
                        { label: 'Births', color: '#059669' },
                        { label: 'Deaths', color: '#ef4444' },
                    ]} />}
                >
                    <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={processedData} margin={chartMargin} stackOffset="sign">
                            <CartesianGrid stroke={gridStroke} vertical={false} />
                            <XAxis {...xAxisProps} />
                            <YAxis
                                stroke="rgba(255,255,255,0.3)"
                                fontSize={10}
                                tickFormatter={(v: number) => `${Math.abs(v)}`}
                            />
                            <Tooltip
                                content={<CustomTooltip
                                    xAxisMode={xAxisMode}
                                    valueFormatter={(_name, v) => Math.abs(v).toLocaleString()}
                                />}
                            />
                            <ReferenceLine y={0} stroke="rgba(255,255,255,0.25)" />
                            {genMarkerLines()}
                            <Bar
                                dataKey="births_interval"
                                stackId="bd"
                                fill="#059669"
                                name="Births"
                                maxBarSize={24}
                                radius={[3, 3, 0, 0]}
                                isAnimationActive={false}
                            />
                            <Bar
                                dataKey="deaths_neg"
                                stackId="bd"
                                fill="#ef4444"
                                name="Deaths"
                                maxBarSize={24}
                                radius={[0, 0, 3, 3]}
                                isAnimationActive={false}
                            />
                        </ComposedChart>
                    </ResponsiveContainer>
                </ChartCard>

                {/* Mortality Causes Trend */}
                <ChartCard
                    title="☠️ Mortality Causes"
                    subtitle="deaths per interval by cause"
                    right={<LegendKey items={[
                        { label: 'Starvation', color: '#ef4444' },
                        { label: 'Old Age', color: '#22c55e' },
                        { label: 'Predation', color: '#fb923c' },
                        { label: 'Migration', color: '#3b82f6' },
                    ]} />}
                >
                    <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={processedData} margin={chartMargin}>
                            <CartesianGrid stroke={gridStroke} vertical={false} />
                            <XAxis {...xAxisProps} />
                            <YAxis stroke="rgba(255,255,255,0.3)" fontSize={10} domain={[0, 'auto']} />
                            <Tooltip content={<CustomTooltip xAxisMode={xAxisMode} />} />
                            {genMarkerLines()}
                            <Area
                                type="monotone"
                                dataKey="death_causes_interval.starvation"
                                stroke="#ef4444"
                                strokeWidth={1.5}
                                fill="#ef4444"
                                fillOpacity={0.1}
                                name="Starvation"
                                dot={false}
                                stackId="deaths"
                                isAnimationActive={false}
                            />
                            <Area
                                type="monotone"
                                dataKey="death_causes_interval.old_age"
                                stroke="#22c55e"
                                strokeWidth={1.5}
                                fill="#22c55e"
                                fillOpacity={0.1}
                                name="Old Age"
                                dot={false}
                                stackId="deaths"
                                isAnimationActive={false}
                            />
                            <Area
                                type="monotone"
                                dataKey="death_causes_interval.predation"
                                stroke="#fb923c"
                                strokeWidth={1.5}
                                fill="#fb923c"
                                fillOpacity={0.1}
                                name="Predation"
                                dot={false}
                                stackId="deaths"
                                isAnimationActive={false}
                            />
                            <Area
                                type="monotone"
                                dataKey="death_causes_interval.migration"
                                stroke="#3b82f6"
                                strokeWidth={1.5}
                                fill="#3b82f6"
                                fillOpacity={0.1}
                                name="Migration"
                                dot={false}
                                stackId="deaths"
                                isAnimationActive={false}
                            />
                        </ComposedChart>
                    </ResponsiveContainer>
                </ChartCard>

                {/* Trait Selection: population trait means indexed to their starting
                    value, so directional selection reads as a slope away from 0%
                    on one comparable axis. Hidden when no trait data is present. */}
                {hasTraitData && (
                    <ChartCard
                        title="Trait drift · selection signal"
                        subtitle="population mean indexed to first sample · ≥5% is a directional signal"
                        right={<LegendKey items={presentTraitSeries} />}
                    >
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={processedData} margin={chartMargin}>
                                <CartesianGrid stroke={gridStroke} vertical={false} />
                                <XAxis {...xAxisProps} />
                                <YAxis
                                    stroke="rgba(255,255,255,0.3)"
                                    fontSize={10}
                                    domain={['auto', 'auto']}
                                    tickFormatter={(v: number) => `${v > 0 ? '+' : ''}${v}%`}
                                />
                                <Tooltip
                                    content={<CustomTooltip
                                        xAxisMode={xAxisMode}
                                        valueFormatter={(_name, v) => `${v > 0 ? '+' : ''}${v.toFixed(1)}%`}
                                    />}
                                />
                                <ReferenceLine y={0} stroke="rgba(255,255,255,0.18)" />
                                {genMarkerLines()}
                                {presentTraitSeries.map(t => (
                                    <Line
                                        key={t.key}
                                        type="monotone"
                                        dataKey={`traits_idx.${t.key}`}
                                        stroke={t.color}
                                        strokeWidth={1.5}
                                        name={t.label}
                                        dot={false}
                                        connectNulls
                                        isAnimationActive={false}
                                    />
                                ))}
                            </LineChart>
                        </ResponsiveContainer>
                    </ChartCard>
                )}

                {/* Diversity */}
                <ChartCard
                    title="🌈 Genetic/Algorithm Diversity"
                    right={<TrendBadge
                        values={processedData.map(d => d.diversity_score ?? 0)}
                        formatter={(v) => v.toFixed(3)}
                    />}
                >
                    <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={processedData} margin={chartMargin}>
                            <CartesianGrid stroke={gridStroke} vertical={false} />
                            <XAxis {...xAxisProps} />
                            <YAxis stroke="rgba(255,255,255,0.3)" fontSize={10} domain={[0, 1]} />
                            <Tooltip content={<CustomTooltip xAxisMode={xAxisMode} />} />
                            {genMarkerLines()}
                            <Area
                                type="monotone"
                                dataKey="diversity_score"
                                stroke="#8b5cf6"
                                strokeWidth={2}
                                fill="#8b5cf6"
                                fillOpacity={0.1}
                                name="Diversity"
                                dot={false}
                                isAnimationActive={false}
                            />
                        </ComposedChart>
                    </ResponsiveContainer>
                </ChartCard>

                {/* Average Fish Energy */}
                <ChartCard
                    title="⚡ Average Fish Energy"
                    right={<TrendBadge
                        values={processedData.map(d => d.mean_energy)}
                        formatter={(v) => `${v.toFixed(0)}⚡`}
                    />}
                >
                    <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={processedData} margin={chartMargin}>
                            <CartesianGrid stroke={gridStroke} vertical={false} />
                            <XAxis {...xAxisProps} />
                            <YAxis stroke="rgba(255,255,255,0.3)" fontSize={10} domain={['auto', 'auto']} />
                            <Tooltip content={<CustomTooltip xAxisMode={xAxisMode} />} />
                            {genMarkerLines()}
                            <Area
                                type="monotone"
                                dataKey="mean_energy"
                                stroke="#f59e0b"
                                strokeWidth={2}
                                fill="#f59e0b"
                                fillOpacity={0.1}
                                name="Avg Energy"
                                dot={false}
                                isAnimationActive={false}
                            />
                        </ComposedChart>
                    </ResponsiveContainer>
                </ChartCard>

                {/* Poker ELO — only when auto-evaluation has actually played games */}
                {hasPokerSignal && (
                    <ChartCard
                        title="♠ Poker ELO"
                        subtitle="vs frozen baseline opponent"
                        right={<TrendBadge
                            values={processedData.map(d => d.poker?.auto_eval_elo ?? 1200)}
                            formatter={(v) => v.toFixed(1)}
                        />}
                    >
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={processedData} margin={chartMargin}>
                                <CartesianGrid stroke={gridStroke} vertical={false} />
                                <XAxis {...xAxisProps} />
                                <YAxis stroke="rgba(255,255,255,0.3)" fontSize={10} domain={['auto', 'auto']} />
                                <Tooltip content={<CustomTooltip xAxisMode={xAxisMode} />} />
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
                                {genMarkerLines()}
                                <Line
                                    type="monotone"
                                    dataKey="poker.auto_eval_elo"
                                    stroke="#8b5cf6"
                                    strokeWidth={2}
                                    name="Poker ELO"
                                    dot={false}
                                    isAnimationActive={false}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </ChartCard>
                )}

                {/* Soccer — only when goals have actually been scored */}
                {hasSoccerSignal && (
                    <ChartCard
                        title="⚽ Soccer Goals per 1k Frames"
                        right={<TrendBadge
                            values={processedData.map(d => d.soccer?.goals_per_1k_frames ?? 0)}
                            formatter={(v) => v.toFixed(2)}
                        />}
                    >
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={processedData} margin={chartMargin}>
                                <CartesianGrid stroke={gridStroke} vertical={false} />
                                <XAxis {...xAxisProps} />
                                <YAxis stroke="rgba(255,255,255,0.3)" fontSize={10} domain={[0, 'auto']} />
                                <Tooltip content={<CustomTooltip xAxisMode={xAxisMode} />} />
                                {genMarkerLines()}
                                <Line
                                    type="monotone"
                                    dataKey="soccer.goals_per_1k_frames"
                                    stroke="#059669"
                                    strokeWidth={2}
                                    name="Goals/1k Frames"
                                    dot={false}
                                    isAnimationActive={false}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </ChartCard>
                )}
            </div>
        </div>
    );
}

// Memoized: the Trends tab is a pure function of `history`, whose reference only
// changes when a new sample is appended (every sample_interval_frames). Without
// this it re-renders and rebuilds every chart over the full sample buffer on
// every WebSocket frame, which drags the whole UI.
export const TankTrendsTab = memo(TankTrendsTabComponent);
