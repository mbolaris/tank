import { formatSimulationClock } from './formatSimulationClock';
import type { BroadcastEvent, SoccerBroadcastMatch } from './soccerEvents';
import { participantName, teamName } from './soccerEvents';
import styles from './SoccerEvents.module.css';

interface GoalCardProps {
    event: BroadcastEvent;
    match: SoccerBroadcastMatch;
    reducedMotion?: boolean;
}

export function GoalCard({ event, match, reducedMotion = false }: GoalCardProps) {
    const scorer = participantName(match, event.actor) ?? 'Unknown scorer';
    const assist = participantName(match, event.assist);
    return (
        <article className={`${styles.goalCard} ${reducedMotion ? styles.reducedMotion : ''}`} data-testid="soccer-goal-card">
            <div className={styles.eventKicker}>⚡ GOAL</div>
            <strong className={styles.goalTeam}>{teamName(match, event.side)} leads</strong>
            <div className={styles.goalScorer}>{scorer}</div>
            {assist && <div className={styles.goalAssist}>Assist: {assist}</div>}
            <div className={styles.goalMeta}>
                <span>{match.score.left} – {match.score.right}</span>
                <time>{formatSimulationClock(match.frame)}</time>
            </div>
        </article>
    );
}
