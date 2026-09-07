/**
 * Pure arrangement logic for the story-event surfaces (U7/E4).
 *
 * Kept out of the component files so the rules that actually carry U7's
 * acceptance criteria - how events cluster on the timeline, how world events
 * interleave with agent commentary - can be tested directly instead of through
 * rendered markup.
 */

import type { CommentaryItem } from '../types/simulation';
import type { StoryEvent } from '../types/story';

// ---------------------------------------------------------------------------
// Timeline clustering
// ---------------------------------------------------------------------------

/** Markers nearer than this share of the track merge into one cluster. */
export const MIN_SEPARATION_PCT = 2.5;

export interface TimelineCluster {
    /** Position along the track, 0-100. */
    pct: number;
    /** Newest first, matching the feed's ordering. */
    events: StoryEvent[];
}

/**
 * Group events into clusters by their position on the track, so a burst of
 * events within a few hundred frames renders as one counted marker rather than
 * an unreadable smear of overlapping dots.
 */
export function clusterEvents(events: StoryEvent[], maxFrame: number): TimelineCluster[] {
    if (events.length === 0) return [];
    const span = Math.max(1, maxFrame);
    // Oldest first so clusters read left-to-right along the track.
    const ordered = [...events].sort((a, b) => a.frame - b.frame || a.id - b.id);

    const clusters: TimelineCluster[] = [];
    for (const event of ordered) {
        const pct = Math.min(100, Math.max(0, (event.frame / span) * 100));
        const last = clusters[clusters.length - 1];
        if (last && pct - last.pct < MIN_SEPARATION_PCT) {
            last.events.push(event);
        } else {
            clusters.push({ pct, events: [event] });
        }
    }
    // Within a cluster, newest first so the detail card leads with the latest.
    for (const cluster of clusters) {
        cluster.events.sort((a, b) => b.id - a.id);
    }
    return clusters;
}

// ---------------------------------------------------------------------------
// Merged Board stream
// ---------------------------------------------------------------------------

/** One row of the merged stream, tagged by which surface produced it. */
export type FeedRow =
    | { kind: 'event'; frame: number; key: string; event: StoryEvent }
    | { kind: 'comment'; frame: number; key: string; comment: CommentaryItem };

/**
 * Merge world events and commentary into one newest-first stream.
 *
 * Ordered by simulation frame, the only axis the two kinds share - their ids
 * come from separate spaces and are not comparable. On a tie the world event
 * sorts first: the fact precedes the commentary about it.
 */
export function mergeFeedRows(events: StoryEvent[], comments: CommentaryItem[]): FeedRow[] {
    const rows: FeedRow[] = [
        ...events.map((event): FeedRow => ({
            kind: 'event', frame: event.frame, key: `event-${event.id}`, event,
        })),
        ...comments.map((comment): FeedRow => ({
            kind: 'comment', frame: comment.frame, key: `comment-${comment.id}`, comment,
        })),
    ];
    return rows.sort((a, b) => {
        if (b.frame !== a.frame) return b.frame - a.frame;
        if (a.kind !== b.kind) return a.kind === 'event' ? -1 : 1;
        return b.key.localeCompare(a.key);
    });
}
