/**
 * Static poker benchmark display component
 */

import type {
  AutoEvaluatePlayerStats,
  AutoEvaluateStats,
  PokerPerformanceSnapshot,
} from '../types/simulation';
import { colors, commonStyles } from '../styles/theme';

const palette = ['#22c55e', '#38bdf8', '#a855f7', '#f97316'];

function PerformanceChart({
  history,
  players,
}: {
  history: PokerPerformanceSnapshot[];
  players: AutoEvaluatePlayerStats[];
}) {
  if (!history || history.length === 0) {
    return null;
  }

  const sortedHistory = [...history].sort((a, b) => a.hand - b.hand);
  const width = 820;
  const height = 280;
  const padding = 40;
  const maxHand = Math.max(...sortedHistory.map((h) => h.hand), 1);
  const allValues = sortedHistory.flatMap((h) => h.players.map((p) => p.net_energy));
  const minValue = Math.min(0, ...allValues);
  const maxValue = Math.max(0, ...allValues);
  const range = maxValue - minValue || 1;

  const scaleX = (hand: number) =>
    padding + (hand / maxHand) * (width - padding * 2);
  const scaleY = (value: number) =>
    height - padding - ((value - minValue) / range) * (height - padding * 2);

  const playerOrder = [...players].sort(
    (a, b) => Number(a.is_standard) - Number(b.is_standard)
  );

  return (
    <div style={styles.chartWrapper}>
      <div style={styles.chartHeader}>
        <div>
          <div style={styles.chartTitle}>Performance over time</div>
          <div style={styles.chartSubtitle}>
            Net energy vs starting stack across hands
          </div>
        </div>
        <div style={styles.chartLegend}>
          {playerOrder.map((player, index) => {
            const color = palette[index % palette.length];
            return (
              <div key={player.player_id} style={styles.legendItem}>
                <span
                  style={{
                    ...styles.legendSwatch,
                    backgroundColor: color,
                  }}
                />
                <span>
                  {player.is_standard ? 'Static standard' : player.name}
                </span>
              </div>
            );
          })}
        </div>
      </div>
      <svg width={width} height={height} style={styles.chartSvg}>
        <line
          x1={padding}
          y1={scaleY(0)}
          x2={width - padding}
          y2={scaleY(0)}
          stroke={colors.border}
          strokeDasharray="4 4"
        />
        {playerOrder.map((player, index) => {
          const color = palette[index % palette.length];
          const pathD = sortedHistory
            .map((point, pointIndex) => {
              const playerPoint = point.players.find(
                (p) => p.player_id === player.player_id
              );
              const value = playerPoint ? playerPoint.net_energy : 0;
              const x = scaleX(point.hand);
              const y = scaleY(value);
              return `${pointIndex === 0 ? 'M' : 'L'}${x},${y}`;
            })
            .join(' ');

          return (
            <path
              key={player.player_id}
              d={pathD}
              fill="none"
              stroke={color}
              strokeWidth={2.5}
              opacity={player.is_standard ? 0.85 : 1}
            />
          );
        })}
      </svg>
    </div>
  );
}

export function AutoEvaluateDisplay({
  stats,
  onClose,
  loading,
}: {
  stats: AutoEvaluateStats | null;
  onClose: () => void;
  loading: boolean;
}) {
  if (loading && !stats) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <h2 style={styles.title}>Running static benchmark...</h2>
          <button onClick={onClose} style={styles.closeButton}>
            ×
          </button>
        </div>
        <div style={styles.loading}>
          <p>
            Playing a regular series with the leaderboard&apos;s top three fish vs
            the static standard player.
          </p>
          <p style={styles.loadingSubtext}>This may take a moment...</p>
        </div>
      </div>
    );
  }

  if (!stats || !stats.players) {
    return null;
  }

  const isTie = stats.winner === 'Tie';
  const standardPlayer = stats.players.find((p) => p.is_standard);
  const fishPlayers = stats.players.filter((p) => !p.is_standard);
  const standardWon = stats.winner === standardPlayer?.name;

  const playerMap = new Map<string, AutoEvaluatePlayerStats>();
  stats.players.forEach((player) => {
    playerMap.set(player.player_id, player);
  });

  (stats.performance_history ?? []).forEach((snapshot) => {
    snapshot.players.forEach((player) => {
      if (!playerMap.has(player.player_id)) {
          playerMap.set(player.player_id, {
            player_id: player.player_id,
            name: player.name,
            is_standard: player.is_standard,
            energy: player.energy,
            hands_won: 0,
            hands_lost: 0,
            total_energy_won: 0,
            total_energy_lost: 0,
          net_energy: player.net_energy,
          win_rate: 0,
        });
      }
    });
  });

  const chartPlayers = Array.from(playerMap.values());

  // Calculate aggregate fish stats
  const totalFishWins = fishPlayers.reduce((sum, p) => sum + p.hands_won, 0);
  const totalFishEnergy = fishPlayers.reduce((sum, p) => sum + p.net_energy, 0);
  const fishWinRate = stats.hands_played > 0
    ? ((totalFishWins / stats.hands_played) * 100).toFixed(1)
    : '0.0';

  const sortedPlayers = [...stats.players].sort((a, b) => b.energy - a.energy);

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>Static Poker Benchmark</h2>
        <button onClick={onClose} style={styles.closeButton}>
          ×
        </button>
      </div>

      <p style={styles.helperText}>
        Top leaderboard fish are automatically benchmarked against the static evaluation
        player every few minutes. The chart below shows how the current contenders compare
        to the static baseline over time.
      </p>

      {/* Winner Announcement */}
      <div
        style={{
          ...styles.winnerSection,
          backgroundColor: standardWon
            ? colors.buttonDanger
            : isTie
              ? colors.bgLight
              : colors.buttonSuccess,
        }}
      >
        <h3 style={styles.winnerTitle}>
          {isTie ? '🤝 Tie Game!' : `🏆 ${stats.winner} Wins!`}
        </h3>
        <p style={styles.winnerSubtext}>{stats.reason}</p>
      </div>

      {/* Summary Stats */}
      <div style={styles.summaryGrid}>
        <div style={styles.summaryCard}>
          <div style={styles.summaryLabel}>Hands Played</div>
          <div style={styles.summaryValue}>{stats.hands_played}</div>
        </div>
        <div style={styles.summaryCard}>
          <div style={styles.summaryLabel}>Fish Win Rate</div>
          <div style={styles.summaryValue}>{fishWinRate}%</div>
        </div>
        <div style={styles.summaryCard}>
          <div style={styles.summaryLabel}>Fish Net Energy</div>
          <div
            style={{
              ...styles.summaryValue,
              color:
                totalFishEnergy >= 0 ? colors.buttonSuccess : colors.danger,
            }}
          >
            {totalFishEnergy >= 0 ? '+' : ''}
            {totalFishEnergy}
          </div>
        </div>
      </div>

      <PerformanceChart
        history={stats.performance_history ?? []}
        players={chartPlayers}
      />

      {/* Detailed Stats */}
      <div style={styles.detailsSection}>
        <h3 style={styles.sectionTitle}>Detailed Statistics</h3>

        {/* Display all players sorted by final energy */}
        {sortedPlayers.map((player) => (
          <div key={player.player_id} style={styles.playerSection}>
            <h4 style={styles.playerName}>
              {player.is_standard ? '🤖' : '🐟'} {player.name}
            </h4>
            <div style={styles.statsGrid}>
              <div style={styles.statRow}>
                <span style={styles.statLabel}>Final Energy:</span>
                <span style={styles.statValue}>{player.energy} ⚡</span>
              </div>
              <div style={styles.statRow}>
                <span style={styles.statLabel}>Hands Won:</span>
                <span style={styles.statValue}>{player.hands_won}</span>
              </div>
              <div style={styles.statRow}>
                <span style={styles.statLabel}>Hands Lost:</span>
                <span style={styles.statValue}>{player.hands_lost}</span>
              </div>
              <div style={styles.statRow}>
                <span style={styles.statLabel}>Total Won:</span>
                <span style={{ ...styles.statValue, color: colors.buttonSuccess }}>
                  +{player.total_energy_won} ⚡
                </span>
              </div>
              <div style={styles.statRow}>
                <span style={styles.statLabel}>Total Lost:</span>
                <span style={{ ...styles.statValue, color: colors.danger }}>
                  -{player.total_energy_lost} ⚡
                </span>
              </div>
              <div style={styles.statRow}>
                <span style={styles.statLabel}>Net Profit:</span>
                <span
                  style={{
                    ...styles.statValue,
                    color:
                      player.net_energy >= 0
                        ? colors.buttonSuccess
                        : colors.danger,
                    fontWeight: 'bold',
                  }}
                >
                  {player.net_energy >= 0 ? '+' : ''}
                  {player.net_energy} ⚡
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Close Button */}
      <div style={styles.actions}>
        <button onClick={onClose} style={styles.closeActionButton}>
          Close
        </button>
      </div>
    </div>
  );
}

const styles = {
  container: {
    backgroundColor: colors.bgDark,
    borderRadius: '12px',
    padding: '20px',
    border: `2px solid ${colors.primary}`,
    boxShadow: '0 0 20px rgba(0, 255, 0, 0.2)',
    width: '100%',
    maxWidth: '820px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px',
    borderBottom: `1px solid ${colors.border}`,
    paddingBottom: '12px',
  },
  title: {
    margin: 0,
    fontSize: '24px',
    color: colors.primary,
  },
  helperText: {
    margin: '0 0 16px 0',
    color: colors.textSecondary,
    lineHeight: 1.5,
    fontSize: '14px',
  },
  closeButton: {
    background: 'none',
    border: 'none',
    color: colors.text,
    fontSize: '32px',
    cursor: 'pointer',
    padding: '0 8px',
  },
  loading: {
    padding: '40px',
    textAlign: 'center' as const,
    fontSize: '16px',
  },
  loadingSubtext: {
    marginTop: '12px',
    color: colors.textSecondary,
    fontSize: '14px',
  },
  winnerSection: {
    padding: '24px',
    borderRadius: '8px',
    textAlign: 'center' as const,
    marginBottom: '24px',
    border: `2px solid ${colors.primary}`,
  },
  winnerTitle: {
    margin: '0 0 8px 0',
    fontSize: '28px',
    color: colors.text,
  },
  winnerSubtext: {
    margin: 0,
    fontSize: '14px',
    color: colors.textSecondary,
  },
  summaryGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '16px',
    marginBottom: '24px',
  },
  summaryCard: {
    padding: '16px',
    backgroundColor: colors.bgLight,
    borderRadius: '8px',
    textAlign: 'center' as const,
    border: `1px solid ${colors.border}`,
  },
  summaryLabel: {
    fontSize: '12px',
    color: colors.textSecondary,
    marginBottom: '8px',
  },
  summaryValue: {
    fontSize: '24px',
    fontWeight: 'bold',
    color: colors.primary,
  },
  chartWrapper: {
    backgroundColor: colors.bgLight,
    border: `1px solid ${colors.border}`,
    borderRadius: '8px',
    padding: '12px',
    marginBottom: '24px',
  },
  chartHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '12px',
  },
  chartTitle: {
    color: colors.primary,
    fontWeight: 700,
    fontSize: '16px',
  },
  chartSubtitle: {
    color: colors.textSecondary,
    fontSize: '13px',
  },
  chartSvg: {
    width: '100%',
  },
  chartLegend: {
    display: 'flex',
    gap: '12px',
    flexWrap: 'wrap' as const,
    justifyContent: 'flex-end',
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    color: colors.text,
    fontSize: '13px',
  },
  legendSwatch: {
    width: '14px',
    height: '14px',
    borderRadius: '4px',
    display: 'inline-block',
    border: `1px solid ${colors.border}`,
  },
  detailsSection: {
    marginBottom: '24px',
  },
  sectionTitle: {
    margin: '0 0 16px 0',
    fontSize: '18px',
    color: colors.primary,
  },
  playerSection: {
    padding: '16px',
    backgroundColor: colors.bgLight,
    borderRadius: '8px',
    marginBottom: '16px',
    border: `1px solid ${colors.border}`,
  },
  playerName: {
    margin: '0 0 12px 0',
    fontSize: '16px',
    color: colors.primary,
  },
  statsGrid: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '8px',
  },
  statRow: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '14px',
  },
  statLabel: {
    color: colors.textSecondary,
  },
  statValue: {
    color: colors.text,
    fontWeight: 500,
  },
  actions: {
    display: 'flex',
    justifyContent: 'center',
  },
  closeActionButton: {
    ...commonStyles.button,
    backgroundColor: colors.buttonPrimary,
    padding: '12px 32px',
    fontSize: '16px',
  },
} as const;
