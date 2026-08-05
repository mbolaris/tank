import type { SoccerMatchState } from '../types/simulation';
import { formatSimulationClock } from './formatSimulationClock';
import { dedupeEvents, eventLabel, participantName, teamName, type BroadcastEvent, type SoccerBroadcastMatch } from './soccerEvents';
import styles from './MatchTimeline.module.css';

/** Newest first, so the most recent moment is visible without scrolling. */
const MAX_TIMELINE_ROWS = 40;

function describe(match: SoccerBroadcastMatch, event: BroadcastEvent): string {
    const actor = participantName(match, event.actor);
    const assist = participantName(match, event.assist);
    if (event.kind === 'goal') {
        const scorer = actor ?? teamName(match, event.side);
        return assist ? `${scorer} (assist ${assist})` : scorer;
    }
    if (event.side) return teamName(match, event.side);
    return actor ?? '';
}

/**
 * §3.1: in Tactical there are **no field-covering overlays at all** - cards
 * route here instead. The same list backs Analysis mode's timeline.
 */
export function MatchTimeline({ match }: { match: SoccerMatchState | null }) {
    const broadcast = match as SoccerBroadcastMatch | null;
    const events = broadcast?.events?.length ? dedupeEvents(broadcast.events as BroadcastEvent[]) : [];
    const rows = events.slice(-MAX_TIMELINE_ROWS).reverse();

    return (
        <div className={styles.timeline} data-testid="soccer-match-timeline">
            <div className={styles.heading}>
                <h3>Match timeline</h3>
                <span className={styles.count}>{events.length || 'no'} event{events.length === 1 ? '' : 's'}</span>
            </div>
            {!rows.length ? (
                <p className={styles.empty}>Events appear here as the match unfolds.</p>
            ) : (
                <ol className={styles.rows}>
                    {rows.map((event) => (
                        <li key={event.event_id ?? `${event.seq}:${event.frame}`} className={styles.row}>
                            <span className={styles.clock}>{formatSimulationClock(event.frame, 10)}</span>
                            <span className={styles.kind} data-kind={event.kind}>{eventLabel(event)}</span>
                            <span className={styles.detail}>{broadcast ? describe(broadcast, event) : ''}</span>
                        </li>
                    ))}
                </ol>
            )}
        </div>
    );
}
