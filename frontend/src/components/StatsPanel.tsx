/**
 * Stats panel component showing ecosystem statistics
 */

import type { StatsData } from '../types/simulation';
import { Panel, CollapsibleSection, StatRow } from './ui';
import { getEnergyColor } from '../utils/energy';
import styles from './StatsPanel.module.css';

interface StatsPanelProps {
  stats: StatsData | null;
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
  const avgEnergy = stats.fish_count > 0 ? stats.total_energy / stats.fish_count : 0;

  return (
    <Panel title="Statistics">
      <div className={styles.highlightGrid}>
        <div className={styles.highlightCard}>
          <p className={styles.highlightLabel}>Generation</p>
          <p className={styles.highlightValue}>{stats.generation}</p>
        </div>
        <div className={styles.highlightCard}>
          <p className={styles.highlightLabel}>Avg Energy</p>
          <p
            className={styles.highlightValue}
            style={{ color: getEnergyColor(avgEnergy) }}
          >
            {avgEnergy.toFixed(1)}
          </p>
        </div>
        <div className={styles.highlightCard}>
          <p className={styles.highlightLabel}>Time</p>
          <p className={styles.highlightValue}>{stats.time}</p>
        </div>
      </div>

      {/* Ecosystem */}
      <CollapsibleSection title="Ecosystem" defaultExpanded>
        <div className={styles.gridRow}>
          <StatRow label="Capacity:" value={stats.capacity} />
          <StatRow label="Energy Reserve:" value={Math.round(stats.total_energy).toLocaleString()} />
        </div>
        <div className={styles.gridRow}>
          <StatRow label="Food:" value={stats.food_count} />
          <StatRow label="Plants:" value={stats.plant_count} />
        </div>
      </CollapsibleSection>

      {/* Population */}
      <CollapsibleSection title="Population" defaultExpanded={false}>
        <div className={styles.gridRow}>
          <StatRow label="Fish Alive:" value={stats.fish_count} />
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
              <div className={styles.gridRow}>
                <StatRow label="Games:" value={stats.poker_stats.total_games} />
                <StatRow
                  label="Win Rate:"
                  value={stats.poker_stats.win_rate_pct || '0.0%'}
                  valueColor={(stats.poker_stats.win_rate || 0) > 0.5 ? '#4ade80' : '#94a3b8'}
                />
              </div>
              <div className={styles.gridRow}>
                <StatRow
                  label="Net Energy:"
                  value={`${stats.poker_stats.net_energy >= 0 ? '+' : ''}${stats.poker_stats.net_energy.toFixed(1)}`}
                  valueColor={stats.poker_stats.net_energy >= 0 ? '#4ade80' : '#f87171'}
                  valueStyle={{ fontWeight: 600 }}
                />
                <StatRow
                  label="ROI:"
                  value={stats.poker_stats.roi !== undefined ? (stats.poker_stats.roi >= 0 ? '+' : '') + stats.poker_stats.roi.toFixed(2) : '0.00'}
                  valueColor={(stats.poker_stats.roi || 0) >= 0 ? '#4ade80' : '#f87171'}
                />
              </div>
              <div className={styles.gridRow}>
                <StatRow label="Showdown:" value={stats.poker_stats.showdown_win_rate || '0.0%'} />
                <StatRow
                  label="Aggression:"
                  value={stats.poker_stats.aggression_factor !== undefined ? stats.poker_stats.aggression_factor.toFixed(2) : '0.00'}
                />
              </div>
              <div className={styles.gridRow}>
                <StatRow label="VPIP:" value={stats.poker_stats.vpip_pct || '0.0%'} />
                <StatRow label="Best Hand:" value={stats.poker_stats.best_hand_name} />
              </div>
            </>
          )}
        </CollapsibleSection>
      )}
    </Panel>
  );
}
