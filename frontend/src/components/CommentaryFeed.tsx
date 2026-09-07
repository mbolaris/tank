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
 *
 * U7/E4 additions: deterministic world events from the E3 story-event service
 * are merged into the same stream, rendered as visibly distinct WORLD EVENT
 * cards (StoryEventCard). The two kinds share one surface but never one voice -
 * a story event is something the tank *did*, a comment is what an agent
 * *thinks* about it. The merged stream is ordered by simulation frame, the one
 * axis both kinds actually share; their ids come from separate spaces and are
 * not comparable.
 */

import { useCallback, useState } from 'react';
import { buildDiscussionPrompt, type BoardPromptRole, type BoardPromptScope } from '../boardPrompts';
import { config } from '../config';
import { useCommentary } from '../hooks/useCommentary';
import { useStoryEvents } from '../hooks/useStoryEvents';
import type { CommentaryTopic } from '../types/simulation';
import { CommentaryCard } from './CommentaryCard';
import { StoryEventCard } from './StoryEventCard';
import { mergeFeedRows } from '../utils/storyFeed';
import styles from './CommentaryFeed.module.css';

const LS_TOPIC_KEY = 'tank.boardTopicFilter';
const LS_REACTOR_KEY = 'tank.reactorName';
const DEFAULT_REACTOR = 'viewer';

/**
 * Board filter values: the four commentary topics, plus `all` and a `world`
 * pseudo-topic for the deterministic story events. Story events carry no topic
 * of their own - they are measurements, not conversations - so they are shown
 * under `all` and `world` and hidden when a specific conversation is selected.
 */
export type BoardFilter = CommentaryTopic | 'all' | 'world';

/** Topic filter chips configuration. */
const TOPIC_CHIPS: { value: BoardFilter; icon: string; label: string }[] = [
    { value: 'all', icon: '', label: 'All' },
    { value: 'world', icon: '🌍', label: 'World events' },
    { value: 'ecosystem', icon: '🌱', label: 'Ecosystem' },
    { value: 'substrate', icon: '🧬', label: 'Substrate' },
    { value: 'environment', icon: '🪸', label: 'Environment' },
    { value: 'ui', icon: '🖥️', label: 'UI' },
];

function getStoredTopic(): BoardFilter {
    try {
        const stored = localStorage.getItem(LS_TOPIC_KEY);
        if (stored && TOPIC_CHIPS.some(c => c.value === stored)) {
            return stored as BoardFilter;
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
    /** Ids present in the latest reconciled world state (for U4 links). */
    liveEntityIds?: ReadonlySet<number>;
    /** Opens the U4 inspector from a world event. */
    onInspectEntity?: (entityId: number) => void;
}

export function CommentaryFeed({ worldId, liveEntityIds, onInspectEntity }: CommentaryFeedProps) {
    const { comments, setComments, error, loaded } = useCommentary(worldId);
    const { events: storyEvents } = useStoryEvents(worldId);
    const [activeTopic, setActiveTopic] = useState<BoardFilter>(getStoredTopic);
    const [copiedRole, setCopiedRole] = useState<BoardPromptRole | null>(null);
    const viewerName = getViewerName();

    const effectiveId = worldId || 'default';

    // --- Topic filter ---
    const handleTopicChange = useCallback((topic: BoardFilter) => {
        setActiveTopic(topic);
        try {
            localStorage.setItem(LS_TOPIC_KEY, topic);
        } catch {
            // localStorage not available
        }
    }, []);

    // Client-side filtering. `world` shows only measurements; a named topic
    // shows only that conversation; `all` shows the merged stream.
    const visibleComments = activeTopic === 'all'
        ? comments
        : activeTopic === 'world'
            ? []
            : comments.filter(c => c.topic === activeTopic);
    const visibleEvents = activeTopic === 'all' || activeTopic === 'world' ? storyEvents : [];
    const rows = mergeFeedRows(visibleEvents, visibleComments);

    // Counts for the chips
    const topicCounts: Record<string, number> = {
        all: comments.length + storyEvents.length,
        world: storyEvents.length,
    };
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
    }, [effectiveId, viewerName, setComments]);

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
    }, [effectiveId, viewerName, setComments]);

    // --- Discussion prompts (copy to clipboard) ---
    const handleCopyPrompt = useCallback(async (role: BoardPromptRole) => {
        // The prompts brief an agent to join a *conversation*. World events are
        // measurements with no conversation to scope to, so that filter falls
        // back to the un-narrowed prompt rather than inventing a topic.
        const scope: BoardPromptScope = activeTopic === 'world' ? 'all' : activeTopic;
        const text = buildDiscussionPrompt(role, scope, config.apiBaseUrl);
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

            {loaded && !error && comments.length === 0 && storyEvents.length === 0 && (
                <div className={styles.empty}>
                    No commentary yet. An agent can post one with{' '}
                    <code>python tools/post_commentary.py --text &quot;...&quot;</code> or by POSTing to{' '}
                    <code>/api/world/{effectiveId}/commentary</code>.
                </div>
            )}

            {rows.length > 0 && (
                <div className={styles.list}>
                    {rows.map((row) => (
                        row.kind === 'event' ? (
                            <StoryEventCard
                                key={row.key}
                                event={row.event}
                                liveEntityIds={liveEntityIds}
                                onInspectEntity={onInspectEntity}
                            />
                        ) : (
                            <CommentaryCard
                                key={row.key}
                                comment={row.comment}
                                viewerName={viewerName}
                                onReact={handleReact}
                                onUnreact={handleUnreact}
                            />
                        )
                    ))}
                </div>
            )}
        </div>
    );
}
