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
    theme?: 'physical' | 'behavioral';
    // Meta stats
    mutationRateMean?: number;
    mutationRateStd?: number;
    mutationStrengthMean?: number;
    mutationStrengthStd?: number;
    hgtProbMean?: number;
    hgtProbStd?: number;
}

export default function SizeSummaryGraph({
    bins = [],
    binEdges = [],
    min = 0,
    max = 0,
    median,
    allowedMin = 0,
    allowedMax = 0,
    width = 260,
    height = 72,
    xLabel = 'Adult Size',
    yLabel = 'Count',
    integerValues = false,
    labels,
    theme = 'physical',
    mutationRateMean,
    mutationRateStd,
    mutationStrengthMean,
    mutationStrengthStd,
    hgtProbMean,
    hgtProbStd,
}: Props) {
    if (!bins || bins.length === 0) return null;

    // Use asymmetric padding so axis labels and tick labels don't get clipped
    const leftPad = 28;
    const rightPad = 12;
    const topPad = 12;
    const bottomPad = 48;
    const plotW = Math.max(16, width - leftPad - rightPad);
    const plotH = Math.max(12, height - topPad - bottomPad);

    // Use allowed bounds as x-axis range if present, otherwise use min/max
    const xMin = allowedMin && allowedMax && allowedMax > allowedMin ? allowedMin : Math.min(...(binEdges.length ? binEdges : [min, max, allowedMin, allowedMax]));
    const xMax = allowedMin && allowedMax && allowedMax > allowedMin ? allowedMax : Math.max(...(binEdges.length ? binEdges : [min, max, allowedMin, allowedMax]));
    const span = xMax - xMin || 1;

    const totalCount = bins.reduce((a, b) => a + b, 0);
    const maxCount = Math.max(...bins, 1);
    const barWidth = Math.max(6, plotW / bins.length);

    const xFor = (v: number) => {
        const rel = leftPad + ((v - xMin) / span) * plotW;
        return Math.min(leftPad + plotW, Math.max(leftPad, isFinite(rel) ? rel : leftPad));
    };

    const svgHeight = topPad + plotH + bottomPad;
    const showBarLabels = labels && labels.length === bins.length;

    const formatMin = labels && labels.length > 0 && !showBarLabels ? labels[0] : (integerValues ? allowedMin.toFixed(0) : allowedMin.toFixed(2));
    const formatMax = labels && labels.length > 1 && !showBarLabels ? labels[labels.length - 1] : (integerValues ? allowedMax.toFixed(0) : allowedMax.toFixed(2));

    const gradientId = `bar-grad-${theme}-${xLabel.replace(/[^a-zA-Z0-9]/g, '_')}`;

    const fmtMultiplierPlusMinus = (mean?: number, std?: number) => {
        if (mean === undefined) return '—';
        const m = mean.toFixed(2) + '×';
        const s = (std === undefined) ? '0.00' : std.toFixed(2);
        return `${m} ± ${s}`;
    };
    const fmtPercentPlusMinus = (mean?: number, std?: number) => {
        if (mean === undefined) return '—';
        const m = (mean * 100).toFixed(1) + '%';
        const s = (std === undefined) ? '0.0' : (std * 100).toFixed(1) + '%';
        return `${m} ± ${s}`;
    };

    const isBehavioral = theme === 'behavioral';
    const primaryColor = isBehavioral ? '#c084fc' : '#38bdf8';
    const medianX = median !== undefined ? xFor(median) : null;

    return (
        <div style={{ width: '100%', maxWidth: width, display: 'flex', flexDirection: 'column', gap: 6 }}>
            <svg width={width} height={svgHeight} viewBox={`0 0 ${width} ${svgHeight}`} style={{ width: '100%', height: 'auto', display: 'block', overflow: 'visible' }}>
                <defs>
                    <linearGradient id={gradientId} x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" stopColor={isBehavioral ? '#e879f9' : '#38bdf8'} stopOpacity={0.95} />
                        <stop offset="100%" stopColor={isBehavioral ? '#8b5cf6' : '#1d4ed8'} stopOpacity={0.65} />
                    </linearGradient>
                </defs>

                {/* Histogram Bars */}
                {bins.map((count, i) => {
                    const h = Math.max(count > 0 ? 3 : 0, (count / maxCount) * (plotH - 4));
                    const slotWidth = barWidth;
                    const visualBarWidth = Math.max(2, Math.min(slotWidth - 2, 16));
                    const x = leftPad + i * slotWidth + (slotWidth - visualBarWidth) / 2;
                    const y = topPad + (plotH - h);

                    const binEdgeMin = binEdges[i] !== undefined ? binEdges[i] : xMin + i * (span / bins.length);
                    const binEdgeMax = binEdges[i + 1] !== undefined ? binEdges[i + 1] : xMin + (i + 1) * (span / bins.length);
                    const rangeLabel = integerValues
                        ? `[${Math.round(binEdgeMin)} - ${Math.round(binEdgeMax)}]`
                        : `[${binEdgeMin.toFixed(2)} - ${binEdgeMax.toFixed(2)}]`;
                    const pctStr = totalCount > 0 ? ` (${((count / totalCount) * 100).toFixed(1)}%)` : '';
                    const titleText = labels && labels[i]
                        ? `${labels[i]}: ${count} fish${pctStr}`
                        : `Bin ${i + 1} ${rangeLabel}: ${count} fish${pctStr}`;

                    return (
                        <rect
                            key={i}
                            x={x}
                            y={y}
                            width={visualBarWidth}
                            height={h}
                            fill={`url(#${gradientId})`}
                            rx={2}
                            ry={2}
                            style={{ cursor: 'pointer', transition: 'all 0.2s ease' }}
                        >
                            <title>{titleText}</title>
                        </rect>
                    );
                })}

                {/* Allowed bounds vertical lines */}
                {!showBarLabels && (
                    <>
                        <line x1={xFor(allowedMin)} x2={xFor(allowedMin)} y1={topPad} y2={topPad + plotH} stroke="rgba(255,255,255,0.15)" strokeDasharray="3 3" />
                        <line x1={xFor(allowedMax)} x2={xFor(allowedMax)} y1={topPad} y2={topPad + plotH} stroke="rgba(255,255,255,0.15)" strokeDasharray="3 3" />
                    </>
                )}

                {/* Median marker vertical overlay line */}
                {medianX !== null && (
                    <g>
                        <line
                            x1={medianX}
                            x2={medianX}
                            y1={topPad - 4}
                            y2={topPad + plotH}
                            stroke="#f59e0b"
                            strokeWidth={1.5}
                            strokeDasharray="2 2"
                        />
                        <polygon
                            points={`${medianX - 4},${topPad - 4} ${medianX + 4},${topPad - 4} ${medianX},${topPad}`}
                            fill="#f59e0b"
                        />
                    </g>
                )}

                {/* x-axis label */}
                <text x={leftPad + plotW / 2} y={topPad + plotH + 38} fontSize={11} fill="var(--color-text-dim, #94a3b8)" textAnchor="middle" fontWeight="500">
                    {xLabel}
                </text>

                {/* Bar labels OR Min/Max labels */}
                {showBarLabels ? (
                    bins.map((_, i) => {
                        const barCenterX = leftPad + i * barWidth + barWidth / 2;
                        return (
                            <text
                                key={i}
                                x={barCenterX}
                                y={topPad + plotH + 15}
                                fontSize={9}
                                fill="var(--color-text-dim, #94a3b8)"
                                textAnchor="middle"
                            >
                                {labels[i]}
                            </text>
                        );
                    })
                ) : (
                    <>
                        <line x1={xFor(allowedMin)} x2={xFor(allowedMin)} y1={topPad + plotH + 3} y2={topPad + plotH + 8} stroke="rgba(255,255,255,0.3)" />
                        <line x1={xFor(allowedMax)} x2={xFor(allowedMax)} y1={topPad + plotH + 3} y2={topPad + plotH + 8} stroke="rgba(255,255,255,0.3)" />
                        <text x={xFor(allowedMin)} y={topPad + plotH + 18} fontSize={10} fill="var(--color-text-dim, #94a3b8)" textAnchor="middle">{formatMin}</text>
                        <text x={xFor(allowedMax)} y={topPad + plotH + 18} fontSize={10} fill="var(--color-text-dim, #94a3b8)" textAnchor="middle">{formatMax}</text>
                    </>
                )}

                {/* y-axis label */}
                <text
                    x={leftPad - 12}
                    y={topPad + plotH / 2}
                    fontSize={10}
                    fill="var(--color-text-dim, #94a3b8)"
                    textAnchor="middle"
                    transform={`rotate(-90 ${leftPad - 12} ${topPad + plotH / 2})`}
                >
                    {yLabel}
                </text>
            </svg>

            {(mutationRateMean !== undefined || mutationStrengthMean !== undefined || hgtProbMean !== undefined) && (
                <div style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    justifyContent: 'center',
                    gap: '4px 12px',
                    fontSize: '0.75rem',
                    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                    lineHeight: 1.2,
                    color: 'rgba(255, 255, 255, 0.78)',
                    fontWeight: 600,
                    width: '100%',
                    padding: '2px 4px',
                    boxSizing: 'border-box',
                    marginTop: '-2px'
                }}>
                    <span style={{ whiteSpace: 'nowrap' }}>
                        <span style={{ color: primaryColor }}>MR:</span> {fmtMultiplierPlusMinus(mutationRateMean, mutationRateStd)}
                    </span>
                    <span style={{ whiteSpace: 'nowrap' }}>
                        <span style={{ color: primaryColor }}>MS:</span> {fmtMultiplierPlusMinus(mutationStrengthMean, mutationStrengthStd)}
                    </span>
                    <span style={{ whiteSpace: 'nowrap' }}>
                        <span style={{ color: primaryColor }}>HP:</span> {fmtPercentPlusMinus(hgtProbMean, hgtProbStd)}
                    </span>
                </div>
            )}
        </div>
    );
}

