/**
 * Auto-evaluation poker results display component
 */

import { colors, commonStyles } from '../styles/theme';

interface AutoEvaluateStats {
  hands_played: number;
  hands_remaining: number;
  fish_energy: number;
  standard_energy: number;
  fish_wins: number;
  standard_wins: number;
  fish_total_won: number;
  fish_total_lost: number;
  standard_total_won: number;
  standard_total_lost: number;
  game_over: boolean;
  winner: string | null;
  reason: string;
  fish_name: string;
  fish_id: number;
  fish_generation: number;
  fish_net_energy: number;
  fish_win_rate: number;
}

interface AutoEvaluateDisplayProps {
  stats: AutoEvaluateStats | null;
  onClose: () => void;
  loading: boolean;
}

export function AutoEvaluateDisplay({ stats, onClose, loading }: AutoEvaluateDisplayProps) {
  if (loading && !stats) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <h2 style={styles.title}>Auto-Evaluating Poker Skill...</h2>
          <button onClick={onClose} style={styles.closeButton}>×</button>
        </div>
        <div style={styles.loading}>
          <p>Running automated poker evaluation against standard algorithm...</p>
          <p style={styles.loadingSubtext}>This may take a moment...</p>
        </div>
      </div>
    );
  }

  if (!stats) {
    return null;
  }

  const fishWon = stats.winner === stats.fish_name;
  const standardWon = stats.winner === 'Standard Algorithm';
  const isTie = stats.winner === 'Tie';

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>Auto-Evaluation Results</h2>
        <button onClick={onClose} style={styles.closeButton}>×</button>
      </div>

      {/* Winner Announcement */}
      <div style={{
        ...styles.winnerSection,
        backgroundColor: fishWon ? colors.buttonSuccess : (standardWon ? colors.buttonDanger : colors.bgLight),
      }}>
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
          <div style={styles.summaryValue}>{stats.fish_win_rate}%</div>
        </div>
        <div style={styles.summaryCard}>
          <div style={styles.summaryLabel}>Fish Net Energy</div>
          <div style={{
            ...styles.summaryValue,
            color: stats.fish_net_energy >= 0 ? colors.buttonSuccess : colors.danger,
          }}>
            {stats.fish_net_energy >= 0 ? '+' : ''}{stats.fish_net_energy}
          </div>
        </div>
      </div>

      {/* Detailed Stats */}
      <div style={styles.detailsSection}>
        <h3 style={styles.sectionTitle}>Detailed Statistics</h3>

        {/* Fish Stats */}
        <div style={styles.playerSection}>
          <h4 style={styles.playerName}>
            🐟 {stats.fish_name} #{stats.fish_id}
          </h4>
          <div style={styles.statsGrid}>
            <div style={styles.statRow}>
              <span style={styles.statLabel}>Final Energy:</span>
              <span style={styles.statValue}>{stats.fish_energy} ⚡</span>
            </div>
            <div style={styles.statRow}>
              <span style={styles.statLabel}>Hands Won:</span>
              <span style={styles.statValue}>{stats.fish_wins}</span>
            </div>
            <div style={styles.statRow}>
              <span style={styles.statLabel}>Hands Lost:</span>
              <span style={styles.statValue}>{stats.standard_wins}</span>
            </div>
            <div style={styles.statRow}>
              <span style={styles.statLabel}>Total Won:</span>
              <span style={{ ...styles.statValue, color: colors.buttonSuccess }}>
                +{stats.fish_total_won} ⚡
              </span>
            </div>
            <div style={styles.statRow}>
              <span style={styles.statLabel}>Total Lost:</span>
              <span style={{ ...styles.statValue, color: colors.danger }}>
                -{stats.fish_total_lost} ⚡
              </span>
            </div>
            <div style={styles.statRow}>
              <span style={styles.statLabel}>Net Profit:</span>
              <span style={{
                ...styles.statValue,
                color: stats.fish_net_energy >= 0 ? colors.buttonSuccess : colors.danger,
                fontWeight: 'bold',
              }}>
                {stats.fish_net_energy >= 0 ? '+' : ''}{stats.fish_net_energy} ⚡
              </span>
            </div>
          </div>
        </div>

        {/* Standard Algorithm Stats */}
        <div style={styles.playerSection}>
          <h4 style={styles.playerName}>
            🤖 Standard Algorithm
          </h4>
          <div style={styles.statsGrid}>
            <div style={styles.statRow}>
              <span style={styles.statLabel}>Final Energy:</span>
              <span style={styles.statValue}>{stats.standard_energy} ⚡</span>
            </div>
            <div style={styles.statRow}>
              <span style={styles.statLabel}>Hands Won:</span>
              <span style={styles.statValue}>{stats.standard_wins}</span>
            </div>
            <div style={styles.statRow}>
              <span style={styles.statLabel}>Hands Lost:</span>
              <span style={styles.statValue}>{stats.fish_wins}</span>
            </div>
            <div style={styles.statRow}>
              <span style={styles.statLabel}>Total Won:</span>
              <span style={{ ...styles.statValue, color: colors.buttonSuccess }}>
                +{stats.standard_total_won} ⚡
              </span>
            </div>
            <div style={styles.statRow}>
              <span style={styles.statLabel}>Total Lost:</span>
              <span style={{ ...styles.statValue, color: colors.danger }}>
                -{stats.standard_total_lost} ⚡
              </span>
            </div>
            <div style={styles.statRow}>
              <span style={styles.statLabel}>Net Profit:</span>
              <span style={{
                ...styles.statValue,
                color: (stats.standard_total_won - stats.standard_total_lost) >= 0 ? colors.buttonSuccess : colors.danger,
                fontWeight: 'bold',
              }}>
                {(stats.standard_total_won - stats.standard_total_lost) >= 0 ? '+' : ''}
                {(stats.standard_total_won - stats.standard_total_lost).toFixed(1)} ⚡
              </span>
            </div>
          </div>
        </div>
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
};
