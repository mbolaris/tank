/**
 * CommentaryFeed - the "Board" panel (formerly "Insights").
 *
 * Renders a live feed of agent observations about the running simulation,
 * posted via POST /api/world/{world_id}/commentary (see backend/commentary_store.py
 * and tools/post_commentary.py). Polls the GET endpoint every few seconds and
 * shows the most recent comments newest-first.
 *
 * v2 additions: topic filter chips, per-message topic badges, and Slack-style
 * emoji reaction bar (via CommentaryCard). See docs/DISCUSSION_BOARD.md.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { buildDiscussionPrompt, type BoardPromptRole } from '../boardPrompts';
import { config } from '../config';
import type { CommentaryItem, CommentaryResponse, CommentaryTopic } from '../types/simulation';
import { CommentaryCard } from './CommentaryCard';
import styles from './CommentaryFeed.module.css';

const POLL_INTERVAL_MS = 4000;
const FETCH_LIMIT = 100;
const LS_TOPIC_KEY = 'tank.boardTopicFilter';
const LS_REACTOR_KEY = 'tank.reactorName';
const DEFAULT_REACTOR = 'viewer';

/** Topic filter chips configuration. */
const TOPIC_CHIPS: { value: CommentaryTopic | 'all'; icon: string; label: string }[] = [
    { value: 'all', icon: '', label: 'All' },
    { value: 'ecosystem', icon: '🌱', label: 'Ecosystem' },
    { value: 'substrate', icon: '🧬', label: 'Substrate' },
    { value: 'environment', icon: '🪸', label: 'Environment' },
    { value: 'ui', icon: '🖥️', label: 'UI' },
];

function getStoredTopic(): CommentaryTopic | 'all' {
    try {
        const stored = localStorage.getItem(LS_TOPIC_KEY);
        if (stored && TOPIC_CHIPS.some(c => c.value === stored)) {
            return stored as CommentaryTopic | 'all';
        }
    } catch {
        // localStorage not available
    }
    return 'all';
}

function getViewerName(): string {
    try {
        return localStorage.getItem(LS_REACTOR_KEY) || DEFAULT_REACTOR;
    } catch {
        return DEFAULT_REACTOR;
    }
}

interface CommentaryFeedProps {
    worldId: string | undefined;
}

export function CommentaryFeed({ worldId }: CommentaryFeedProps) {
    const [comments, setComments] = useState<CommentaryItem[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [loaded, setLoaded] = useState(false);
    const [activeTopic, setActiveTopic] = useState<CommentaryTopic | 'all'>(getStoredTopic);
    const [copiedRole, setCopiedRole] = useState<BoardPromptRole | null>(null);
    const mountedRef = useRef(true);
    const viewerName = getViewerName();

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

    // --- Topic filter ---
    const handleTopicChange = useCallback((topic: CommentaryTopic | 'all') => {
        setActiveTopic(topic);
        try {
            localStorage.setItem(LS_TOPIC_KEY, topic);
        } catch {
            // localStorage not available
        }
    }, []);

    // Client-side topic filtering
    const filteredComments = activeTopic === 'all'
        ? comments
        : comments.filter(c => c.topic === activeTopic);

    // Count per topic for the chips
    const topicCounts: Record<string, number> = { all: comments.length };
    for (const c of comments) {
        topicCounts[c.topic] = (topicCounts[c.topic] || 0) + 1;
    }

    // --- Reactions (optimistic) ---
    const handleReact = useCallback(async (commentId: number, emoji: string) => {
        // Optimistic update
        setComments(prev =>
            prev.map(c => {
                if (c.id !== commentId) return c;
                const reactions = { ...c.reactions };
                const reactors = [...(reactions[emoji] ?? [])];
                if (!reactors.includes(viewerName)) {
                    reactors.push(viewerName);
                }
                reactions[emoji] = reactors;
                return { ...c, reactions };
            }),
        );
        // Fire and forget — next poll reconciles
        try {
            await fetch(config.reactionUrl(effectiveId, commentId), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ emoji, reactor: viewerName }),
            });
        } catch {
            // Reconciled on next poll
        }
    }, [effectiveId, viewerName]);

    const handleUnreact = useCallback(async (commentId: number, emoji: string) => {
        // Optimistic update
        setComments(prev =>
            prev.map(c => {
                if (c.id !== commentId) return c;
                const reactions = { ...c.reactions };
                const reactors = (reactions[emoji] ?? []).filter(r => r !== viewerName);
                if (reactors.length > 0) {
                    reactions[emoji] = reactors;
                } else {
                    delete reactions[emoji];
                }
                return { ...c, reactions };
            }),
        );
        // Fire and forget — next poll reconciles
        try {
            const params = new URLSearchParams({ emoji, reactor: viewerName });
            await fetch(`${config.reactionUrl(effectiveId, commentId)}?${params}`, {
                method: 'DELETE',
            });
        } catch {
            // Reconciled on next poll
        }
    }, [effectiveId, viewerName]);

    // --- Discussion prompts (copy to clipboard) ---
    const handleCopyPrompt = useCallback(async (role: BoardPromptRole) => {
        const text = buildDiscussionPrompt(role, activeTopic, config.apiBaseUrl);
        try {
            await navigator.clipboard.writeText(text);
            setCopiedRole(role);
            setTimeout(() => setCopiedRole(prev => (prev === role ? null : prev)), 2000);
        } catch {
            // Clipboard permission denied or unavailable - nothing to reconcile,
            // just skip the "Copied!" confirmation.
        }
    }, [activeTopic]);

    return (
        <div className={styles.container}>
            <p className={styles.subtitle}>
                Live observations posted by agents studying this simulation. Launch one with{' '}
                <code>/observe-sim</code> or <code>python tools/post_commentary.py</code>.
            </p>

            {/* Topic filter chips */}
            <div className={styles.chipBar}>
                {TOPIC_CHIPS.map(chip => {
                    const isActive = activeTopic === chip.value;
                    const count = topicCounts[chip.value] ?? 0;
                    return (
                        <button
                            key={chip.value}
                            className={`${styles.chip} ${isActive ? styles.chipActive : ''}`}
                            onClick={() => handleTopicChange(chip.value)}
                        >
                            {chip.icon && <span className={styles.chipIcon}>{chip.icon}</span>}
                            {chip.label}
                            <span className={styles.chipCount}>{count}</span>
                        </button>
                    );
                })}
            </div>

            {/* Discussion prompts (copy to clipboard) */}
            <div className={styles.promptBar}>
                <button
                    className={styles.promptButton}
                    onClick={() => handleCopyPrompt('leader')}
                    title="Copy a self-contained prompt for starting a discussion under the selected topic"
                >
                    📣 Copy Discussion Leader Prompt
                </button>
                <button
                    className={styles.promptButton}
                    onClick={() => handleCopyPrompt('participant')}
                    title="Copy a self-contained prompt for monitoring and joining a discussion under the selected topic"
                >
                    🗣️ Copy Participate Prompt
                </button>
                {copiedRole && <span className={styles.copiedHint}>Copied!</span>}
            </div>

            {error && comments.length === 0 && (
                <div className={styles.error}>Could not load commentary: {error}</div>
            )}

            {loaded && !error && comments.length === 0 && (
                <div className={styles.empty}>
                    No commentary yet. An agent can post one with{' '}
                    <code>python tools/post_commentary.py --text &quot;...&quot;</code> or by POSTing to{' '}
                    <code>/api/world/{effectiveId}/commentary</code>.
                </div>
            )}

            {filteredComments.length > 0 && (
                <div className={styles.list}>
                    {filteredComments.map((c) => (
                        <CommentaryCard
                            key={c.id}
                            comment={c}
                            viewerName={viewerName}
                            onReact={handleReact}
                            onUnreact={handleUnreact}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}
