/**
 * StoryEventCard - one deterministic world fact in the Board feed (U7/E4).
 *
 * Deliberately distinct from CommentaryCard: a story event is something the
 * simulation *did*, measured by a detector with an explicit threshold, whereas
 * a comment is something an agent *thinks*. The card carries a WORLD EVENT
 * badge, the detector's own before/after numbers, and no reaction bar - you do
 * not react to a measurement.
 *
 * Two honesty rules the card enforces:
 *
 * - **Replay.** A "watch" affordance appears only when `replay_ref` resolves to
 *   retained replay data. Nothing sets it today, so the card shows the frame
 *   instead of pretending replay exists.
 * - **Entities.** The inspect action is offered only for an entity still in the
 *   live world; otherwise the card says the fish is gone rather than opening an
 *   inspector onto nothing.
 */

import type { StoryEvent } from '../types/story';
import { severityStyle } from '../utils/commentaryDisplay';
import {
    describeChange,
    describeThreshold,
    formatSimulationTime,
    storyEventMeta,
} from '../utils/storyEventDisplay';
import styles from './StoryEventCard.module.css';

interface StoryEventCardProps {
    event: StoryEvent;
    /** Ids present in the latest reconciled world state. */
    liveEntityIds?: ReadonlySet<number>;
    /** Opens the U4 inspector. Omitted when no inspector is available. */
    onInspectEntity?: (entityId: number) => void;
}

export function StoryEventCard({ event, liveEntityIds, onInspectEntity }: StoryEventCardProps) {
    const sev = severityStyle(event.severity);
    const meta = storyEventMeta(event.event_type);
    const change = describeChange(event);
    const threshold = describeThreshold(event);

    const involved = event.entity_ids ?? [];
    const stillLive = liveEntityIds
        ? involved.filter((id) => liveEntityIds.has(id))
        : [];
    // Only claim an entity is gone once we actually know what is live.
    const allGone = Boolean(liveEntityIds) && involved.length > 0 && stillLive.length === 0;
    const canInspect = Boolean(onInspectEntity) && stillLive.length > 0;

    return (
        <div
            className={styles.card}
            style={{ borderLeftColor: sev.color }}
            data-testid="story-event-card"
            data-event-type={event.event_type}
        >
            <div className={styles.header}>
                <span className={styles.icon} aria-hidden="true">{meta.icon}</span>
                <span className={styles.badge}>World event</span>
                <span className={styles.kind}>{meta.label}</span>
                {/* Severity in words as well as colour - never colour alone. */}
                <span className={styles.severity} style={{ color: sev.color }}>
                    {sev.icon} {event.severity}
                </span>
                <span className={styles.clock} title={`Simulation frame ${event.frame}`}>
                    {formatSimulationTime(event.simulation_time)}
                </span>
            </div>

            <p className={styles.title}>{event.title}</p>

            {change && <p className={styles.change}>{change}</p>}

            <div className={styles.footer}>
                <span className={styles.detector} title={threshold ? `Threshold: ${threshold}` : undefined}>
                    {event.detector_name}
                    {threshold && <span className={styles.threshold}> · {threshold}</span>}
                </span>

                {event.lineage_ids?.length > 0 && (
                    <span className={styles.lineage}>
                        lineage {event.lineage_ids.join(', ')}
                    </span>
                )}

                {canInspect && (
                    <button
                        type="button"
                        className={styles.inspect}
                        onClick={() => onInspectEntity?.(stillLive[0])}
                    >
                        Inspect fish #{stillLive[0]}
                    </button>
                )}

                {allGone && (
                    <span className={styles.gone}>
                        {involved.length === 1
                            ? `Fish #${involved[0]} has left the tank`
                            : 'These fish have left the tank'}
                    </span>
                )}

                {/* No replay_ref means no replay data. Show the frame instead of
                    offering a "watch" button that could not do anything. */}
                <span className={styles.frame}>frame {event.frame}</span>
            </div>
        </div>
    );
}
