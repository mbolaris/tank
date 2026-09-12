import type { EntityData } from '../types/simulation';
import type { StoryEvent } from '../types/story';
import { useCinematicDirector } from '../hooks/useCinematicDirector';
import { usePrefersReducedMotion } from '../hooks/usePrefersReducedMotion';
import styles from './CinematicDirector.module.css';

/**
 * Human wording for each detector output. The backend `title` already reads
 * well, so this is the *eyebrow* above it - what kind of moment this is - not a
 * replacement for the event's own words.
 */
const EVENT_LABELS: Record<StoryEvent['event_type'], string> = {
    population_danger: 'Population crisis',
    population_recovered: 'Recovery',
    generation_milestone: 'New generation',
    lineage_dominant: 'Lineage rising',
};

const SEVERITY_CLASS: Partial<Record<StoryEvent['severity'], string>> = {
    warning: styles.captionWarning,
    concern: styles.captionConcern,
    insight: styles.captionInsight,
};

interface CinematicDirectorProps {
    enabled: boolean;
    onToggle: () => void;
    events: readonly StoryEvent[];
    entities: readonly EntityData[];
    selectedEntityId: number | null;
    onFollow: (entityId: number, entityType: string) => void;
    onRelease: () => void;
}

/**
 * Opt-in auto-camera: follows whoever the world just did something to and
 * captions it, then gives the tank back. Owns its own toggle so that turning it
 * on and seeing what it does are the same piece of screen.
 */
export function CinematicDirector({
    enabled,
    onToggle,
    events,
    entities,
    selectedEntityId,
    onFollow,
    onRelease,
}: CinematicDirectorProps) {
    const reducedMotion = usePrefersReducedMotion();
    const { shot } = useCinematicDirector({
        enabled,
        events,
        entities,
        selectedEntityId,
        onFollow,
        onRelease,
        reducedMotion,
    });

    const subject = shot?.entityId != null
        ? entities.find((entity) => entity.id === shot.entityId) ?? null
        : null;

    return (
        <>
            <button
                type="button"
                className={`${styles.toggle} ${enabled ? styles.toggleOn : ''}`}
                onClick={onToggle}
                aria-pressed={enabled}
                title={
                    enabled
                        ? 'Stop following the story automatically'
                        : 'Let the camera follow notable moments as they happen'
                }
            >
                <span className={styles.dot} aria-hidden="true" />
                Director
            </button>

            {shot && (
                <div
                    className={`${styles.caption} ${SEVERITY_CLASS[shot.severity] ?? ''}`}
                    role="status"
                    aria-live="polite"
                >
                    <div className={styles.eyebrow}>{EVENT_LABELS[shot.eventType] ?? 'Moment'}</div>
                    <div className={styles.title}>{shot.title}</div>
                    {subject && (
                        <div className={styles.subject}>
                            Following {String(subject.common_name || subject.taxonomy?.common_name || 'this fish')} #{subject.id}
                            {reducedMotion ? ' — camera held still for reduced motion' : ''}
                        </div>
                    )}
                </div>
            )}
        </>
    );
}
