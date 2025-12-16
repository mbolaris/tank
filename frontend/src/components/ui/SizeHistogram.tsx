interface SizeHistogramProps {
    bins?: number[];
    edges?: number[];
    width?: number;
    height?: number;
}

export default function SizeHistogram({ bins = [], width = 240, height = 48 }: SizeHistogramProps) {
    if (!bins || bins.length === 0) return null;

    const maxCount = Math.max(...bins, 1);
    const barWidth = width / bins.length;

    return (
        <svg width={width} height={height} style={{ display: 'block' }}>
            {bins.map((count, i) => {
                const h = (count / maxCount) * (height - 6);
                const x = i * barWidth + 1;
                const y = height - h - 2;
                return (
                    <rect key={i} x={x} y={y} width={Math.max(0, barWidth - 2)} height={h} fill="#60a5fa" rx={2} ry={2} />
                );
            })}
            {/* optional axis line */}
            <line x1={0} y1={height - 1} x2={width} y2={height - 1} stroke="rgba(255,255,255,0.06)" />
        </svg>
    );
}
