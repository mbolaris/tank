import { ResponsiveContainer, Line, LineChart } from 'recharts';
import { calculateTrend, type XAxisMode } from './trendUtils';

// ---------------------------------------------------------------------------
// Trend badge
// ---------------------------------------------------------------------------

interface TrendBadgeProps {
    values: number[];
    formatter?: (v: number) => string;
}

export function TrendBadge({ values, formatter }: TrendBadgeProps) {
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

// ---------------------------------------------------------------------------
// Chart tooltip
// ---------------------------------------------------------------------------

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
export const CustomTooltip = ({ active, payload, label, xAxisMode, valueFormatter }: CustomTooltipProps) => {
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

export function StatTile({ label, value, sub, subColor, spark, sparkColor }: StatTileProps) {
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

export function ChartCard({ title, subtitle, right, children }: ChartCardProps) {
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

export function LegendKey({ items }: { items: { label: string; color: string }[] }) {
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

// ---------------------------------------------------------------------------
// Readout cards (evolution readout strip)
// ---------------------------------------------------------------------------

export type ReadoutTone = 'positive' | 'neutral' | 'warning' | 'danger';

interface ReadoutCardProps {
    label: string;
    value: string;
    detail: string;
    tone: ReadoutTone;
}

export function ReadoutCard({ label, value, detail, tone }: ReadoutCardProps) {
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
