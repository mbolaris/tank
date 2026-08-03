import type { SoccerLeagueLiveState, SoccerMatchState } from '../types/simulation';
import type { ArenaPresentation } from './soccerArenaState';
import styles from './SoccerScoreboard.module.css';

export function SoccerProgressStrip({
    liveState,
    match,
    presentation,
}: {
    liveState: SoccerLeagueLiveState | null;
    match: SoccerMatchState | null;
    presentation: ArenaPresentation;
}) {
    const players = match?.entities.filter((entity) => entity.type === 'player').length;
    const details = match
        ? `${players ?? 0} participants · SIM frame ${match.frame}${match.league_round === undefined ? '' : ` · Round ${match.league_round}`}`
        : `${liveState?.leaderboard.length ?? 0} teams in standings · Awaiting next fixture`;
    return (
        <div className={styles.progressStrip} data-testid="soccer-progress-strip" aria-label="Soccer match progress">
            <span className={`${styles.progressDot} ${presentation === 'live' ? styles.progressDotLive : ''}`} aria-hidden="true" />
            <span>{details}</span>
            <span className={styles.progressState}>{presentation.replace('_', ' ')}</span>
        </div>
    );
}
