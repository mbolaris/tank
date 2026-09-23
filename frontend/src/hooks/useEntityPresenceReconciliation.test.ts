import { describe, expect, it } from 'vitest';

import type { EntityData } from '../types/simulation';
import { selectionNeedsReconciliation } from './useEntityPresenceReconciliation';
import { entitySelectionReducer, initialEntitySelectionState } from './useEntitySelection';

const entities = [{ id: 1 }, { id: 2 }] as EntityData[];

describe('selectionNeedsReconciliation', () => {
    it('skips the dispatch when nothing is selected, the selection is present, or already missing', () => {
        expect(selectionNeedsReconciliation(entities, null, false)).toBe(false);
        expect(selectionNeedsReconciliation(entities, 2, false)).toBe(false);
        expect(selectionNeedsReconciliation(entities, 9, true)).toBe(false);
    });

    it('dispatches when the selected entity has left the snapshot', () => {
        expect(selectionNeedsReconciliation(entities, 9, false)).toBe(true);
    });

    it('skips exactly the cases the reducer would have ignored', () => {
        const cases: Array<[number | null, boolean]> = [
            [null, false], [1, false], [9, false], [9, true], [1, true],
        ];
        for (const [selectedEntityId, selectedEntityMissing] of cases) {
            const state = { ...initialEntitySelectionState, selectedEntityId, selectedEntityMissing };
            const next = entitySelectionReducer(state, {
                type: 'reconcile_entities',
                entityIds: entities.map((e) => e.id),
            });
            expect(selectionNeedsReconciliation(entities, selectedEntityId, selectedEntityMissing))
                .toBe(next !== state);
        }
    });
});
