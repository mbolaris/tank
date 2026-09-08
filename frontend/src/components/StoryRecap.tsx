/**
 * StoryRecap - "Since your last visit" (U8a/E5).
 *
 * Shows what the tank did while this viewer was away, computed from the story
 * events after their stored last-seen id. Everything it says comes from the
 * detector records themselves: counts, the measured before/after numbers, and
 * the frame span. It never asserts that one event caused another, because the
 * records do not establish that.
 *
 * The card appears only when there is genuinely something missed. A first
 * visit, cleared storage, or a quiet absence renders nothing at all rather
 * than an empty "welcome back" with no content behind it.
 */

import { useMemo, useState } from 'react';
import type { StoryEvent } from '../types/story';
import { buildRecap, headlineEvent, summarizeCounts } from '../utils/storyRecap';
import { formatSimulationTime } from '../utils/storyEventDisplay';
import { StoryEventCard } from './StoryEventCard';
import styles from './StoryRecap.module.css';

interface StoryRecapProps {
    events: StoryEvent[];
    /** The viewer's stored high-water mark; null on a first visit. */
    baselineId: number | null;
    /** Frozen upper bound, so live arrivals do not grow the recap. */
    ceilingId: number | null;
    /** Persist the new high-water mark. */
    onDismiss: (ceilingId: number) => void;
    liveEntityIds?: ReadonlySet<number>;
    onInspectEntity?: (entityId: number) => void;
}

export function StoryRecap({
    events,
    baselineId,
    ceilingId,
    onDismiss,
    liveEntityIds,
    onInspectEntity,
}: StoryRecapProps) {
    const [dismissed, setDismissed] = useState(false);
    const [expanded, setExpanded] = useState(false);

    const recap = useMemo(
        () => buildRecap(events, baselineId, ceilingId),
        [events, baselineId, ceilingId],
    );

    if (!recap || dismissed) return null;

    const headline = headlineEvent(recap);
    const counts = summarizeCounts(recap);
    // A single event happened at a moment, not across a range; rendering
    // "1:40 – 1:40" just makes the reader check whether it is a typo.
    const from = formatSimulationTime(recap.fromTime);
    const to = formatSimulationTime(recap.toTime);
    const span = recap.events.length === 0 ? null : from === to ? from : `${from} – ${to}`;

    const handleDismiss = () => {
        setDismissed(true);
        onDismiss(recap.ceilingId);
    };

    return (
        <section className={styles.recap} aria-label="Since your last visit" data-testid="story-recap">
            <div className={styles.header}>
                <h3 className={styles.title}>Since your last visit</h3>
                {span && <span className={styles.span}>{span}</span>}
                <button
                    type="button"
                    className={styles.dismiss}
                    onClick={handleDismiss}
                    data-testid="story-recap-dismiss"
                >
                    Mark as seen
                </button>
            </div>

            {counts && <p className={styles.counts}>{counts}</p>}

            {/* Stated plainly rather than hidden: the buffer is bounded, and a
                recap that silently omitted dropped records would understate
                what the viewer missed. */}
            {recap.missingCount > 0 && (
                <p className={styles.gap} data-testid="story-recap-gap">
                    {recap.missingCount} earlier event{recap.missingCount === 1 ? '' : 's'} from
                    this period {recap.missingCount === 1 ? 'is' : 'are'} no longer retained.
                </p>
            )}

            {headline && (
                <StoryEventCard
                    event={headline}
                    liveEntityIds={liveEntityIds}
                    onInspectEntity={onInspectEntity}
                />
            )}

            {recap.events.length > 1 && (
                <>
                    <button
                        type="button"
                        className={styles.toggle}
                        aria-expanded={expanded}
                        onClick={() => setExpanded((open) => !open)}
                        data-testid="story-recap-toggle"
                    >
                        {expanded
                            ? 'Hide the rest'
                            : `Show ${recap.events.length - 1} more event${recap.events.length - 1 === 1 ? '' : 's'}`}
                    </button>
                    {expanded && (
                        <div className={styles.rest}>
                            {recap.events
                                .filter((event) => event.id !== headline?.id)
                                .map((event) => (
                                    <StoryEventCard
                                        key={event.id}
                                        event={event}
                                        liveEntityIds={liveEntityIds}
                                        onInspectEntity={onInspectEntity}
                                    />
                                ))}
                        </div>
                    )}
                </>
            )}
        </section>
    );
}
