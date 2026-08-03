import type { SoccerLeagueLiveState, SoccerEventData } from '../../types/simulation';
import styles from './TankSoccerTab.module.css';

interface TankSoccerTabProps {
    liveState: SoccerLeagueLiveState | null;
    events: SoccerEventData[];
    currentFrame: number;
    worldId?: string;
    onOpenArena?: () => void;
}

export function TankSoccerTab({ liveState, events, onOpenArena }: TankSoccerTabProps) {
    const activeMatch = liveState?.active_match ?? null;
    const completedMatches = events.filter((event) => !event.skipped).length;

    return (
        <div className={styles.soccerTab}>
            <div className="glass-panel" style={{ padding: '16px' }}>
                <div className={styles.previewHeader}>
                    <div>
                        <div className={styles.previewEyebrow}>Dedicated venue</div>
                        <h2 className={styles.previewTitle}>Soccer Arena</h2>
                    </div>
                    <span className={`${styles.statusBadge} ${activeMatch ? styles.statusLive : styles.statusIdle}`}>
                        {activeMatch ? 'Live' : 'Idle'}
                    </span>
                </div>
                <div className={styles.previewBody}>
                    <div>
                        <p className={styles.previewDescription}>
                            {activeMatch
                                ? `${activeMatch.home_name || activeMatch.home_id || 'Home'} vs ${activeMatch.away_name || activeMatch.away_id || 'Away'}`
                                : 'Open the full-width venue to watch the next fixture.'}
                        </p>
                        <div className={styles.previewMeta}>
                            <span>{completedMatches} completed match{completedMatches === 1 ? '' : 'es'}</span>
                            <span>{liveState?.leaderboard.length ?? 0} teams in standings</span>
                        </div>
                    </div>
                    <button type="button" className={styles.openArenaButton} onClick={onOpenArena} disabled={!onOpenArena}>
                        Open Arena <span aria-hidden="true">→</span>
                    </button>
                </div>
            </div>
        </div>
    );
}
