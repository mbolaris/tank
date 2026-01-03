/**
 * Shared Poker Score Display component
 * Shows ELO or win-rate score with color-coded rating and sparkline chart
 */

interface PokerScoreDisplayProps {
    score?: number;
    elo?: number;
    history: number[];
    isLoading?: boolean;
    /** Compact mode for inline display (e.g., in stats panels) */
    compact?: boolean;
}

export function PokerScoreDisplay({ score, elo, history, isLoading, compact = false }: PokerScoreDisplayProps) {
    if (isLoading) {
        return (
            <div style={{
                marginTop: compact ? 0 : '10px',
                backgroundColor: '#1e293b',
                borderRadius: '6px',
                padding: compact ? '6px 10px' : '8px 12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                opacity: 0.7
            }}>
                <div>
                    <div style={{ fontSize: '9px', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '2px' }}>Poker Score</div>
                    <div style={{ fontSize: '10px', color: '#64748b', fontStyle: 'italic' }}>Analyzing...</div>
                </div>
            </div>
        );
    }

    // Use ELO as primary if available
    const displayElo = elo !== undefined && elo !== null && elo > 0;
    const value = displayElo ? elo : (score !== undefined ? Math.round(score * 100) : null);

    if (value === null) return null;

    // Color based on performance
    let color = '#3b82f6'; // Default Blue
    let rating = 'Unknown';

    if (displayElo) {
        color = elo >= 1600 ? '#22c55e' :
            elo >= 1400 ? '#84cc16' :
                elo >= 1200 ? '#eab308' :
                    elo >= 1000 ? '#f97316' : '#ef4444';

        rating = elo >= 1800 ? 'Grandmaster' :
            elo >= 1600 ? 'Expert' :
                elo >= 1400 ? 'Advanced' :
                    elo >= 1200 ? 'Intermediate' :
                        elo >= 1000 ? 'Beginner' : 'Novice';
    } else {
        const percentage = value as number;
        color = percentage >= 70 ? '#22c55e' :
            percentage >= 55 ? '#84cc16' :
                percentage >= 50 ? '#eab308' :
                    percentage >= 40 ? '#f97316' : '#ef4444';

        rating = percentage >= 90 ? 'Excellent' :
            percentage >= 70 ? 'Very Good' :
                percentage >= 55 ? 'Good' :
                    percentage >= 50 ? 'Average' :
                        percentage >= 40 ? 'Below Avg' : 'Poor';
    }

    // Sparkline
    const width = compact ? 80 : 120;
    const height = compact ? 18 : 24;
    const padding = 2;
    const plotWidth = width - padding * 2;
    const plotHeight = height - padding * 2;

    const points = history && history.length > 0 ? history : [displayElo ? elo : (score || 0)];

    // Auto-range the sparkline
    let minVal = Math.min(...points);
    let maxVal = Math.max(...points);

    if (!displayElo) {
        minVal = Math.min(minVal, 0.4);
        maxVal = Math.max(maxVal, 0.6);
    } else {
        // For ELO, provide some breathing room around the points
        const buffer = 100;
        minVal -= buffer;
        maxVal += buffer;
        if (minVal < 800) minVal = 800;
    }

    const range = maxVal - minVal || 1;

    const scaleX = (i: number) => padding + (i / (points.length - 1 || 1)) * plotWidth;
    const scaleY = (v: number) => height - padding - ((v - minVal) / range) * plotHeight;

    const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${scaleX(i)},${scaleY(p)}`).join(' ');

    return (
        <div style={{
            marginTop: compact ? 0 : '10px',
            backgroundColor: '#1e293b',
            borderRadius: '6px',
            padding: compact ? '6px 10px' : '8px 12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
        }}>
            <div>
                <div style={{ fontSize: '9px', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '2px' }}>
                    Poker Score {displayElo && <span style={{ color: '#6366f1', opacity: 0.8 }}>(ELO)</span>}
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
                    <span style={{ fontSize: compact ? '14px' : '18px', fontWeight: 700, color, lineHeight: 1 }}>
                        {displayElo ? Math.round(value as number) : `${value}%`}
                    </span>
                    <span style={{ fontSize: compact ? '9px' : '10px', color, fontWeight: 600 }}>{rating}</span>
                </div>
            </div>

            {points.length > 1 && (
                <svg width={width} height={height}>
                    {!displayElo && (
                        <line
                            x1={0} y1={scaleY(0.5)}
                            x2={width} y2={scaleY(0.5)}
                            stroke="#334155" strokeWidth="1" strokeDasharray="2,2"
                        />
                    )}
                    <path d={pathD} fill="none" stroke={color} strokeWidth="1.5" />
                    <circle cx={scaleX(points.length - 1)} cy={scaleY(points[points.length - 1])} r={2} fill={color} />
                </svg>
            )}
        </div>
    );
}
