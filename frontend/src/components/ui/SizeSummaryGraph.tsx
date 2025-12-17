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
    const bottomPad = 50; // Increased to make room for labels + title
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

    // Determine if we should show individual bar labels (for discrete traits)
    const showBarLabels = labels && labels.length === bins.length;

    // Format x-axis tick labels for min/max display
    const formatMin = labels && labels.length > 0 && !showBarLabels ? labels[0] : (integerValues ? allowedMin.toFixed(0) : allowedMin.toFixed(2));
    const formatMax = labels && labels.length > 1 && !showBarLabels ? labels[labels.length - 1] : (integerValues ? allowedMax.toFixed(0) : allowedMax.toFixed(2));

    return (
        <div style={{ width, display: 'flex', flexDirection: 'column', gap: 6 }}>
            <svg width={width} height={svgHeight}>
                {/* bars */}
                {bins.map((count, i) => {
                    const h = (count / maxCount) * (plotH - 6);
                    // Center the bar in the slot. Cap width at 18px-2px padding.
                    const slotWidth = barWidth;
                    const visualBarWidth = Math.min(slotWidth - 2, 16);
                    const x = leftPad + i * slotWidth + (slotWidth - visualBarWidth) / 2;
                    const y = topPad + (plotH - h - 2);
                    const color = '#60a5fa';
                    return <rect key={i} x={x} y={y} width={visualBarWidth} height={h} fill={color} rx={2} ry={2} />;
                })}

                {/* allowed bounds (vertical guides) - only show if not using bar labels */}
                {!showBarLabels && (
                    <>
                        <line x1={xFor(allowedMin)} x2={xFor(allowedMin)} y1={topPad} y2={topPad + plotH} stroke="rgba(255,255,255,0.12)" strokeDasharray="3 3" />
                        <line x1={xFor(allowedMax)} x2={xFor(allowedMax)} y1={topPad} y2={topPad + plotH} stroke="rgba(255,255,255,0.12)" strokeDasharray="3 3" />
                    </>
                )}

                {/* x-axis label (positioned clearly below ticks) */}
                <text x={leftPad + plotW / 2} y={topPad + plotH + 42} fontSize={11} fill="var(--color-text-dim)" textAnchor="middle">{xLabel}</text>

                {/* Individual bar labels (for discrete traits) OR min/max labels (for continuous traits) */}
                {showBarLabels ? (
                    // Show label under each bar
                    bins.map((_, i) => {
                        const barCenterX = leftPad + i * barWidth + barWidth / 2;
                        return (
                            <text
                                key={i}
                                x={barCenterX}
                                y={topPad + plotH + 15}
                                fontSize={9}
                                fill="var(--color-text-dim)"
                                textAnchor="middle"
                            >
                                {labels[i]}
                            </text>
                        );
                    })
                ) : (
                    // Show min/max ticks and labels
                    <>
                        <line x1={xFor(allowedMin)} x2={xFor(allowedMin)} y1={topPad + plotH + 4} y2={topPad + plotH + 10} stroke="var(--color-text-dim)" />
                        <line x1={xFor(allowedMax)} x2={xFor(allowedMax)} y1={topPad + plotH + 4} y2={topPad + plotH + 10} stroke="var(--color-text-dim)" />
                        <text x={xFor(allowedMin)} y={topPad + plotH + 20} fontSize={10} fill="var(--color-text-dim)" textAnchor="middle">{formatMin}</text>
                        <text x={xFor(allowedMax)} y={topPad + plotH + 20} fontSize={10} fill="var(--color-text-dim)" textAnchor="middle">{formatMax}</text>
                    </>
                )}

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
