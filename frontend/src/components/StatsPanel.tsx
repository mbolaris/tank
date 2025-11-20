/**
 * Stats panel component showing ecosystem statistics
 */

import type { StatsData } from '../types/simulation';
import { Panel, CollapsibleSection, StatRow } from './ui';
import styles from './StatsPanel.module.css';

interface StatsPanelProps {
  stats: StatsData | null;
}

/**
 * Get color for total energy based on food spawning thresholds
 * Matches the dynamic food spawning system in core/constants.py
 */
function getEnergyColor(totalEnergy: number): string {
  if (totalEnergy < 2000) {
    return '#ef4444'; // Red - Critical/Starvation (double food spawn)
  } else if (totalEnergy < 4000) {
    return '#4ade80'; // Green - Normal (normal food spawn)
  } else if (totalEnergy < 6000) {
    return '#fbbf24'; // Yellow - High (reduced food spawn)
  } else {
    return '#fb923c'; // Orange - Very High (very reduced food spawn)
  }
}

export function StatsPanel({ stats }: StatsPanelProps) {
  if (!stats) {
    return (
      <Panel title="Statistics">
        <p className={styles.noData}>Waiting for data...</p>
      </Panel>
    );
  }

  const deathCauseEntries = Object.entries(stats.death_causes);
  const winRate = stats.poker_stats ? (stats.poker_stats.win_rate || 0) * 100 : 0;

  return (
    <Panel title="Statistics">
      {/* Summary Section */}
      <div className={styles.summaryCard}>
        <div className={styles.summaryGrid}>
          <div className={styles.summaryItem}>
            <div className={styles.summaryLabel}>Fish</div>
            <div className={styles.summaryValue}>{stats.fish_count}</div>
          </div>
          <div className={styles.summaryItem}>
            <div className={styles.summaryLabel}>Gen</div>
            <div className={styles.summaryValue}>{stats.generation}</div>
          </div>
          <div className={styles.summaryItem}>
            <div className={styles.summaryLabel}>Energy</div>
            <div className={styles.summaryValue} style={{ color: getEnergyColor(stats.total_energy) }}>
              {stats.total_energy.toFixed(0)}
            </div>
          </div>
          <div className={styles.summaryItem}>
            <div className={styles.summaryLabel}>Frame</div>
            <div className={styles.summaryValue}>{(stats.frame / 1000).toFixed(1)}k</div>
          </div>
        </div>
      </div>

      {/* Ecosystem & Time */}
      <CollapsibleSection title="Ecosystem" defaultExpanded={false}>
        <div className={styles.gridRow}>
          <StatRow label="Time:" value={stats.time} />
          <StatRow label="Frame:" value={stats.frame.toLocaleString()} />
        </div>
        <div className={styles.gridRow}>
          <StatRow label="Capacity:" value={stats.capacity} />
          <StatRow
            label="Total Energy:"
            value={stats.total_energy.toFixed(1)}
            valueColor={getEnergyColor(stats.total_energy)}
          />
        </div>
      </CollapsibleSection>

      {/* Population */}
      <CollapsibleSection title="Population">
        <div className={styles.gridRow}>
          <StatRow label="Fish:" value={stats.fish_count} />
          <StatRow label="Food:" value={stats.food_count} />
        </div>
        <div className={styles.gridRow}>
          <StatRow label="Plants:" value={stats.plant_count} />
        </div>
      </CollapsibleSection>

      {/* Genetics */}
      <CollapsibleSection title="Genetics">
        <div className={styles.gridRow}>
          <StatRow label="Generation:" value={stats.generation} />
          <StatRow label="Total Births:" value={stats.births} />
        </div>
        <div className={styles.gridRow}>
          <StatRow label="Total Deaths:" value={stats.deaths} />
        </div>
      </CollapsibleSection>

      {/* Death Causes */}
      {deathCauseEntries.length > 0 && (
        <CollapsibleSection title="Death Causes" defaultExpanded={false}>
          {deathCauseEntries.map(([cause, count]) => (
            <div key={cause} className={styles.statRow}>
              <StatRow label={`${cause}:`} value={count} />
            </div>
          ))}
        </CollapsibleSection>
      )}

      {/* Poker Stats */}
      {stats.poker_stats && (
        <CollapsibleSection title={`Poker Stats ${stats.poker_stats.total_games > 0 ? `(${winRate.toFixed(0)}% WR)` : ''}`}>
          {stats.poker_stats.total_games === 0 ? (
            <div className={styles.noPokerGames}>
              No poker games yet (fish need 10+ energy & to collide)
            </div>
          ) : (
            <>
              {/* Key Metrics */}
              <div className={styles.subsection}>
                <div className={styles.gridRow}>
                  <StatRow label="Games:" value={stats.poker_stats.total_games} />
                  <StatRow
                    label="W/L/T:"
                    value={`${stats.poker_stats.total_wins}/${stats.poker_stats.total_losses}/${stats.poker_stats.total_ties}`}
                  />
                </div>
                <div className={styles.gridRow}>
                  <StatRow
                    label="Win Rate:"
                    value={stats.poker_stats.win_rate_pct || '0.0%'}
                    valueColor={(stats.poker_stats.win_rate || 0) > 0.5 ? '#4ade80' : '#94a3b8'}
                  />
                  <StatRow
                    label="Net Energy:"
                    value={`${stats.poker_stats.net_energy >= 0 ? '+' : ''}${stats.poker_stats.net_energy.toFixed(1)}`}
                    valueColor={stats.poker_stats.net_energy >= 0 ? '#4ade80' : '#f87171'}
                    valueStyle={{ fontWeight: 600 }}
                  />
                </div>
              </div>

              {/* Performance */}
              <div className={styles.subsection}>
                <div className={styles.subsectionLabel}>Performance</div>
                <div className={styles.gridRow}>
                  <StatRow
                    label="ROI:"
                    value={stats.poker_stats.roi !== undefined ? (stats.poker_stats.roi >= 0 ? '+' : '') + stats.poker_stats.roi.toFixed(2) : '0.00'}
                    valueColor={(stats.poker_stats.roi || 0) >= 0 ? '#4ade80' : '#f87171'}
                  />
                  <StatRow label="Showdown:" value={stats.poker_stats.showdown_win_rate || '0.0%'} />
                </div>
              </div>

              {/* Playing Style */}
              <div className={styles.subsection}>
                <div className={styles.subsectionLabel}>Playing Style</div>
                <div className={styles.gridRow}>
                  <StatRow label="VPIP:" value={stats.poker_stats.vpip_pct || '0.0%'} />
                  <StatRow
                    label="Aggression:"
                    value={stats.poker_stats.aggression_factor !== undefined ? stats.poker_stats.aggression_factor.toFixed(2) : '0.00'}
                  />
                </div>
                <div className={styles.gridRow}>
                  <StatRow label="Fold Rate:" value={stats.poker_stats.avg_fold_rate || '0.0%'} />
                  <StatRow
                    label="Avg Hand:"
                    value={stats.poker_stats.avg_hand_rank !== undefined ? stats.poker_stats.avg_hand_rank.toFixed(2) : '0.00'}
                  />
                </div>
              </div>

              {/* Advanced */}
              <div className={styles.subsection}>
                <div className={styles.subsectionLabel}>Advanced</div>
                <div className={styles.gridRow}>
                  <StatRow label="Bluff Success:" value={stats.poker_stats.bluff_success_pct || '0.0%'} />
                  <StatRow
                    label="Position Edge:"
                    value={stats.poker_stats.positional_advantage_pct || '0.0%'}
                    valueColor={(stats.poker_stats.positional_advantage || 0) > 0 ? '#4ade80' : '#94a3b8'}
                  />
                </div>
                <div className={styles.gridRow}>
                  <StatRow
                    label="Pre/Post Folds:"
                    value={`${stats.poker_stats.preflop_folds || 0}/${stats.poker_stats.postflop_folds || 0}`}
                  />
                  <StatRow label="Best Hand:" value={stats.poker_stats.best_hand_name} />
                </div>
              </div>
            </>
          )}
        </CollapsibleSection>
      )}
    </Panel>
  );
}
