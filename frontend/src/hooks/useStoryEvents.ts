import { useCallback, useEffect, useRef, useState } from 'react';
import { config } from '../config';
import type { StoryEvent, StoryEventResponse } from '../types/story';

const POLL_INTERVAL_MS = 4000;
/** One backfill page. The backend buffer is bounded at 500. */
const BACKFILL_LIMIT = 200;
/** Client-side cap so a long session cannot grow the list without bound. */
const MAX_RETAINED = 300;

export interface UseStoryEventsResult {
    /** Newest first. Stable order, no duplicates, safe across reconnects. */
    events: StoryEvent[];
    error: string | null;
    loaded: boolean;
}

/**
 * Polls GET /api/world/{world_id}/story-events - the deterministic world facts
 * produced by the E3 detectors (see backend/story_events.py).
 *
 * Polling is **incremental**: after the first page we ask only for events newer
 * than the highest id we hold, and merge them into the existing list. That is
 * what makes the feed reconnect-safe, and it is only sound because story-event
 * ids are monotonic and never reused - even after old events scroll out of the
 * server's bounded buffer.
 *
 * Two failure modes are handled explicitly rather than by hoping:
 *
 * - **Duplicates.** A retried or overlapping request can return an event we
 *   already hold, so the merge is keyed by id instead of appending blindly.
 * - **A world switch or a server restart.** Ids then restart from 1, which
 *   would look like "nothing newer than what I have" forever. Changing worlds
 *   resets the cursor, and an event id *below* our cursor is treated as a new
 *   stream rather than merged into the old one.
 */
export function useStoryEvents(worldId: string | undefined): UseStoryEventsResult {
    const [events, setEvents] = useState<StoryEvent[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [loaded, setLoaded] = useState(false);

    const mountedRef = useRef(true);
    /** Highest id merged so far; 0 means "no cursor, fetch a backfill page". */
    const cursorRef = useRef(0);

    const effectiveId = worldId || 'default';

    const fetchEvents = useCallback(async () => {
        const cursor = cursorRef.current;
        const query = cursor > 0 ? `since_id=${cursor}` : `limit=${BACKFILL_LIMIT}`;
        try {
            const response = await fetch(`${config.storyEventsUrl(effectiveId)}?${query}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const data: StoryEventResponse = await response.json();
            if (!mountedRef.current) return;

            const incoming = data.events ?? [];
            setEvents((prev) => merge(prev, incoming, cursor));
            if (incoming.length > 0) {
                const highest = Math.max(...incoming.map((e) => e.id));
                // After a restart, adopt the new stream's high-water mark rather
                // than pinning to a cursor no future event will ever exceed.
                cursorRef.current = restarted(incoming, cursor) ? highest : Math.max(cursor, highest);
            }
            setError(null);
            setLoaded(true);
        } catch (e) {
            if (!mountedRef.current) return;
            setError(e instanceof Error ? e.message : 'Failed to load story events');
            setLoaded(true);
        }
    }, [effectiveId]);

    useEffect(() => {
        mountedRef.current = true;
        // A different world is a different id space - never carry the cursor
        // or the previous world's events across.
        cursorRef.current = 0;
        setEvents([]);
        setLoaded(false);
        fetchEvents();
        const interval = setInterval(fetchEvents, POLL_INTERVAL_MS);
        return () => {
            mountedRef.current = false;
            clearInterval(interval);
        };
    }, [fetchEvents]);

    return { events, error, loaded };
}

/**
 * True when the whole page sits *behind* our cursor - the signature of a
 * renumbered stream.
 *
 * It must be the page maximum, not "any id at or below the cursor": a server
 * can legitimately include the cursor event itself in an overlapping page, and
 * treating that benign overlap as a restart would throw away every event we
 * already hold.
 */
function restarted(incoming: StoryEvent[], cursor: number): boolean {
    if (cursor <= 0 || incoming.length === 0) return false;
    return Math.max(...incoming.map((e) => e.id)) < cursor;
}

/**
 * Merge a fetched page into the retained list, newest first.
 *
 * Exported for tests: the dedup/ordering contract is the part of U7 that has to
 * survive reconnects, so it is verified directly rather than through the DOM.
 */
export function merge(prev: StoryEvent[], incoming: StoryEvent[], cursor = 0): StoryEvent[] {
    if (incoming.length === 0) return prev;
    // A restarted id space replaces the list outright; merging would interleave
    // two unrelated numbering schemes.
    const base = restarted(incoming, cursor) ? [] : prev;

    const byId = new Map<number, StoryEvent>();
    for (const event of base) byId.set(event.id, event);
    // Incoming wins on a collision: the server's copy is the newer truth.
    for (const event of incoming) byId.set(event.id, event);

    return [...byId.values()].sort((a, b) => b.id - a.id).slice(0, MAX_RETAINED);
}
