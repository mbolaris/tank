import type { CommentarySeverity, CommentaryTopic } from '../types/simulation';

/** Shared severity/topic display metadata for the Board feed and its ambient toasts. */
export const SEVERITY: Record<CommentarySeverity, { icon: string; color: string }> = {
    info: { icon: '💬', color: '#94a3b8' },
    insight: { icon: '🔬', color: '#3b82f6' },
    warning: { icon: '⚠️', color: '#fbbf24' },
    concern: { icon: '🚨', color: '#ef4444' },
};

export const TOPIC_META: Record<CommentaryTopic, { icon: string; label: string }> = {
    ecosystem: { icon: '🌱', label: 'Ecosystem' },
    substrate: { icon: '🧬', label: 'Substrate' },
    environment: { icon: '🪸', label: 'Environment' },
    ui: { icon: '🖥️', label: 'UI' },
};

export function severityStyle(severity: CommentarySeverity) {
    return SEVERITY[severity] ?? SEVERITY.info;
}
