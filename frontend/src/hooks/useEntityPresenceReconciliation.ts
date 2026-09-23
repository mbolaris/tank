import { useEffect } from 'react';

import type { EntityData } from '../types/simulation';

/**
 * Whether a payload's entities require reconciling the selection: only when a
 * selected entity, not already marked missing, is absent from the snapshot.
 * Mirrors the no-op cases of the `reconcile_entities` reducer branch.
 */
export function selectionNeedsReconciliation(
    entities: EntityData[],
    selectedEntityId: number | null,
    selectedEntityMissing: boolean
): boolean {
    if (selectedEntityId === null || selectedEntityMissing) return false;
    return !entities.some((entity) => entity.id === selectedEntityId);
}

/**
 * Clear only the visual/follow state when a selected entity leaves the merged
 * WebSocket snapshot. The inspector stays open to explain that disappearance.
 *
 * Dispatches only when there is something to reconcile. The reducer already
 * ignores the other cases, but a reducer dispatch still re-renders the calling
 * component before React can bail out - and this runs after every payload, so
 * an unconditional dispatch rendered all of TankView twice per WebSocket
 * message.
 */
export function useEntityPresenceReconciliation(
    entities: EntityData[],
    selectedEntityId: number | null,
    selectedEntityMissing: boolean,
    reconcileEntities: (entityIds: number[]) => void
) {
    useEffect(() => {
        if (!selectionNeedsReconciliation(entities, selectedEntityId, selectedEntityMissing)) return;
        reconcileEntities(entities.map((entity) => entity.id));
    }, [entities, selectedEntityId, selectedEntityMissing, reconcileEntities]);
}
