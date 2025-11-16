/**
 * Stats panel component showing ecosystem statistics
 */

import type { StatsData } from '../types/simulation';

interface StatsPanelProps {
  stats: StatsData | null;
}

export function StatsPanel({ stats }: StatsPanelProps) {
  if (!stats) {
    return (
      <div style={styles.container}>
        <h2 style={styles.title}>Statistics</h2>
        <p style={styles.noData}>Waiting for data...</p>
      </div>
    );
  }

  const deathCauseEntries = Object.entries(stats.death_causes);

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Statistics</h2>

      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Ecosystem</h3>
        <div style={styles.statRow}>
          <span style={styles.statLabel}>Time:</span>
          <span style={styles.statValue}>{stats.time}</span>
        </div>
        <div style={styles.statRow}>
          <span style={styles.statLabel}>Frame:</span>
          <span style={styles.statValue}>{stats.frame.toLocaleString()}</span>
        </div>
      </div>

      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Population</h3>
        <div style={styles.statRow}>
          <span style={styles.statLabel}>Fish:</span>
          <span style={styles.statValue}>{stats.fish_count}</span>
        </div>
        <div style={styles.statRow}>
          <span style={styles.statLabel}>Food:</span>
          <span style={styles.statValue}>{stats.food_count}</span>
        </div>
        <div style={styles.statRow}>
          <span style={styles.statLabel}>Plants:</span>
          <span style={styles.statValue}>{stats.plant_count}</span>
        </div>
        <div style={styles.statRow}>
          <span style={styles.statLabel}>Capacity:</span>
          <span style={styles.statValue}>{stats.capacity}</span>
        </div>
      </div>

      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Genetics</h3>
        <div style={styles.statRow}>
          <span style={styles.statLabel}>Generation:</span>
          <span style={styles.statValue}>{stats.generation}</span>
        </div>
        <div style={styles.statRow}>
          <span style={styles.statLabel}>Total Births:</span>
          <span style={styles.statValue}>{stats.births}</span>
        </div>
        <div style={styles.statRow}>
          <span style={styles.statLabel}>Total Deaths:</span>
          <span style={styles.statValue}>{stats.deaths}</span>
        </div>
      </div>

      {deathCauseEntries.length > 0 && (
        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>Death Causes</h3>
          {deathCauseEntries.map(([cause, count]) => (
            <div key={cause} style={styles.statRow}>
              <span style={styles.statLabel}>{cause}:</span>
              <span style={styles.statValue}>{count}</span>
            </div>
          ))}
        </div>
      )}

      {stats.poker_stats && (
        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>Poker Stats</h3>
          {stats.poker_stats.total_games === 0 ? (
            <div style={styles.statRow}>
              <span style={{...styles.statValue, fontStyle: 'italic', opacity: 0.7}}>
                No poker games yet (fish need 10+ energy & to collide)
              </span>
            </div>
          ) : (
            <>
              <div style={styles.statRow}>
                <span style={styles.statLabel}>Games Played:</span>
                <span style={styles.statValue}>{stats.poker_stats.total_games}</span>
              </div>
              <div style={styles.statRow}>
                <span style={styles.statLabel}>W/L/T:</span>
                <span style={styles.statValue}>
                  {stats.poker_stats.total_wins}/{stats.poker_stats.total_losses}/{stats.poker_stats.total_ties}
                </span>
              </div>
              <div style={styles.statRow}>
                <span style={styles.statLabel}>Energy Won:</span>
                <span style={styles.statValue}>{stats.poker_stats.total_energy_won.toFixed(1)}</span>
              </div>
              <div style={styles.statRow}>
                <span style={styles.statLabel}>Energy Lost:</span>
                <span style={styles.statValue}>{stats.poker_stats.total_energy_lost.toFixed(1)}</span>
              </div>
              <div style={styles.statRow}>
                <span style={styles.statLabel}>House Cuts:</span>
                <span style={styles.statValue}>{(stats.poker_stats.total_house_cuts || 0).toFixed(1)}</span>
              </div>
              <div style={styles.statRow}>
                <span style={styles.statLabel}>Net Energy:</span>
                <span style={{
                  ...styles.statValue,
                  color: stats.poker_stats.net_energy >= 0 ? '#4ade80' : '#f87171'
                }}>
                  {stats.poker_stats.net_energy >= 0 ? '+' : ''}{stats.poker_stats.net_energy.toFixed(1)}
                </span>
              </div>
              <div style={styles.statRow}>
                <span style={styles.statLabel}>Best Hand:</span>
                <span style={styles.statValue}>{stats.poker_stats.best_hand_name}</span>
              </div>
            </>
          )}
        </div>
      )}

      <div style={styles.legend}>
        <h3 style={styles.legendTitle}>Species Legend</h3>
        <div style={styles.legendItems}>
          <div style={styles.legendItem}>
            <div style={{ ...styles.legendDot, backgroundColor: '#4ecdc4' }} />
            <span>Neural AI</span>
          </div>
          <div style={styles.legendItem}>
            <div style={{ ...styles.legendDot, backgroundColor: '#ffe66d' }} />
            <span>Algorithmic</span>
          </div>
          <div style={styles.legendItem}>
            <div style={{ ...styles.legendDot, backgroundColor: '#a8dadc' }} />
            <span>Schooling</span>
          </div>
          <div style={styles.legendItem}>
            <div style={{ ...styles.legendDot, backgroundColor: '#ff6b6b' }} />
            <span>Solo</span>
          </div>
        </div>
      </div>
    </div>
  );
}

const styles = {
  container: {
    padding: '24px',
    background: 'linear-gradient(145deg, rgba(30,41,59,0.92), rgba(15,23,42,0.95))',
    borderRadius: '20px',
    color: '#e2e8f0',
    border: '1px solid rgba(148,163,184,0.18)',
    boxShadow: '0 35px 55px rgba(2,6,23,0.65)',
  },
  title: {
    margin: '0 0 16px 0',
    fontSize: '20px',
    fontWeight: 600,
  },
  noData: {
    fontSize: '14px',
    color: '#94a3b8',
  },
  section: {
    marginBottom: '20px',
  },
  sectionTitle: {
    margin: '0 0 8px 0',
    fontSize: '14px',
    fontWeight: 500,
    color: '#94a3b8',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  },
  statRow: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '6px 0',
    fontSize: '14px',
    borderBottom: '1px solid #334155',
  },
  statLabel: {
    color: '#cbd5e1',
  },
  statValue: {
    fontWeight: 600,
    color: '#e2e8f0',
  },
  legend: {
    marginTop: '24px',
    padding: '16px',
    backgroundColor: 'rgba(15,23,42,0.85)',
    borderRadius: '12px',
    border: '1px solid rgba(148,163,184,0.1)',
  },
  legendTitle: {
    margin: '0 0 12px 0',
    fontSize: '14px',
    fontWeight: 500,
  },
  legendItems: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '8px',
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    fontSize: '13px',
  },
  legendDot: {
    width: '12px',
    height: '12px',
    borderRadius: '50%',
    marginRight: '8px',
  },
};
