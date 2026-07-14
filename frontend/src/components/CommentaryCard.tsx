/**
 * CommentaryCard - a single message in the Board feed.
 *
 * Renders the header (severity icon, topic badge, author, frame/time), body
 * text, tags, metrics, and the Slack-style emoji reaction bar. Extracted from
 * CommentaryFeed so the feed component stays a thin fetch-and-filter shell.
 */

import { useCallback, useState } from 'react';
import type { CommentaryItem, CommentarySeverity, CommentaryTopic } from '../types/simulation';
import styles from './CommentaryCard.module.css';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const SEVERITY: Record<CommentarySeverity, { icon: string; color: string }> = {
    info: { icon: '💬', color: '#94a3b8' },
    insight: { icon: '🔬', color: '#3b82f6' },
    warning: { icon: '⚠️', color: '#fbbf24' },
    concern: { icon: '🚨', color: '#ef4444' },
};

const TOPIC_META: Record<CommentaryTopic, { icon: string; label: string }> = {
    ecosystem: { icon: '🌱', label: 'Ecosystem' },
    substrate: { icon: '🧬', label: 'Substrate' },
    environment: { icon: '🪸', label: 'Environment' },
    ui: { icon: '🖥️', label: 'UI' },
};

/** The curated palette - must match backend REACTION_EMOJI. */
const REACTION_PALETTE = ['👍', '👎', '❤️', '😂', '🎉', '💡', '👀', '⚠️'];

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

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface CommentaryCardProps {
    comment: CommentaryItem;
    viewerName: string;
    onReact: (commentId: number, emoji: string) => void;
    onUnreact: (commentId: number, emoji: string) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CommentaryCard({ comment, viewerName, onReact, onUnreact }: CommentaryCardProps) {
    const [paletteOpen, setPaletteOpen] = useState(false);

    const sev = severityStyle(comment.severity);
    const topicMeta = TOPIC_META[comment.topic] ?? TOPIC_META.ecosystem;

    const handlePillClick = useCallback(
        (emoji: string) => {
            const reactors = comment.reactions?.[emoji] ?? [];
            if (reactors.includes(viewerName)) {
                onUnreact(comment.id, emoji);
            } else {
                onReact(comment.id, emoji);
            }
        },
        [comment.id, comment.reactions, viewerName, onReact, onUnreact],
    );

    const handlePaletteSelect = useCallback(
        (emoji: string) => {
            onReact(comment.id, emoji);
            setPaletteOpen(false);
        },
        [comment.id, onReact],
    );

    // Collect existing reactions as sorted entries
    const reactionEntries = Object.entries(comment.reactions ?? {}).filter(
        ([, reactors]) => reactors.length > 0,
    );

    return (
        <div
            className={styles.card}
            style={{ borderLeftColor: sev.color }}
        >
            {/* Header */}
            <div className={styles.header}>
                <span className={styles.severityIcon} title={comment.severity}>
                    {sev.icon}
                </span>
                <span className={styles.topicBadge} title={`Topic: ${topicMeta.label}`}>
                    {topicMeta.icon} {topicMeta.label}
                </span>
                <span className={styles.author}>{comment.author}</span>
                <span className={styles.meta}>
                    frame {comment.frame.toLocaleString()} · {timeAgo(comment.created_at)}
                </span>
            </div>

            {/* Body */}
            <p className={styles.text}>{comment.text}</p>

            {/* Tags */}
            {comment.tags.length > 0 && (
                <div className={styles.tags}>
                    {comment.tags.map((tag) => (
                        <span key={tag} className={styles.tag}>
                            {tag}
                        </span>
                    ))}
                </div>
            )}

            {/* Metrics */}
            {comment.metrics && Object.keys(comment.metrics).length > 0 && (
                <div className={styles.metrics}>
                    {Object.entries(comment.metrics).map(([k, v]) => (
                        <span key={k} className={styles.metric}>
                            {k}=
                            <span className={styles.metricValue}>
                                {String(v)}
                            </span>
                        </span>
                    ))}
                </div>
            )}

            {/* Reactions bar */}
            <div className={styles.reactionsBar}>
                {reactionEntries.map(([emoji, reactors]) => {
                    const isViewer = reactors.includes(viewerName);
                    return (
                        <button
                            key={emoji}
                            className={`${styles.reactionPill} ${isViewer ? styles.reactionPillActive : ''}`}
                            onClick={() => handlePillClick(emoji)}
                            title={reactors.join(', ')}
                        >
                            {emoji} {reactors.length}
                        </button>
                    );
                })}

                {/* Add reaction button */}
                <div className={styles.addReactionWrapper}>
                    <button
                        className={styles.addReactionBtn}
                        onClick={() => setPaletteOpen(!paletteOpen)}
                        title="Add reaction"
                    >
                        +
                    </button>
                    {paletteOpen && (
                        <div className={styles.palette}>
                            {REACTION_PALETTE.map((emoji) => (
                                <button
                                    key={emoji}
                                    className={styles.paletteEmoji}
                                    onClick={() => handlePaletteSelect(emoji)}
                                >
                                    {emoji}
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
