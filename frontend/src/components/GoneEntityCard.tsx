import type { KeyboardEvent, RefObject } from 'react';
import { entityTypeLabel } from './entityInspectorFormat';
import styles from './EntityInspectorDrawer.module.css';

interface GoneEntityCardProps {
    entityId: number;
    entityType: string;
    onClose: () => void;
    dialogRef: RefObject<HTMLDivElement | null>;
    onKeyDown: (event: KeyboardEvent) => void;
}

/**
 * Stand-in for the full inspector drawer once the entity has left the world
 * (died or transferred) — a small card instead of a tall, mostly-empty panel.
 */
export function GoneEntityCard({ entityId, entityType, onClose, dialogRef, onKeyDown }: GoneEntityCardProps) {
    return (
        <div
            ref={dialogRef}
            className={styles.goneCard}
            role="dialog"
            aria-label={`${entityTypeLabel(entityType)} inspector`}
            tabIndex={-1}
            onKeyDown={onKeyDown}
        >
            <header className={styles.header}>
                <div className={styles.headerTitle}>
                    <span className={styles.entityType}>{entityTypeLabel(entityType)}</span>
                    <span className={styles.entityId}>{`#${entityId}`}</span>
                </div>
                <button
                    className={styles.closeButton}
                    onClick={onClose}
                    aria-label="Close inspector"
                    title="Close inspector (Esc)"
                >
                    ×
                </button>
            </header>
            <div className={styles.goneCardBody}>
                <div className={styles.goneBanner} role="status">
                    No longer in the world — it may have died or been transferred.
                </div>
            </div>
        </div>
    );
}
