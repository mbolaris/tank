import { useCallback, useEffect, useRef, useState } from 'react';
import type { StoryEvent } from '../types/story';

/** One key per world: two tanks are two separate visit histories. */
export const LS_PREFIX = 'tank.lastSeenStoryEvent.';

export function storageKey(worldId: string): string {
    return `${LS_PREFIX}${worldId}`;
}

export interface UseLastSeenStoryEventResult {
    /**
     * The id the viewer had seen when they arrived, frozen for this visit.
     *
     * `null` means no baseline was stored - a first visit or cleared storage.
     * It stays frozen so the recap describes the moment of arrival rather than
     * shrinking as events keep arriving.
     */
    baselineId: number | null;
    /** True once the stored value has been read (or found absent). */
    ready: boolean;
    /** Persist a new high-water mark, e.g. when the recap is dismissed. */
    markSeen: (eventId: number) => void;
}

/**
 * Remembers, per world, the highest story-event id this browser has seen (U8a).
 *
 * Deliberately per-viewer and local: a recap is a property of *this* person's
 * visit, not of the world, so it belongs in localStorage rather than in the
 * world snapshot every viewer shares.
 *
 * Storage can be unavailable or throw (private windows, blocked site data), so
 * every access is guarded: a failure degrades to "no baseline", which shows no
 * recap rather than a wrong one.
 */
export function useLastSeenStoryEvent(worldId: string | undefined): UseLastSeenStoryEventResult {
    const [baselineId, setBaselineId] = useState<number | null>(null);
    const [ready, setReady] = useState(false);
    const effectiveId = worldId || 'default';
    // The baseline is read once per world and then held; later writes update
    // storage without moving the baseline this visit is being measured against.
    const frozenRef = useRef<string | null>(null);

    useEffect(() => {
        if (frozenRef.current === effectiveId) return;
        frozenRef.current = effectiveId;
        setBaselineId(readStoredId(effectiveId));
        setReady(true);
    }, [effectiveId]);

    const markSeen = useCallback(
        (eventId: number) => {
            if (!Number.isFinite(eventId) || eventId < 0) return;
            try {
                localStorage.setItem(storageKey(effectiveId), String(Math.floor(eventId)));
            } catch {
                // Storage unavailable; the recap simply reappears next visit.
            }
        },
        [effectiveId],
    );

    return { baselineId, ready, markSeen };
}

/** Read a world's stored id, treating anything unparseable as absent. */
export function readStoredId(worldId: string): number | null {
    try {
        const raw = localStorage.getItem(storageKey(worldId));
        if (raw === null) return null;
        const parsed = Number.parseInt(raw, 10);
        return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
    } catch {
        return null;
    }
}

/**
 * Freeze the highest event id present when the viewer arrived (U8a).
 *
 * The recap answers "what happened while I was away", so its upper bound has
 * to be pinned at arrival. Without this, an event arriving while the viewer is
 * watching would silently join the summary of the time they were absent.
 *
 * Returns null until the first non-empty batch of events is seen.
 */
export function useFrozenCeiling(events: StoryEvent[], ready: boolean): number | null {
    const [ceiling, setCeiling] = useState<number | null>(null);
    const frozenRef = useRef(false);

    useEffect(() => {
        if (frozenRef.current || !ready || events.length === 0) return;
        frozenRef.current = true;
        setCeiling(Math.max(...events.map((e) => e.id)));
    }, [events, ready]);

    return ceiling;
}
