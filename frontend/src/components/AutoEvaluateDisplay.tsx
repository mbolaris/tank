/**
 * Static poker benchmark display component
 */

import type {
    AutoEvaluateStats,
    AutoEvaluatePlayerStats,
    PokerPerformanceSnapshot,
} from '../types/simulation';
import { colors } from '../styles/theme';
import { useEffect, useState } from 'react';

function PerformanceChart({
    history,
    metric = 'energy',
}: {
    history: PokerPerformanceSnapshot[];
    metric?: 'energy' | 'winRate';
}) {
    if (!history || history.length === 0) {
        return null;
    }

    const sortedHistory = [...history].sort((a, b) => a.hand - b.hand);
    const width = 1088;
    const height = 180;
    const padding = { top: 20, right: 40, bottom: 35, left: 55 };
    const maxHand = Math.max(...sortedHistory.map((h) => h.hand), 1);
    const minHand = Math.min(...sortedHistory.map((h) => h.hand));
    const handRange = maxHand - minHand || 1;

    // Calculate fish average and standard values for each hand
    const chartData = sortedHistory.map((snapshot) => {
        const fishPlayers = snapshot.players.filter((p) => !p.is_standard && p.species !== 'plant');
        const plantPlayers = snapshot.players.filter((p) => p.species === 'plant');
        const standardPlayer = snapshot.players.find((p) => p.is_standard);

        const getValue = (p: PokerPerformanceSnapshot['players'][number]) => metric === 'energy' ? p.net_energy : (p.win_rate ?? 0);

        const fishAvg = fishPlayers.length > 0
            ? fishPlayers.reduce((sum, p) => sum + getValue(p), 0) / fishPlayers.length
            : 0;
        const plantAvg = plantPlayers.length > 0
            ? plantPlayers.reduce((sum, p) => sum + getValue(p), 0) / plantPlayers.length
            : null;

        return {
            hand: snapshot.hand,
            fishAvg,
            standard: standardPlayer ? getValue(standardPlayer) : 0,
            plantAvg,
        };
    });

    const allValues = chartData.flatMap((d) => {
        if (d.plantAvg === null) {
            return [d.fishAvg, d.standard];
        }
        return [d.fishAvg, d.standard, d.plantAvg];
    });
    const minValue = Math.min(0, ...allValues);
    const maxValue = Math.max(0, ...allValues);
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

    // Y-axis ticks
    const yTicks = [minValue, 0, maxValue].filter((v, i, arr) => arr.indexOf(v) === i);

    return (
        <div style={styles.chartWrapper}>
            <svg width={width} height={height} style={styles.chartSvg}>
                {/* Y-axis */}
                <line
                    x1={padding.left}
                    y1={padding.top}
                    x2={padding.left}
                    y2={height - padding.bottom}
                    stroke={colors.border}
                    strokeWidth={1}
                />
                {/* X-axis */}
                <line
                    x1={padding.left}
                    y1={height - padding.bottom}
                    x2={width - padding.right}
                    y2={height - padding.bottom}
                    stroke={colors.border}
                    strokeWidth={1}
                />

                {/* Y-axis ticks and labels */}
                {yTicks.map((tick) => (
                    <g key={tick}>
                        <line
                            x1={padding.left - 5}
                            y1={scaleY(tick)}
                            x2={padding.left}
                            y2={scaleY(tick)}
                            stroke={colors.border}
                        />
                        <text
                            x={padding.left - 8}
                            y={scaleY(tick)}
                            fill={colors.textSecondary}
                            fontSize={10}
                            textAnchor="end"
                            dominantBaseline="middle"
                        >
                            {metric === 'energy'
                                ? `${tick >= 0 ? '+' : ''}${Math.round(tick)}`
                                : `${Math.round(tick)}%`
                            }
                        </text>
                        {/* Grid line */}
                        <line
                            x1={padding.left}
                            y1={scaleY(tick)}
                            x2={width - padding.right}
                            y2={scaleY(tick)}
                            stroke={tick === 0 ? colors.border : 'rgba(100,100,100,0.2)'}
                            strokeDasharray={tick === 0 ? "4 4" : "2 4"}
                        />
                    </g>
                ))}

                {/* X-axis label */}
                <text
                    x={(width - padding.left - padding.right) / 2 + padding.left}
                    y={height - 5}
                    fill={colors.textSecondary}
                    fontSize={11}
                    textAnchor="middle"
                >
                    Hands Played
                </text>

                {/* Y-axis label */}
                <text
                    x={12}
                    y={(height - padding.top - padding.bottom) / 2 + padding.top}
                    fill={colors.textSecondary}
                    fontSize={11}
                    textAnchor="middle"
                    transform={`rotate(-90, 12, ${(height - padding.top - padding.bottom) / 2 + padding.top})`}
                >
                    {metric === 'energy' ? 'Profit' : 'Win %'}
                </text>

                {/* Fish average line */}
                <path
                    d={fishPath}
                    fill="none"
                    stroke="#a78bfa"
                    strokeWidth={2}
                />

                {/* Standard algorithm line */}
                <path
                    d={standardPath}
                    fill="none"
                    stroke="#ef4444"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                />

                {/* Plant average line */}
                {hasPlantLine && (
                    <path
                        d={plantPath}
                        fill="none"
                        stroke="#84cc16"
                        strokeWidth={2}
                        strokeDasharray="3 4"
                    />
                )}

                {/* Legend */}
                <g transform={`translate(${width - padding.right - 200}, ${padding.top})`}>
                    <rect x={0} y={0} width={190} height={hasPlantLine ? 64 : 44} fill="rgba(15,23,42,0.8)" rx={4} />
                    <line x1={10} y1={14} x2={30} y2={14} stroke="#a78bfa" strokeWidth={2} />
                    <text x={36} y={18} fill={colors.text} fontSize={11}>Fish (avg)</text>
                    {hasPlantLine && (
                        <>
                            <line x1={10} y1={32} x2={30} y2={32} stroke="#84cc16" strokeWidth={2} strokeDasharray="3 4" />
                            <text x={36} y={36} fill={colors.text} fontSize={11}>Plants (avg)</text>
                        </>
                    )}
                    <line
                        x1={10}
                        y1={hasPlantLine ? 50 : 32}
                        x2={30}
                        y2={hasPlantLine ? 50 : 32}
                        stroke="#ef4444"
                        strokeWidth={2}
                        strokeDasharray="5 5"
                    />
                    <text
                        x={36}
                        y={hasPlantLine ? 54 : 36}
                        fill={colors.text}
                        fontSize={11}
                    >
                        Static Baseline
                    </text>
                </g>
            </svg>
        </div>
    );
}

const getPlayerIcon = (player: AutoEvaluatePlayerStats): string => {
    if (player.is_standard) {
        return '🤖';
    }
    if (player.species === 'plant') {
        return '🌿';
    }
    return '🐟';
};

function PlayerRow({ player, isWinning }: { player: AutoEvaluatePlayerStats; isWinning: boolean }) {
    const netColor = player.net_energy >= 0 ? '#22c55e' : '#ef4444';
    const genLabel = player.fish_generation !== undefined ? `Gen ${player.fish_generation}` : '';

    return (
        <div style={{
            ...styles.playerRow,
            borderLeft: isWinning ? '3px solid #22c55e' : '3px solid transparent',
            background: isWinning ? 'rgba(34, 197, 94, 0.08)' : 'transparent',
        }}>
            <div style={styles.playerName}>
                {getPlayerIcon(player)} {player.name}
                {genLabel && <span style={styles.genLabel}>{genLabel}</span>}
            </div>
            <div style={styles.playerStat}>
                <span style={styles.statLabel}>Win Rate</span>
                <span style={styles.statValue}>{Math.round(player.win_rate ?? 0)}%</span>
            </div>
            <div style={styles.playerStat}>
                <span style={styles.statLabel}>Profit</span>
                <span style={{ ...styles.statValue, color: netColor, fontWeight: 700 }}>
                    {player.net_energy >= 0 ? '+' : ''}{Math.round(player.net_energy)}
                </span>
            </div>
            <div style={styles.playerStat}>
                <span style={styles.statLabel}>Stack</span>
                <span style={styles.statValue}>{Math.round(player.energy)}</span>
            </div>
        </div>
    );
}

export function AutoEvaluateDisplay({
    stats,
    loading,
}: {
    stats: AutoEvaluateStats | null;
    loading: boolean;
}) {
    const [fullHistory, setFullHistory] = useState<PokerPerformanceSnapshot[]>([]);
    const [metric, setMetric] = useState<'energy' | 'winRate'>('energy');
    const [historyError, setHistoryError] = useState<string | null>(null);

    // Fetch full history periodically or when stats update
    useEffect(() => {
        if (!stats) return;

        const fetchHistory = async () => {
            try {
                setHistoryError(null);
                const response = await fetch('/api/evaluation-history');
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                const data = await response.json();
                setFullHistory(data);
            } catch (error) {
                const message = error instanceof Error ? error.message : 'Unknown error';
                setHistoryError(`Failed to fetch history: ${message}`);
            }
        };

        // Fetch if we hit the truncation limit (50)
        if (stats.performance_history?.length === 50) {
            fetchHistory();
        } else if (stats.performance_history) {
            // If we have the full history in stats (e.g. start of game), use it
            setFullHistory(stats.performance_history);
        }
    }, [stats?.performance_history]);

    if (loading && !stats) {
        return (
            <div style={styles.container}>
                <div style={styles.header}>
                    <h2 style={styles.title}>Running benchmark...</h2>
                </div>
                <div style={styles.loading}>
                    <p>
                        Playing poker with the top 3 fish vs static algorithm to track evolution progress.
                    </p>
                    <p style={styles.loadingSubtext}>This may take a moment...</p>
                </div>
            </div>
        );
    }

    if (!stats || !stats.players) {
        return null;
    }

    const standardPlayer = stats.players.find(p => p.is_standard);
    const nonStandardPlayers = stats.players.filter(p => !p.is_standard);

    const plantPlayers = nonStandardPlayers.filter(p => p.species === 'plant');

    const plantTotalNet = plantPlayers.reduce((sum, p) => sum + p.net_energy, 0);
    const standardNet = standardPlayer?.net_energy ?? 0;
    const plantWinning = plantPlayers.length > 0 && plantTotalNet > standardNet;

    // Sort players by net energy for display
    const sortedPlayers = [...stats.players].sort((a, b) => b.net_energy - a.net_energy);
    const leader = sortedPlayers[0];

    // Use fullHistory if available and longer, otherwise fall back to stats.performance_history
    const displayHistory = fullHistory.length > (stats.performance_history?.length || 0)
        ? fullHistory
        : stats.performance_history || [];

    return (
        <div style={styles.container}>
            <div style={styles.header}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <h2 style={styles.title}>Evolution Benchmark</h2>
                    <div style={styles.toggleGroup}>
                        <button
                            onClick={() => setMetric('energy')}
                            style={metric === 'energy' ? styles.activeToggle : styles.toggle}
                        >
                            Energy
                        </button>
                        <button
                            onClick={() => setMetric('winRate')}
                            style={metric === 'winRate' ? styles.activeToggle : styles.toggle}
                        >
                            Win %
                        </button>
                    </div>
                </div>
                <div style={styles.headerStats}>
                    <span style={styles.handsPlayed}>{stats.hands_played} hands</span>
                    {stats.game_over ? (
                        <span style={styles.gameOver}>Benchmark Complete</span>
                    ) : (
                        <span style={styles.inProgress}>In Progress</span>
                    )}
                </div>
            </div>

            {/* Summary */}
            <div style={styles.summary}>
                <div style={styles.summaryItem}>
                    <span style={styles.summaryLabel}>Leader</span>
                    <span style={styles.summaryValue}>
                        {getPlayerIcon(leader)} {leader.name} ({leader.net_energy >= 0 ? '+' : ''}{Math.round(leader.net_energy)} ⚡)
                    </span>
                </div>
                {plantPlayers.length > 0 && (
                    <div style={styles.summaryItem}>
                        <span style={styles.summaryLabel}>Plants vs Baseline</span>
                        <span style={{
                            ...styles.summaryValue,
                            color: plantWinning ? '#84cc16' : '#ef4444',
                        }}>
                            {plantWinning ? '+' : ''}{Math.round(plantTotalNet - standardNet)} ⚡
                        </span>
                    </div>
                )}
            </div>

            {/* Player breakdown */}
            <div style={styles.playersSection}>
                {sortedPlayers.map((player, idx) => (
                    <PlayerRow
                        key={player.player_id}
                        player={player}
                        isWinning={idx === 0}
                    />
                ))}
            </div>

            {historyError && (
                <div style={styles.errorMessage}>
                    {historyError}
                </div>
            )}

            <PerformanceChart history={displayHistory} metric={metric} />
        </div>
    );
}

const styles = {
    container: {
        backgroundColor: colors.bgDark,
        borderRadius: '12px',
        padding: '12px',
        border: `1px solid ${colors.border}`,
        width: '100%',
        maxWidth: '1088px',
    },
    header: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '12px',
        borderBottom: `1px solid ${colors.border}`,
        paddingBottom: '8px',
    },
    title: {
        margin: 0,
        fontSize: '16px',
        color: colors.primary,
    },
    headerStats: {
        display: 'flex',
        gap: '12px',
        alignItems: 'center',
    },
    handsPlayed: {
        color: colors.textSecondary,
        fontSize: '13px',
    },
    gameOver: {
        color: '#22c55e',
        fontSize: '12px',
        fontWeight: 600,
        padding: '2px 8px',
        background: 'rgba(34, 197, 94, 0.15)',
        borderRadius: '4px',
    },
    inProgress: {
        color: '#3b82f6',
        fontSize: '12px',
        fontWeight: 600,
        padding: '2px 8px',
        background: 'rgba(59, 130, 246, 0.15)',
        borderRadius: '4px',
    },
    summary: {
        display: 'flex',
        gap: '24px',
        marginBottom: '12px',
        padding: '8px 12px',
        background: colors.bgLight,
        borderRadius: '6px',
    },
    summaryItem: {
        display: 'flex',
        gap: '8px',
        alignItems: 'center',
    },
    summaryLabel: {
        color: colors.textSecondary,
        fontSize: '12px',
    },
    summaryValue: {
        color: colors.text,
        fontSize: '13px',
        fontWeight: 600,
    },
    playersSection: {
        display: 'flex',
        flexDirection: 'column' as const,
        gap: '4px',
        marginBottom: '12px',
    },
    playerRow: {
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
        padding: '6px 12px',
        borderRadius: '4px',
    },
    playerName: {
        flex: '1 1 180px',
        color: colors.text,
        fontSize: '13px',
        fontWeight: 500,
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
    },
    genLabel: {
        color: colors.textSecondary,
        fontSize: '11px',
        fontWeight: 400,
    },
    playerStat: {
        display: 'flex',
        flexDirection: 'column' as const,
        alignItems: 'center',
        minWidth: '60px',
    },
    statLabel: {
        color: colors.textSecondary,
        fontSize: '10px',
        textTransform: 'uppercase' as const,
    },
    statValue: {
        color: colors.text,
        fontSize: '13px',
    },
    loading: {
        padding: '24px',
        textAlign: 'center' as const,
        fontSize: '14px',
    },
    loadingSubtext: {
        marginTop: '8px',
        color: colors.textSecondary,
        fontSize: '13px',
    },
    errorMessage: {
        padding: '8px 12px',
        marginBottom: '12px',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        border: '1px solid rgba(239, 68, 68, 0.3)',
        borderRadius: '6px',
        color: '#ef4444',
        fontSize: '12px',
    },
    chartWrapper: {
        backgroundColor: colors.bgLight,
        border: `1px solid ${colors.border}`,
        borderRadius: '8px',
        padding: '8px',
    },
    chartSvg: {
        width: '100%',
    },
    toggleGroup: {
        display: 'flex',
        background: 'rgba(0,0,0,0.2)',
        borderRadius: '4px',
        padding: '2px',
        gap: '2px',
    },
    toggle: {
        background: 'transparent',
        border: 'none',
        color: colors.textSecondary,
        fontSize: '11px',
        padding: '2px 8px',
        cursor: 'pointer',
        borderRadius: '3px',
    },
    activeToggle: {
        background: 'rgba(255,255,255,0.1)',
        border: 'none',
        color: colors.text,
        fontSize: '11px',
        padding: '2px 8px',
        cursor: 'pointer',
        borderRadius: '3px',
        fontWeight: 600,
    },
} as const;
