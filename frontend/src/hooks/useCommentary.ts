import { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityRequests } from './activityRequests';
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
    const [comments, setCommentsInternal] = useState<CommentaryItem[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [loaded, setLoaded] = useState(false);
    const [owner, setOwner] = useState(worldId || 'default');
    const ownerRef = useRef<string | null>(owner);

    const effectiveId = worldId || 'default';

    const setComments = useCallback<UseCommentaryResult['setComments']>((update) => {
        setCommentsInternal(prev => ownerRef.current === effectiveId ? (typeof update === 'function' ? update(prev) : update) : prev);
    }, [effectiveId]);

    useEffect(() => {
        const requests = new ActivityRequests();
        ownerRef.current = effectiveId;
        setOwner(effectiveId);
        setCommentsInternal([]);
        setError(null);
        setLoaded(false);
        const fetchComments = () => requests.run(async signal => {
            const url = `${config.commentaryUrl(effectiveId)}?limit=${FETCH_LIMIT}`;
            const response = await fetch(url, { signal });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const data: CommentaryResponse = await response.json();
            return data;
        }, data => {
            const sorted = [...(data.comments ?? [])].sort((a, b) => b.id - a.id);
            setCommentsInternal(sorted);
            setError(null);
            setLoaded(true);
        }, e => {
            setError(e instanceof Error ? e.message : 'Failed to load commentary');
            setLoaded(true);
        });
        fetchComments();
        const interval = setInterval(fetchComments, POLL_INTERVAL_MS);
        return () => {
            requests.close();
            ownerRef.current = null;
            clearInterval(interval);
        };
    }, [effectiveId]);

    return { comments: owner === effectiveId ? comments : [], setComments, error: owner === effectiveId ? error : null, loaded: owner === effectiveId && loaded };
}
