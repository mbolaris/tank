import { useCallback, useEffect, useRef, useState } from 'react';
import { config } from '../config';
import type { CommentaryItem, CommentaryResponse } from '../types/simulation';

const POLL_INTERVAL_MS = 4000;
const FETCH_LIMIT = 100;

export interface UseCommentaryResult {
    comments: CommentaryItem[];
    setComments: React.Dispatch<React.SetStateAction<CommentaryItem[]>>;
    error: string | null;
    loaded: boolean;
}

/**
 * Polls GET /api/world/{world_id}/commentary, newest-first. Shared by the
 * Board feed (CommentaryFeed) and the ambient toast layer (LivingWorldToasts)
 * so both read the same data without doubling the request rate.
 */
export function useCommentary(worldId: string | undefined): UseCommentaryResult {
    const [comments, setComments] = useState<CommentaryItem[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [loaded, setLoaded] = useState(false);
    const mountedRef = useRef(true);

    const effectiveId = worldId || 'default';

    const fetchComments = useCallback(async () => {
        try {
            const url = `${config.commentaryUrl(effectiveId)}?limit=${FETCH_LIMIT}`;
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const data: CommentaryResponse = await response.json();
            if (!mountedRef.current) return;
            const sorted = [...(data.comments ?? [])].sort((a, b) => b.id - a.id);
            setComments(sorted);
            setError(null);
            setLoaded(true);
        } catch (e) {
            if (!mountedRef.current) return;
            setError(e instanceof Error ? e.message : 'Failed to load commentary');
            setLoaded(true);
        }
    }, [effectiveId]);

    useEffect(() => {
        mountedRef.current = true;
        fetchComments();
        const interval = setInterval(fetchComments, POLL_INTERVAL_MS);
        return () => {
            mountedRef.current = false;
            clearInterval(interval);
        };
    }, [fetchComments]);

    return { comments, setComments, error, loaded };
}
