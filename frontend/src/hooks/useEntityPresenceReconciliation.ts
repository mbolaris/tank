import { useEffect } from 'react';

import type { EntityData } from '../types/simulation';

/**
 * Clear only the visual/follow state when a selected entity leaves the merged
 * WebSocket snapshot. The inspector stays open to explain that disappearance.
 */
export function useEntityPresenceReconciliation(
    entities: EntityData[],
    reconcileEntities: (entityIds: number[]) => void
) {
    useEffect(() => {
        reconcileEntities(entities.map((entity) => entity.id));
    }, [entities, reconcileEntities]);
}
