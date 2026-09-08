/**
 * "Since your last visit" recap (U8a/E5).
 *
 * Pure summarisation of the story events a viewer missed, computed from the
 * client's last-seen event id. All five acceptance cases U8a names are decided
 * here rather than in the component, so each one is pinned by a test:
 *
 * | case                   | behaviour                                          |
 * |------------------------|----------------------------------------------------|
 * | first visit            | no recap; the baseline is seeded silently           |
 * | cleared storage        | identical to a first visit - nothing is claimed     |
 * | expired buffer entries | the gap is counted and stated, never glossed over   |
 * | multiple worlds        | the baseline is per-world (see useLastSeenStoryEvent)|
 * | no new events          | no recap                                            |
 *
 * **The recap states what was measured and nothing more.** Detector records
 * establish that things happened, never that one caused another, so the
 * summary is a count and a list - it never joins two events with "because",
 * "so", or "after", and never orders them to imply a chain.
 */

import type { StoryEvent, StoryEventType } from '../types/story';
import { storyEventMeta } from './storyEventDisplay';

/** Severity ranking used only to pick which event leads the headline. */
const SEVERITY_RANK: Record<string, number> = {
    concern: 3,
    warning: 2,
    insight: 1,
    info: 0,
};

export interface StoryRecap {
    /** Events after the baseline, newest first. */
    events: StoryEvent[];
    /** How many events per type, for the deterministic summary line. */
    counts: Partial<Record<StoryEventType, number>>;
    /**
     * Events that happened after the baseline but are no longer retained.
     *
     * Story-event ids are dense and never reused, so a gap between the
     * baseline and the oldest event still held is exactly this many missing
     * records. Saying "nothing happened" when the buffer simply dropped them
     * would be a lie the recap can easily avoid telling.
     */
    missingCount: number;
    /** Simulation frames the recap spans. */
    fromFrame: number;
    toFrame: number;
    /**
     * The same span in simulated seconds, taken from the records themselves.
     *
     * Deliberately not re-derived from frames: the events already carry
     * ``simulation_time``, and recomputing it against a hardcoded frame rate
     * would silently disagree with the timestamps on the cards below.
     */
    fromTime: number;
    toTime: number;
    /** The highest id included; what to store when the viewer dismisses it. */
    ceilingId: number;
}

/**
 * Build a recap of everything after ``baselineId``.
 *
 * Returns ``null`` when there is nothing honest to show: no baseline yet (a
 * first visit or cleared storage), or no events past it.
 *
 * ``ceilingId`` freezes the upper bound at the moment the viewer arrived, so
 * events that arrive while they are watching belong to the live timeline
 * rather than silently growing a summary of the time they were away.
 */
export function buildRecap(
    events: StoryEvent[],
    baselineId: number | null,
    ceilingId: number | null = null,
): StoryRecap | null {
    // First visit or cleared storage: the viewer has not been away from
    // anything, so there is nothing to recap.
    if (baselineId === null) return null;

    const ceiling = ceilingId ?? Math.max(0, ...events.map((e) => e.id));
    const missed = events
        .filter((e) => e.id > baselineId && e.id <= ceiling)
        .sort((a, b) => b.id - a.id);

    // Ids are dense, so the distance between the baseline and the oldest event
    // we still hold is the number of records that scrolled out of the buffer.
    const oldestHeld = missed.length > 0 ? missed[missed.length - 1].id : ceiling + 1;
    const missingCount = Math.max(0, oldestHeld - baselineId - 1);

    if (missed.length === 0 && missingCount === 0) return null;

    const counts: Partial<Record<StoryEventType, number>> = {};
    for (const event of missed) {
        counts[event.event_type] = (counts[event.event_type] ?? 0) + 1;
    }

    const frames = missed.map((e) => e.frame);
    const times = missed.map((e) => e.simulation_time);
    return {
        events: missed,
        counts,
        missingCount,
        fromFrame: frames.length ? Math.min(...frames) : 0,
        toFrame: frames.length ? Math.max(...frames) : 0,
        fromTime: times.length ? Math.min(...times) : 0,
        toTime: times.length ? Math.max(...times) : 0,
        ceilingId: ceiling,
    };
}

/**
 * The single most notable event in a recap, or null.
 *
 * Highest severity wins; ties break to the most recent. This only chooses what
 * to *show first* - it asserts no relationship between the events.
 */
export function headlineEvent(recap: StoryRecap): StoryEvent | null {
    if (recap.events.length === 0) return null;
    return recap.events.reduce((best, candidate) => {
        const bestRank = SEVERITY_RANK[best.severity] ?? 0;
        const rank = SEVERITY_RANK[candidate.severity] ?? 0;
        if (rank !== bestRank) return rank > bestRank ? candidate : best;
        return candidate.id > best.id ? candidate : best;
    });
}

/**
 * A deterministic one-line summary: "2 population dangers, 1 generation
 * milestone". Counts only - no ordering, no connectives, nothing that would
 * imply one event brought about another.
 */
export function summarizeCounts(recap: StoryRecap): string {
    const parts = (Object.keys(recap.counts) as StoryEventType[])
        // Sorted by type name so the same recap always reads the same way.
        .sort()
        .map((type) => {
            const count = recap.counts[type] ?? 0;
            const label = storyEventMeta(type).label.toLowerCase();
            return `${count} ${label}${count === 1 ? '' : 's'}`;
        });
    return parts.join(', ');
}
