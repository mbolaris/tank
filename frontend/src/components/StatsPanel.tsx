/**
 * Stats panel component showing ecosystem statistics
 */

import { useState } from 'react';
import type { StatsData } from '../types/simulation';

interface StatsPanelProps {
  stats: StatsData | null;
}

interface CollapsibleSectionProps {
  title: string;
  children: React.ReactNode;
  defaultExpanded?: boolean;
}

function CollapsibleSection({ title, children, defaultExpanded = true }: CollapsibleSectionProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div style={styles.section}>
      <h3
        style={{...styles.sectionTitle, cursor: 'pointer', userSelect: 'none'}}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span style={{marginRight: '8px', fontSize: '12px'}}>
          {isExpanded ? '▼' : '▶'}
        </span>
        {title}
      </h3>
      {isExpanded && <div>{children}</div>}
    </div>
  );
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
  const winRate = stats.poker_stats ? (stats.poker_stats.win_rate || 0) * 100 : 0;

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Statistics</h2>

      {/* Summary Section */}
      <div style={styles.summaryCard}>
        <div style={styles.summaryGrid}>
          <div style={styles.summaryItem}>
            <div style={styles.summaryLabel}>Fish</div>
            <div style={styles.summaryValue}>{stats.fish_count}</div>
          </div>
          <div style={styles.summaryItem}>
            <div style={styles.summaryLabel}>Gen</div>
            <div style={styles.summaryValue}>{stats.generation}</div>
          </div>
          <div style={styles.summaryItem}>
            <div style={styles.summaryLabel}>Energy</div>
            <div style={styles.summaryValue}>{stats.total_energy.toFixed(0)}</div>
          </div>
          <div style={styles.summaryItem}>
            <div style={styles.summaryLabel}>Frame</div>
            <div style={styles.summaryValue}>{(stats.frame / 1000).toFixed(1)}k</div>
          </div>
        </div>
      </div>

      {/* Ecosystem & Time */}
      <CollapsibleSection title="Ecosystem" defaultExpanded={false}>
        <div style={styles.gridRow}>
          <div style={styles.statRow}>
            <span style={styles.statLabel}>Time:</span>
            <span style={styles.statValue}>{stats.time}</span>
          </div>
          <div style={styles.statRow}>
            <span style={styles.statLabel}>Frame:</span>
            <span style={styles.statValue}>{stats.frame.toLocaleString()}</span>
          </div>
        </div>
        <div style={styles.gridRow}>
          <div style={styles.statRow}>
            <span style={styles.statLabel}>Capacity:</span>
            <span style={styles.statValue}>{stats.capacity}</span>
          </div>
          <div style={styles.statRow}>
            <span style={styles.statLabel}>Total Energy:</span>
            <span style={styles.statValue}>{stats.total_energy.toFixed(1)}</span>
          </div>
        </div>
      </CollapsibleSection>

      {/* Population */}
      <CollapsibleSection title="Population">
        <div style={styles.gridRow}>
          <div style={styles.statRow}>
            <span style={styles.statLabel}>Fish:</span>
            <span style={styles.statValue}>{stats.fish_count}</span>
          </div>
          <div style={styles.statRow}>
            <span style={styles.statLabel}>Food:</span>
            <span style={styles.statValue}>{stats.food_count}</span>
          </div>
        </div>
        <div style={styles.gridRow}>
          <div style={styles.statRow}>
            <span style={styles.statLabel}>Plants:</span>
            <span style={styles.statValue}>{stats.plant_count}</span>
          </div>
        </div>
      </CollapsibleSection>

      {/* Genetics */}
      <CollapsibleSection title="Genetics">
        <div style={styles.gridRow}>
          <div style={styles.statRow}>
            <span style={styles.statLabel}>Generation:</span>
            <span style={styles.statValue}>{stats.generation}</span>
          </div>
          <div style={styles.statRow}>
            <span style={styles.statLabel}>Total Births:</span>
            <span style={styles.statValue}>{stats.births}</span>
          </div>
        </div>
        <div style={styles.gridRow}>
          <div style={styles.statRow}>
            <span style={styles.statLabel}>Total Deaths:</span>
            <span style={styles.statValue}>{stats.deaths}</span>
          </div>
        </div>
      </CollapsibleSection>

      {/* Death Causes */}
      {deathCauseEntries.length > 0 && (
        <CollapsibleSection title="Death Causes" defaultExpanded={false}>
          {deathCauseEntries.map(([cause, count]) => (
            <div key={cause} style={styles.statRow}>
              <span style={styles.statLabel}>{cause}:</span>
              <span style={styles.statValue}>{count}</span>
            </div>
          ))}
        </CollapsibleSection>
      )}

      {/* Poker Stats */}
      {stats.poker_stats && (
        <CollapsibleSection title={`Poker Stats ${stats.poker_stats.total_games > 0 ? `(${winRate.toFixed(0)}% WR)` : ''}`}>
          {stats.poker_stats.total_games === 0 ? (
            <div style={styles.statRow}>
              <span style={{...styles.statValue, fontStyle: 'italic', opacity: 0.7}}>
                No poker games yet (fish need 10+ energy & to collide)
              </span>
            </div>
          ) : (
            <>
              {/* Key Metrics */}
              <div style={styles.subsection}>
                <div style={styles.gridRow}>
                  <div style={styles.statRow}>
                    <span style={styles.statLabel}>Games:</span>
                    <span style={styles.statValue}>{stats.poker_stats.total_games}</span>
                  </div>
                  <div style={styles.statRow}>
                    <span style={styles.statLabel}>W/L/T:</span>
                    <span style={styles.statValue}>
                      {stats.poker_stats.total_wins}/{stats.poker_stats.total_losses}/{stats.poker_stats.total_ties}
                    </span>
                  </div>
                </div>
                <div style={styles.gridRow}>
                  <div style={styles.statRow}>
                    <span style={styles.statLabel}>Win Rate:</span>
                    <span style={{
                      ...styles.statValue,
                      color: (stats.poker_stats.win_rate || 0) > 0.5 ? '#4ade80' : '#94a3b8'
                    }}>
                      {stats.poker_stats.win_rate_pct || '0.0%'}
                    </span>
                  </div>
                  <div style={styles.statRow}>
                    <span style={styles.statLabel}>Net Energy:</span>
                    <span style={{
                      ...styles.statValue,
                      color: stats.poker_stats.net_energy >= 0 ? '#4ade80' : '#f87171',
                      fontWeight: 600
                    }}>
                      {stats.poker_stats.net_energy >= 0 ? '+' : ''}{stats.poker_stats.net_energy.toFixed(1)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Performance */}
              <div style={styles.subsection}>
                <div style={styles.subsectionLabel}>Performance</div>
                <div style={styles.gridRow}>
                  <div style={styles.statRow}>
                    <span style={styles.statLabel}>ROI:</span>
                    <span style={{
                      ...styles.statValue,
                      color: (stats.poker_stats.roi || 0) >= 0 ? '#4ade80' : '#f87171'
                    }}>
                      {stats.poker_stats.roi !== undefined ? (stats.poker_stats.roi >= 0 ? '+' : '') + stats.poker_stats.roi.toFixed(2) : '0.00'}
                    </span>
                  </div>
                  <div style={styles.statRow}>
                    <span style={styles.statLabel}>Showdown:</span>
                    <span style={styles.statValue}>{stats.poker_stats.showdown_win_rate || '0.0%'}</span>
                  </div>
                </div>
              </div>

              {/* Playing Style */}
              <div style={styles.subsection}>
                <div style={styles.subsectionLabel}>Playing Style</div>
                <div style={styles.gridRow}>
                  <div style={styles.statRow}>
                    <span style={styles.statLabel}>VPIP:</span>
                    <span style={styles.statValue}>
                      {stats.poker_stats.vpip_pct || '0.0%'}
                    </span>
                  </div>
                  <div style={styles.statRow}>
                    <span style={styles.statLabel}>Aggression:</span>
                    <span style={styles.statValue}>
                      {stats.poker_stats.aggression_factor !== undefined ? stats.poker_stats.aggression_factor.toFixed(2) : '0.00'}
                    </span>
                  </div>
                </div>
                <div style={styles.gridRow}>
                  <div style={styles.statRow}>
                    <span style={styles.statLabel}>Fold Rate:</span>
                    <span style={styles.statValue}>{stats.poker_stats.avg_fold_rate || '0.0%'}</span>
                  </div>
                  <div style={styles.statRow}>
                    <span style={styles.statLabel}>Avg Hand:</span>
                    <span style={styles.statValue}>
                      {stats.poker_stats.avg_hand_rank !== undefined ? stats.poker_stats.avg_hand_rank.toFixed(2) : '0.00'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Advanced */}
              <div style={styles.subsection}>
                <div style={styles.subsectionLabel}>Advanced</div>
                <div style={styles.gridRow}>
                  <div style={styles.statRow}>
                    <span style={styles.statLabel}>Bluff Success:</span>
                    <span style={styles.statValue}>{stats.poker_stats.bluff_success_pct || '0.0%'}</span>
                  </div>
                  <div style={styles.statRow}>
                    <span style={styles.statLabel}>Position Edge:</span>
                    <span style={{
                      ...styles.statValue,
                      color: (stats.poker_stats.positional_advantage || 0) > 0 ? '#4ade80' : '#94a3b8'
                    }}>
                      {stats.poker_stats.positional_advantage_pct || '0.0%'}
                    </span>
                  </div>
                </div>
                <div style={styles.gridRow}>
                  <div style={styles.statRow}>
                    <span style={styles.statLabel}>Pre/Post Folds:</span>
                    <span style={styles.statValue}>
                      {stats.poker_stats.preflop_folds || 0}/{stats.poker_stats.postflop_folds || 0}
                    </span>
                  </div>
                  <div style={styles.statRow}>
                    <span style={styles.statLabel}>Best Hand:</span>
                    <span style={styles.statValue}>{stats.poker_stats.best_hand_name}</span>
                  </div>
                </div>
              </div>
            </>
          )}
        </CollapsibleSection>
      )}
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
  summaryCard: {
    background: 'rgba(51,65,85,0.4)',
    borderRadius: '12px',
    padding: '16px',
    marginBottom: '20px',
    border: '1px solid rgba(148,163,184,0.1)',
  },
  summaryGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '16px',
  },
  summaryItem: {
    textAlign: 'center' as const,
  },
  summaryLabel: {
    fontSize: '11px',
    color: '#94a3b8',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
    marginBottom: '6px',
  },
  summaryValue: {
    fontSize: '24px',
    fontWeight: 700,
    color: '#e2e8f0',
  },
  section: {
    marginBottom: '16px',
  },
  sectionTitle: {
    margin: '0 0 10px 0',
    fontSize: '13px',
    fontWeight: 600,
    color: '#94a3b8',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
    display: 'flex',
    alignItems: 'center',
  },
  gridRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '12px',
    marginBottom: '8px',
  },
  statRow: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '8px 12px',
    fontSize: '13px',
    background: 'rgba(51,65,85,0.2)',
    borderRadius: '6px',
    border: '1px solid rgba(148,163,184,0.08)',
  },
  statLabel: {
    color: '#cbd5e1',
    fontSize: '13px',
  },
  statValue: {
    fontWeight: 600,
    color: '#e2e8f0',
    fontSize: '13px',
  },
  subsection: {
    marginBottom: '14px',
    paddingBottom: '14px',
    borderBottom: '1px solid rgba(148,163,184,0.15)',
  },
  subsectionLabel: {
    fontSize: '11px',
    color: '#94a3b8',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
    marginBottom: '8px',
    fontWeight: 600,
  },
};
