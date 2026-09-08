import { useCallback, useEffect, useRef, useState } from 'react';
import { config } from '../config';
import type { Legend, LegendResponse } from '../types/legend';

/** Legends are promoted rarely; there is nothing to gain from polling hard. */
const POLL_INTERVAL_MS = 15000;
const FETCH_LIMIT = 50;

export interface UseLegendsResult {
    /** Newest first. */
    legends: Legend[];
    error: string | null;
    loaded: boolean;
}

/**
 * Polls GET /api/world/{world_id}/legends.
 *
 * Simpler than the story-event hook on purpose: legends are few and bounded,
 * so each poll just replaces the list rather than merging a delta. There is no
 * cursor to get wrong, and a dropped response costs nothing but freshness.
 */
export function useLegends(worldId: string | undefined): UseLegendsResult {
    const [legends, setLegends] = useState<Legend[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [loaded, setLoaded] = useState(false);
    const mountedRef = useRef(true);

    const effectiveId = worldId || 'default';

    const fetchLegends = useCallback(async () => {
        try {
            const response = await fetch(`${config.legendsUrl(effectiveId)}?limit=${FETCH_LIMIT}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data: LegendResponse = await response.json();
            if (!mountedRef.current) return;
            setLegends([...(data.legends ?? [])].sort((a, b) => b.id - a.id));
            setError(null);
            setLoaded(true);
        } catch (e) {
            if (!mountedRef.current) return;
            setError(e instanceof Error ? e.message : 'Failed to load legends');
            setLoaded(true);
        }
    }, [effectiveId]);

    useEffect(() => {
        mountedRef.current = true;
        setLegends([]);
        setLoaded(false);
        fetchLegends();
        const interval = setInterval(fetchLegends, POLL_INTERVAL_MS);
        return () => {
            mountedRef.current = false;
            clearInterval(interval);
        };
    }, [fetchLegends]);

    return { legends, error, loaded };
}
