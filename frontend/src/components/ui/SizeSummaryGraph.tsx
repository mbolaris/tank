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
    integerValues?: boolean;
    /** Optional labels to display for discrete x-axis values (e.g., pattern names) */
    labels?: string[];
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
    integerValues = false,
    labels,
}: Props) {
    if (!bins || bins.length === 0) return null;

    // Use asymmetric padding so axis labels and tick labels don't get clipped
    const leftPad = 28;
    const rightPad = 12;
    const topPad = 8;
    const bottomPad = 36; // leave room for x-axis label and tick labels
    const plotW = Math.max(16, width - leftPad - rightPad);
    const plotH = Math.max(12, height - topPad - bottomPad);

    // Use allowed bounds as x-axis range if present, otherwise use min/max
    const xMin = allowedMin && allowedMax && allowedMax > allowedMin ? allowedMin : Math.min(...(binEdges.length ? binEdges : [min, max, allowedMin, allowedMax]));
    const xMax = allowedMin && allowedMax && allowedMax > allowedMin ? allowedMax : Math.max(...(binEdges.length ? binEdges : [min, max, allowedMin, allowedMax]));
    const span = xMax - xMin || 1;

    const maxCount = Math.max(...bins, 1);
    const barWidth = Math.max(8, plotW / bins.length);

    const xFor = (v: number) => {
        const rel = leftPad + ((v - xMin) / span) * plotW;
        return Math.min(leftPad + plotW, Math.max(leftPad, isFinite(rel) ? rel : leftPad));
    };

    const svgHeight = topPad + plotH + bottomPad;

    // Format x-axis tick labels
    const formatMin = labels && labels.length > 0 ? labels[0] : (integerValues ? allowedMin.toFixed(0) : allowedMin.toFixed(2));
    const formatMax = labels && labels.length > 1 ? labels[labels.length - 1] : (integerValues ? allowedMax.toFixed(0) : allowedMax.toFixed(2));

    return (
        <div style={{ width, display: 'flex', flexDirection: 'column', gap: 6 }}>
            <svg width={width} height={svgHeight}>
                {/* bars */}
                {bins.map((count, i) => {
                    const h = (count / maxCount) * (plotH - 6);
                    const x = leftPad + i * barWidth + Math.max(1, (barWidth - Math.min(barWidth, 18)) / 2);
                    const y = topPad + (plotH - h - 2);
                    const color = '#60a5fa';
                    return <rect key={i} x={x} y={y} width={Math.max(0, barWidth - 2)} height={h} fill={color} rx={2} ry={2} />;
                })}

                {/* allowed bounds (vertical guides) */}
                <line x1={xFor(allowedMin)} x2={xFor(allowedMin)} y1={topPad} y2={topPad + plotH} stroke="rgba(255,255,255,0.12)" strokeDasharray="3 3" />
                <line x1={xFor(allowedMax)} x2={xFor(allowedMax)} y1={topPad} y2={topPad + plotH} stroke="rgba(255,255,255,0.12)" strokeDasharray="3 3" />

                {/* x-axis label (positioned clearly below ticks) */}
                <text x={leftPad + plotW / 2} y={topPad + plotH + 28} fontSize={11} fill="var(--color-text-dim)" textAnchor="middle">{xLabel}</text>

                {/* allowed range ticks and labels on x-axis (labels slightly above the x-axis label) */}
                <line x1={xFor(allowedMin)} x2={xFor(allowedMin)} y1={topPad + plotH + 4} y2={topPad + plotH + 10} stroke="var(--color-text-dim)" />
                <line x1={xFor(allowedMax)} x2={xFor(allowedMax)} y1={topPad + plotH + 4} y2={topPad + plotH + 10} stroke="var(--color-text-dim)" />
                <text x={xFor(allowedMin)} y={topPad + plotH + 20} fontSize={10} fill="var(--color-text-dim)" textAnchor="middle">{formatMin}</text>
                <text x={xFor(allowedMax)} y={topPad + plotH + 20} fontSize={10} fill="var(--color-text-dim)" textAnchor="middle">{formatMax}</text>

                {/* y-axis label (rotated) */}
                <text
                    x={leftPad - 12}
                    y={topPad + plotH / 2}
                    fontSize={11}
                    fill="var(--color-text-dim)"
                    textAnchor="middle"
                    transform={`rotate(-90 ${leftPad - 12} ${topPad + plotH / 2})`}
                >
                    {yLabel}
                </text>
            </svg>

            <div style={{ height: 6 }} />
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
