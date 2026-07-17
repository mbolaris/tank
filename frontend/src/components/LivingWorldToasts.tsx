/**
 * LivingWorldToasts — ambient, dismissible notices for new Board posts.
 *
 * The Board (CommentaryFeed) already carries agent-posted observations about
 * the running simulation, but it's only visible behind the Analysis tab bar
 * and invisible in Watch Mode. This floats *new* posts over the canvas as
 * small toasts as they arrive, using the same polled data (see
 * hooks/useCommentary.ts), so evolutionary moments are noticed without
 * opening a panel.
 */

import { useEffect, useRef, useState } from 'react';
import { useCommentary } from '../hooks/useCommentary';
import type { CommentaryItem } from '../types/simulation';
import { severityStyle } from '../utils/commentaryDisplay';
import styles from './LivingWorldToasts.module.css';

const TOAST_LIFETIME_MS = 9000;
const MAX_VISIBLE_TOASTS = 3;

interface LivingWorldToastsProps {
    worldId: string | undefined;
    /** Invoked when a toast is clicked, to surface the full Board panel. */
    onOpenBoard: () => void;
}

export function LivingWorldToasts({ worldId, onOpenBoard }: LivingWorldToastsProps) {
    const { comments, loaded } = useCommentary(worldId);
    const [toasts, setToasts] = useState<CommentaryItem[]>([]);
    const [lastSeenId, setLastSeenId] = useState<number | null>(null);

    useEffect(() => {
        // Wait for the first successful fetch to resolve the true state —
        // an empty `comments` before that just means "haven't asked yet",
        // not "this world has no history".
        if (!loaded) return;

        if (lastSeenId === null) {
            // First successful fetch, even if it came back empty: establish
            // the baseline silently so pre-existing history never toasts,
            // but a brand-new post right after mount still does.
            setLastSeenId(comments[0]?.id ?? 0);
            return;
        }

        const fresh = comments.filter((c) => c.id > lastSeenId);
        if (fresh.length === 0) return;
        setLastSeenId(comments[0]?.id ?? lastSeenId);
        setToasts((prev) => [...fresh, ...prev].slice(0, MAX_VISIBLE_TOASTS));
    }, [comments, loaded, lastSeenId]);

    const dismiss = (id: number) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    };

    if (toasts.length === 0) return null;

    return (
        <div className={styles.stack} aria-live="polite">
            {toasts.map((comment) => (
                <Toast
                    key={comment.id}
                    comment={comment}
                    onDismiss={() => dismiss(comment.id)}
                    onOpenBoard={onOpenBoard}
                />
            ))}
        </div>
    );
}

interface ToastProps {
    comment: CommentaryItem;
    onDismiss: () => void;
    onOpenBoard: () => void;
}

function Toast({ comment, onDismiss, onOpenBoard }: ToastProps) {
    // Re-arm the auto-dismiss timer only when the comment itself changes, not
    // on every parent re-render (which would otherwise recreate onDismiss and
    // keep resetting the clock).
    const onDismissRef = useRef(onDismiss);
    useEffect(() => {
        onDismissRef.current = onDismiss;
    }, [onDismiss]);

    useEffect(() => {
        const timer = window.setTimeout(() => onDismissRef.current(), TOAST_LIFETIME_MS);
        return () => window.clearTimeout(timer);
    }, [comment.id]);

    const sev = severityStyle(comment.severity);

    return (
        <div className={styles.toast} style={{ borderLeftColor: sev.color }} role="status">
            <button className={styles.body} onClick={onOpenBoard} title="Open the Board">
                <span className={styles.icon}>{sev.icon}</span>
                <span className={styles.text}>{comment.text}</span>
            </button>
            <button className={styles.close} onClick={onDismiss} aria-label="Dismiss">
                ×
            </button>
        </div>
    );
}
