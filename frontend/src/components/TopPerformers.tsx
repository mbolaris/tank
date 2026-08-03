import type { SoccerFishLeaderEntry } from '../types/simulation';
import styles from './TeamProgressPanel.module.css';

export function TopPerformers({ leaders }: { leaders: SoccerFishLeaderEntry[] }) {
    if (!leaders.length) return <div className={styles.emptySection}>No individual match records yet.</div>;
    return (
        <div className={styles.performers} data-testid="soccer-top-performers">
            {leaders.slice(0, 3).map((leader, index) => (
                <div className={styles.performer} key={leader.fish_id}>
                    <span className={styles.performerRank}>{index + 1}</span>
                    <span>Fish #{leader.fish_id}</span>
                    <span className={styles.performerStats}>{leader.goals}g · {leader.assists}a</span>
                </div>
            ))}
        </div>
    );
}
