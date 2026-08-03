import type { BroadcastEvent, SoccerBroadcastMatch } from './soccerEvents';
import { eventLabel, participantName, teamName } from './soccerEvents';
import styles from './SoccerEvents.module.css';

interface EventToastProps {
    event: BroadcastEvent;
    match: SoccerBroadcastMatch;
    reducedMotion?: boolean;
}

export function EventToast({ event, match, reducedMotion = false }: EventToastProps) {
    const actor = participantName(match, event.actor);
    const detail = actor ? `${teamName(match, event.side)} · ${actor}` : teamName(match, event.side);
    return (
        <div className={`${styles.eventToast} ${reducedMotion ? styles.reducedMotion : ''}`} data-testid="soccer-event-toast">
            <strong>{eventLabel(event)}</strong>
            <span>{detail}</span>
        </div>
    );
}
