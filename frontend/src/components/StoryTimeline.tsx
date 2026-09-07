/**
 * StoryTimeline - a compact, keyboard-navigable timeline of world events (U7/E4).
 *
 * Sits under the canvas and plots E3 story events against the run's own
 * simulation clock, so a viewer can see *when* the tank did something without
 * opening the Board. Selecting a marker opens the detail card beneath the
 * track, which can link straight into the U4 inspector.
 *
 * Three details the U7 acceptance bar turns on:
 *
 * - **Aggregation.** Markers closer together than MIN_SEPARATION_PCT of the
 *   track collapse into one cluster carrying a count, so a burst of events in a
 *   few hundred frames does not become an unreadable smear of overlapping dots.
 * - **Keyboard.** The track is a listbox with roving tabindex: one stop in the
 *   page's tab order, then Arrow/Home/End to move between markers. Tabbing
 *   through forty individual dots would technically be "navigable" and horrible.
 * - **Not colour alone.** Every marker states its severity and kind in its
 *   accessible name, and the selected detail card repeats both as text.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { StoryEvent } from '../types/story';
import { severityStyle } from '../utils/commentaryDisplay';
import { formatSimulationTime, storyEventMeta } from '../utils/storyEventDisplay';
import { StoryEventCard } from './StoryEventCard';
import { clusterEvents } from '../utils/storyFeed';
import styles from './StoryTimeline.module.css';

interface StoryTimelineProps {
    events: StoryEvent[];
    /** The run's current frame; anchors the track's right edge. */
    currentFrame: number;
    liveEntityIds?: ReadonlySet<number>;
    onInspectEntity?: (entityId: number) => void;
}

export function StoryTimeline({
    events,
    currentFrame,
    liveEntityIds,
    onInspectEntity,
}: StoryTimelineProps) {
    const [activeIndex, setActiveIndex] = useState<number | null>(null);
    const markerRefs = useRef<(HTMLButtonElement | null)[]>([]);

    const maxFrame = useMemo(
        () => Math.max(currentFrame, ...events.map((e) => e.frame), 1),
        [currentFrame, events],
    );
    const clusters = useMemo(() => clusterEvents(events, maxFrame), [events, maxFrame]);

    // Clusters re-form as events arrive; keep the selection in range rather
    // than pointing at an index that no longer exists.
    useEffect(() => {
        setActiveIndex((current) => {
            if (current === null) return null;
            return current < clusters.length ? current : null;
        });
    }, [clusters.length]);

    const focusMarker = useCallback((index: number) => {
        setActiveIndex(index);
        markerRefs.current[index]?.focus();
    }, []);

    const handleKeyDown = useCallback(
        (event: React.KeyboardEvent<HTMLButtonElement>, index: number) => {
            const last = clusters.length - 1;
            switch (event.key) {
                case 'ArrowRight':
                case 'ArrowDown':
                    event.preventDefault();
                    focusMarker(Math.min(last, index + 1));
                    break;
                case 'ArrowLeft':
                case 'ArrowUp':
                    event.preventDefault();
                    focusMarker(Math.max(0, index - 1));
                    break;
                case 'Home':
                    event.preventDefault();
                    focusMarker(0);
                    break;
                case 'End':
                    event.preventDefault();
                    focusMarker(last);
                    break;
                case 'Escape':
                    event.preventDefault();
                    setActiveIndex(null);
                    break;
                default:
                    break;
            }
        },
        [clusters.length, focusMarker],
    );

    if (events.length === 0) {
        return (
            <div className={styles.timeline} data-testid="story-timeline">
                <div className={styles.heading}>
                    <h3 className={styles.title}>Living history</h3>
                    <span className={styles.count}>no events yet</span>
                </div>
                <p className={styles.empty}>
                    Milestones appear here as the tank reaches them — a population
                    collapse, a new generation, a lineage taking over.
                </p>
            </div>
        );
    }

    const active = activeIndex !== null ? clusters[activeIndex] : null;
    // Roving tabindex: exactly one marker is in the tab order at a time.
    const tabIndexFor = (index: number) =>
        (activeIndex === null ? index === clusters.length - 1 : activeIndex === index) ? 0 : -1;

    return (
        <div className={styles.timeline} data-testid="story-timeline">
            <div className={styles.heading}>
                <h3 className={styles.title}>Living history</h3>
                <span className={styles.count}>
                    {events.length} event{events.length === 1 ? '' : 's'}
                </span>
            </div>

            <div
                className={styles.track}
                role="listbox"
                aria-label="World event timeline"
                aria-orientation="horizontal"
            >
                <div className={styles.rail} aria-hidden="true" />
                {clusters.map((cluster, index) => {
                    const newest = cluster.events[0];
                    const meta = storyEventMeta(newest.event_type);
                    const sev = severityStyle(newest.severity);
                    const isActive = activeIndex === index;
                    const label =
                        cluster.events.length > 1
                            ? `${cluster.events.length} events around ${formatSimulationTime(newest.simulation_time)}, latest ${meta.label}, severity ${newest.severity}`
                            : `${meta.label} at ${formatSimulationTime(newest.simulation_time)}, severity ${newest.severity}`;
                    return (
                        <button
                            key={`${newest.id}-${index}`}
                            ref={(node) => { markerRefs.current[index] = node; }}
                            type="button"
                            role="option"
                            aria-selected={isActive}
                            aria-label={label}
                            title={label}
                            tabIndex={tabIndexFor(index)}
                            className={`${styles.marker} ${isActive ? styles.markerActive : ''}`}
                            style={{ left: `${cluster.pct}%` }}
                            data-testid="story-timeline-marker"
                            data-count={cluster.events.length}
                            onKeyDown={(e) => handleKeyDown(e, index)}
                            onClick={() => setActiveIndex(isActive ? null : index)}
                        >
                            <span className={styles.dot} style={{ background: sev.color }} aria-hidden="true" />
                            {cluster.events.length > 1 && (
                                <span className={styles.clusterCount} aria-hidden="true">
                                    {cluster.events.length}
                                </span>
                            )}
                        </button>
                    );
                })}
            </div>

            <div className={styles.scale} aria-hidden="true">
                <span>0:00</span>
                <span>now</span>
            </div>

            {active && (
                <div className={styles.detail}>
                    {active.events.map((event) => (
                        <StoryEventCard
                            key={event.id}
                            event={event}
                            liveEntityIds={liveEntityIds}
                            onInspectEntity={onInspectEntity}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}
