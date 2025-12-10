import React from 'react';

interface Props {
    bins?: number[];
    binEdges?: number[];
    min?: number;
    max?: number;
    median?: number;
    allowedMin?: number;
    allowedMax?: number;
    width?: number;
    height?: number;
    xLabel?: string;
    yLabel?: string;
}

export default function SizeSummaryGraph({
    bins = [],
    binEdges = [],
    min = 0,
    max = 0,
    median = 0,
    allowedMin = 0,
    allowedMax = 0,
    width = 260,
    height = 72,
    xLabel = 'Adult Size',
    yLabel = 'Count',
}: Props) {
    if (!bins || bins.length === 0) return null;

    const padding = 8;
    const plotW = width - padding * 2;
    const plotH = height - 28; // leave room for legend/labels

    // Use allowed bounds as x-axis range if present, otherwise use min/max
    const xMin = allowedMin && allowedMax && allowedMax > allowedMin ? allowedMin : Math.min(...(binEdges.length ? binEdges : [min, max, allowedMin, allowedMax]));
    const xMax = allowedMin && allowedMax && allowedMax > allowedMin ? allowedMax : Math.max(...(binEdges.length ? binEdges : [min, max, allowedMin, allowedMax]));
    const span = xMax - xMin || 1;

    const maxCount = Math.max(...bins, 1);
    const barWidth = plotW / bins.length;

    const xFor = (v: number) => padding + ((v - xMin) / span) * plotW;

    return (
        <div style={{ width, display: 'flex', flexDirection: 'column', gap: 6 }}>
            <svg width={width} height={plotH + padding + 18}>
                {/* bars */}
                {bins.map((count, i) => {
                    const h = (count / maxCount) * (plotH - 6);
                    const x = padding + i * barWidth + 1;
                    const y = plotH - h - 2;
                    const color = '#60a5fa';
                    return <rect key={i} x={x} y={y} width={Math.max(0, barWidth - 2)} height={h} fill={color} rx={2} ry={2} />;
                })}

                {/* allowed bounds */}
                <line x1={xFor(allowedMin)} x2={xFor(allowedMin)} y1={6} y2={plotH} stroke="rgba(255,255,255,0.12)" strokeDasharray="3 3" />
                <line x1={xFor(allowedMax)} x2={xFor(allowedMax)} y1={6} y2={plotH} stroke="rgba(255,255,255,0.12)" strokeDasharray="3 3" />

                {/* population min/max */}
                <line x1={xFor(min)} x2={xFor(min)} y1={6} y2={plotH} stroke="rgba(34,197,94,0.9)" strokeWidth={1.5} />
                <line x1={xFor(max)} x2={xFor(max)} y1={6} y2={plotH} stroke="rgba(239,68,68,0.9)" strokeWidth={1.5} />

                {/* median marker */}
                <line x1={xFor(median)} x2={xFor(median)} y1={6} y2={plotH} stroke="#f59e0b" strokeWidth={2} strokeLinecap="round" />

                {/* small top labels */}
                <text x={xFor(min)} y={10} fontSize={10} fill="#86efac" textAnchor="middle">min</text>
                <text x={xFor(median)} y={10} fontSize={10} fill="#ffd580" textAnchor="middle">median</text>
                <text x={xFor(max)} y={10} fontSize={10} fill="#fca5a5" textAnchor="middle">max</text>

                {/* x-axis label */}
                <text x={padding + plotW / 2} y={plotH + 14} fontSize={11} fill="var(--color-text-dim)" textAnchor="middle">{xLabel}</text>

                {/* y-axis label (rotated) */}
                <text
                    x={12}
                    y={padding + plotH / 2}
                    fontSize={11}
                    fill="var(--color-text-dim)"
                    textAnchor="middle"
                    transform={`rotate(-90 12 ${padding + plotH / 2})`}
                >
                    {yLabel}
                </text>
            </svg>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 11 }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', color: 'var(--color-text-dim)' }}>
                    <LegendItem color="#f59e0b" label={`Median ${median.toFixed(2)}`} />
                    <LegendItem color="#86efac" label={`Min ${min.toFixed(2)}`} />
                    <LegendItem color="#fca5a5" label={`Max ${max.toFixed(2)}`} />
                </div>
                <div style={{ color: 'var(--color-text-dim)', fontSize: 11 }}>
                    Allowed: {allowedMin.toFixed(2)}-{allowedMax.toFixed(2)}
                </div>
            </div>
        </div>
    );
}

function LegendItem({ color, label }: { color: string; label: string }) {
    return (
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <div style={{ width: 10, height: 10, background: color, borderRadius: 2 }} />
            <div style={{ color: 'var(--color-text-dim)', fontSize: 11 }}>{label}</div>
        </div>
    );
}
