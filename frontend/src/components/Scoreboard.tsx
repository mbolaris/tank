import type { SoccerMatchState } from '../types/simulation';
import { MatchClock } from './MatchClock';
import type { ArenaPresentation } from './soccerArenaState';
import { TeamBlock } from './TeamBlock';
import styles from './SoccerScoreboard.module.css';

interface ScoreboardProps {
    match: SoccerMatchState | null;
    presentation: ArenaPresentation;
    unknownStage?: string;
    skippedReason?: string;
    errorMessage?: string;
    /**
     * §4.1: Tactical compresses the scoreboard to 44 px, score and clock only.
     *
     * The stage and status lines are *hidden*, not unmounted, so the state
     * machine (§8) keeps driving the same DOM and switching modes cannot
     * change what state the arena believes it is in.
     */
    compact?: boolean;
}

const STATUS_LABELS: Record<ArenaPresentation, string> = {
    empty: '● IDLE',
    loading: '◌ WARMING UP',
    live: '● LIVE',
    paused: '❚❚ PAUSED',
    halftime: 'HALF TIME',
    finished: 'FULL TIME',
    disconnected: '⚠ DISCONNECTED',
    skipped: 'MATCH SKIPPED',
    error: 'ARENA ERROR',
};

function stageLabel(match: SoccerMatchState | null, presentation: ArenaPresentation, unknownStage?: string): string {
    if (unknownStage) return unknownStage;
    if (!match) return presentation === 'empty' ? 'SOCCER LEAGUE · IDLE' : 'SOCCER LEAGUE';
    if (match.league_round !== undefined) return `LEAGUE · ROUND ${match.league_round}`;
    return 'FRIENDLY';
}

export function Scoreboard({ match, presentation, unknownStage, skippedReason, errorMessage, compact = false }: ScoreboardProps) {
    const home = match?.home_name || match?.home_id || 'Home';
    const away = match?.away_name || match?.away_id || 'Away';
    const leftScore = match?.score.left ?? 0;
    const rightScore = match?.score.right ?? 0;
    const status = STATUS_LABELS[presentation];
    // Held stale data must not read as a live match ticking along.
    const clockStopped = presentation === 'disconnected';

    return (
        <section
            className={`${styles.scoreboard}${compact ? ` ${styles.compact}` : ''}`}
            data-testid="soccer-scoreboard"
            data-compact={compact ? 'true' : undefined}
            aria-label="Soccer scoreboard"
        >
            <TeamBlock match={match} side="left" name={home} score={leftScore} />
            <div className={styles.centerBlock}>
                <div className={styles.scoreLine}>
                    <span className={styles.score}>{leftScore}</span>
                    <span className={styles.scoreDivider}>–</span>
                    <span className={styles.score}>{rightScore}</span>
                </div>
                <div className={`${styles.clock}${clockStopped ? ` ${styles.clockStopped}` : ''}`}>
                    <MatchClock frame={match?.frame} stopped={clockStopped} />
                </div>
                <div className={styles.stage}>{stageLabel(match, presentation, unknownStage)}</div>
                <div className={`${styles.status} ${styles[`status${presentation[0].toUpperCase()}${presentation.slice(1)}`]}`}>
                    {status}
                </div>
            </div>
            <TeamBlock match={match} side="right" name={away} score={rightScore} />
            {(skippedReason || errorMessage) && (
                <p className={styles.stateMessage}>{skippedReason || errorMessage}</p>
            )}
        </section>
    );
}
