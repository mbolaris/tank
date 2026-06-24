/**
 * CommentaryFeed - the "Insights" tab.
 *
 * Renders a live feed of agent observations about the running simulation,
 * posted via POST /api/world/{world_id}/commentary (see backend/commentary_store.py
 * and tools/post_commentary.py). Polls the GET endpoint every few seconds and
 * shows the most recent comments newest-first.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { config } from '../config';
import type { CommentaryItem, CommentarySeverity, CommentaryResponse } from '../types/simulation';
import styles from './CommentaryFeed.module.css';

const POLL_INTERVAL_MS = 4000;
const FETCH_LIMIT = 100;

const SEVERITY: Record<CommentarySeverity, { icon: string; color: string }> = {
    info: { icon: '💬', color: '#94a3b8' },
    insight: { icon: '🔬', color: '#3b82f6' },
    warning: { icon: '⚠️', color: '#fbbf24' },
    concern: { icon: '🚨', color: '#ef4444' },
};

function severityStyle(severity: CommentarySeverity) {
    return SEVERITY[severity] ?? SEVERITY.info;
}

function timeAgo(epochSeconds: number): string {
    const secs = Math.max(0, Math.floor(Date.now() / 1000 - epochSeconds));
    if (secs < 60) return `${secs}s ago`;
    const mins = Math.floor(secs / 60);
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
}

interface CommentaryFeedProps {
    worldId: string | undefined;
}

export function CommentaryFeed({ worldId }: CommentaryFeedProps) {
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
            // Newest first for a commentary feed.
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

    return (
        <div className={styles.container}>
            <p className={styles.subtitle}>
                Live observations posted by agents studying this simulation. Launch one with{' '}
                <code>/observe-sim</code> or <code>python tools/post_commentary.py</code>.
            </p>

            {error && comments.length === 0 && (
                <div className={styles.error}>Could not load commentary: {error}</div>
            )}

            {loaded && !error && comments.length === 0 && (
                <div className={styles.empty}>
                    No commentary yet. An agent can post one with{' '}
                    <code>python tools/post_commentary.py --text "..."</code> or by POSTing to{' '}
                    <code>/api/world/{effectiveId}/commentary</code>.
                </div>
            )}

            {comments.length > 0 && (
                <div className={styles.list}>
                    {comments.map((c) => {
                        const sev = severityStyle(c.severity);
                        return (
                            <div
                                key={c.id}
                                className={styles.item}
                                style={{ borderLeftColor: sev.color }}
                            >
                                <div className={styles.itemHeader}>
                                    <span className={styles.severityIcon} title={c.severity}>
                                        {sev.icon}
                                    </span>
                                    <span className={styles.author}>{c.author}</span>
                                    <span className={styles.meta}>
                                        frame {c.frame.toLocaleString()} · {timeAgo(c.created_at)}
                                    </span>
                                </div>
                                <p className={styles.text}>{c.text}</p>
                                {c.tags.length > 0 && (
                                    <div className={styles.tags}>
                                        {c.tags.map((tag) => (
                                            <span key={tag} className={styles.tag}>
                                                {tag}
                                            </span>
                                        ))}
                                    </div>
                                )}
                                {c.metrics && Object.keys(c.metrics).length > 0 && (
                                    <div className={styles.metrics}>
                                        {Object.entries(c.metrics).map(([k, v]) => (
                                            <span key={k} className={styles.metric}>
                                                {k}=
                                                <span className={styles.metricValue}>
                                                    {String(v)}
                                                </span>
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
