/**
 * Stats panel component showing poker statistics
 */

import type { StatsData } from '../types/simulation';
import { Panel, StatRow } from './ui';
import styles from './StatsPanel.module.css';

interface StatsPanelProps {
  stats: StatsData | null;
}

export function StatsPanel({ stats }: StatsPanelProps) {
  if (!stats) {
    return (
      <Panel title="Poker Stats">
        <p className={styles.noData}>Waiting for data...</p>
      </Panel>
    );
  }

  const winRate = stats.poker_stats ? (stats.poker_stats.win_rate || 0) * 100 : 0;

  return (
    <Panel title={`Poker Stats ${stats.poker_stats && stats.poker_stats.total_games > 0 ? `(${winRate.toFixed(0)}% WR)` : ''}`}>
      {!stats.poker_stats || stats.poker_stats.total_games === 0 ? (
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
    </Panel>
  );
}
