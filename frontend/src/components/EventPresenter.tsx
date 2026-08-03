import type { SoccerMatchState } from '../types/simulation';
import { formatSimulationClock } from './formatSimulationClock';
import { EventToast } from './EventToast';
import { GoalCard } from './GoalCard';
import { eventLabel, participantName, presentEvents, type BroadcastEvent, type SoccerBroadcastMatch } from './soccerEvents';
import styles from './SoccerEvents.module.css';

interface EventPresenterProps {
    match: SoccerMatchState | null;
    reducedMotion?: boolean;
}

function broadcastMatch(match: SoccerMatchState): SoccerBroadcastMatch {
    return match as SoccerBroadcastMatch;
}

function StateCard({ event, match }: { event: BroadcastEvent; match: SoccerBroadcastMatch }) {
    const label = eventLabel(event);
    const actor = participantName(match, event.actor);
    const detail = event.kind === 'half_time'
        ? 'Teams switch attacking directions.'
        : event.kind === 'full_time'
            ? `${match.score.left} – ${match.score.right} · ${formatSimulationClock(match.frame)}`
            : actor ?? 'The match is continuing.';
    return (
        <article className={styles.eventStateCard} data-testid={`soccer-${event.kind.replace('_', '-')}-card`}>
            <strong>{label}</strong>
            <span>{detail}</span>
        </article>
    );
}

export function EventPresenter({ match, reducedMotion = false }: EventPresenterProps) {
    if (!match) return null;
    const current = broadcastMatch(match);
    const presented = presentEvents((current.events ?? []) as BroadcastEvent[], current.frame);
    const major = presented.major;
    const stateMajor = major?.kind === 'half_time' || major?.kind === 'full_time' || major?.kind === 'breakthrough';
    return (
        <div className={styles.eventPresenter} data-testid="soccer-event-presenter" aria-live="polite">
            {major?.kind === 'goal' && <GoalCard event={major} match={current} reducedMotion={reducedMotion} />}
            {stateMajor && <StateCard event={major} match={current} />}
            {!major && presented.notable.length > 0 && (
                <div className={styles.toastStack}>
                    {presented.notable.map((event) => <EventToast key={`${event.event_id ?? event.seq}`} event={event} match={current} reducedMotion={reducedMotion} />)}
                </div>
            )}
            {presented.collapsedNotable > 0 && <span className={styles.collapsedNotice}>{presented.collapsedNotable} event{presented.collapsedNotable === 1 ? '' : 's'} in timeline</span>}
        </div>
    );
}
