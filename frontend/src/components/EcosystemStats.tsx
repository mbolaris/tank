/**
 * Ecosystem statistics component
 * Displays non-poker stats below the tank simulation
 */

import type { StatsData } from '../types/simulation';
import styles from './EcosystemStats.module.css';

interface EcosystemStatsProps {
  stats: StatsData | null;
}

export function EcosystemStats({ stats }: EcosystemStatsProps) {
  if (!stats) {
    return null;
  }

  const deathCauseEntries = Object.entries(stats.death_causes);

  return (
    <div className={styles.container}>
      <div className={styles.section}>
        <div className={styles.sectionTitle}>Ecosystem</div>
        <div className={styles.statsGrid}>
          <div className={styles.statItem}>
            <span className={styles.label}>Food:</span>
            <span className={styles.value}>{stats.food_count}</span>
          </div>
        </div>
      </div>

      <div className={styles.section}>
        <div className={styles.sectionTitle}>Population</div>
        <div className={styles.statsGrid}>
          <div className={styles.statItem}>
            <span className={styles.label}>Fish Alive:</span>
            <span className={styles.value}>{stats.fish_count}</span>
          </div>
          <div className={styles.statItem}>
            <span className={styles.label}>Total Births:</span>
            <span className={styles.value}>{stats.births}</span>
          </div>
          <div className={styles.statItem}>
            <span className={styles.label}>Total Deaths:</span>
            <span className={styles.value}>{stats.deaths}</span>
          </div>
        </div>
      </div>

      {deathCauseEntries.length > 0 && (
        <div className={styles.section}>
          <div className={styles.sectionTitle}>Death Causes</div>
          <div className={styles.statsGrid}>
            {deathCauseEntries.map(([cause, count]) => (
              <div key={cause} className={styles.statItem}>
                <span className={styles.label}>{cause}:</span>
                <span className={styles.value}>{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
