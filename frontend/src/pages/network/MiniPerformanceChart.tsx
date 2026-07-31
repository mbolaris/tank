import type { PokerPerformanceSnapshot } from '../../types/simulation';
import type { SnapshotPlayer } from './types';

/**
 * Mini performance chart for network dashboard
 */
export function MiniPerformanceChart({ history }: { history: PokerPerformanceSnapshot[] }) {
    if (!history || history.length === 0) {
        return null;
    }

    const sortedHistory = [...history].sort((a, b) => a.hand - b.hand);
    const width = 280;
    const height = 50;
    const padding = { top: 5, right: 5, bottom: 5, left: 25 };
    const maxHand = Math.max(...sortedHistory.map((h) => h.hand), 1);
    const minHand = Math.min(...sortedHistory.map((h) => h.hand));
    const handRange = maxHand - minHand || 1;

    // Calculate fish average and standard values for each hand
    const chartData = sortedHistory.map((snapshot) => {
        const fishPlayers = snapshot.players.filter((p: SnapshotPlayer) => !p.is_standard && p.species !== 'plant');
        const plantPlayers = snapshot.players.filter((p: SnapshotPlayer) => !p.is_standard && p.species === 'plant');
        const standardPlayer = snapshot.players.find((p: SnapshotPlayer) => p.is_standard);

        const fishAvg = fishPlayers.length > 0
            ? fishPlayers.reduce((sum: number, p: SnapshotPlayer) => sum + p.net_energy, 0) / fishPlayers.length
            : 0;
        const plantAvg = plantPlayers.length > 0
            ? plantPlayers.reduce((sum: number, p: SnapshotPlayer) => sum + p.net_energy, 0) / plantPlayers.length
            : null;

        return {
            hand: snapshot.hand,
            fishAvg,
            plantAvg,
            standard: standardPlayer ? standardPlayer.net_energy : 0,
        };
    });

    const values = chartData.flatMap((d) => [d.fishAvg, d.standard, d.plantAvg].filter((v): v is number => v !== null));
    const minValue = Math.min(0, ...values);
    const maxValue = Math.max(0, ...values);
    const range = maxValue - minValue || 1;

    const scaleX = (hand: number) =>
        padding.left + ((hand - minHand) / handRange) * (width - padding.left - padding.right);
    const scaleY = (value: number) =>
        height - padding.bottom - ((value - minValue) / range) * (height - padding.top - padding.bottom);

    // Generate paths for fish average and standard
    const fishPath = chartData
        .map((point, i) => {
            const x = scaleX(point.hand);
            const y = scaleY(point.fishAvg);
            return `${i === 0 ? 'M' : 'L'}${x},${y}`;
        })
        .join(' ');

    const standardPath = chartData
        .map((point, i) => {
            const x = scaleX(point.hand);
            const y = scaleY(point.standard);
            return `${i === 0 ? 'M' : 'L'}${x},${y}`;
        })
        .join(' ');

    const hasPlantLine = chartData.some((point) => point.plantAvg !== null);
    const plantPath = hasPlantLine
        ? chartData
            .map((point, i) => {
                const plantValue = point.plantAvg ?? 0;
                const x = scaleX(point.hand);
                const y = scaleY(plantValue);
                return `${i === 0 ? 'M' : 'L'}${x},${y}`;
            })
            .join(' ')
        : '';

    const zeroY = scaleY(0);

    return (
        <svg width={width} height={height} style={{ display: 'block', margin: '0 auto' }}>
            {/* Zero line */}
            <line
                x1={padding.left}
                y1={zeroY}
                x2={width - padding.right}
                y2={zeroY}
                stroke="#475569"
                strokeWidth="1"
                strokeDasharray="2,2"
            />

            {/* Standard line (baseline) */}
            <path
                d={standardPath}
                fill="none"
                stroke="#ef4444"
                strokeWidth="1.5"
                strokeDasharray="3,3"
            />

            {/* Fish average line */}
            <path
                d={fishPath}
                fill="none"
                stroke="#a855f7"
                strokeWidth="2"
            />

            {/* Plant average line */}
            {hasPlantLine && (
                <path
                    d={plantPath}
                    fill="none"
                    stroke="#22c55e"
                    strokeWidth="1.5"
                    strokeDasharray="3,3"
                />
            )}
        </svg>
    );
}
