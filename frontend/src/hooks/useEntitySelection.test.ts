/**
 * Interaction-contract tests for the entity selection reducer (U4/E1).
 *
 * The load-bearing rule: a canvas click opens the INSPECTOR, and transfer is
 * only reachable as an explicit secondary action from an active selection.
 */

import { describe, expect, it } from 'vitest';

import {
    entitySelectionReducer,
    initialEntitySelectionState,
    type EntitySelectionState,
} from './useEntitySelection';

function select(state: EntitySelectionState, entityId = 42, entityType = 'fish') {
    return entitySelectionReducer(state, { type: 'select', entityId, entityType });
}

describe('entitySelectionReducer', () => {
    it('clicking an entity opens the inspector, never the transfer dialog', () => {
        const state = select(initialEntitySelectionState);
        expect(state.selectedEntityId).toBe(42);
        expect(state.selectedEntityType).toBe('fish');
        expect(state.inspectorOpen).toBe(true);
        expect(state.transferOpen).toBe(false);
    });

    it('selecting another entity while transfer is open returns to the inspector', () => {
        let state = select(initialEntitySelectionState);
        state = entitySelectionReducer(state, { type: 'open_transfer' });
        expect(state.transferOpen).toBe(true);

        state = select(state, 77, 'plant');
        expect(state.selectedEntityId).toBe(77);
        expect(state.inspectorOpen).toBe(true);
        expect(state.transferOpen).toBe(false);
    });

    it('transfer cannot open without a selection', () => {
        const state = entitySelectionReducer(initialEntitySelectionState, {
            type: 'open_transfer',
        });
        expect(state.transferOpen).toBe(false);
        expect(state).toBe(initialEntitySelectionState);
    });

    it('cancelling transfer preserves the selection and the inspector', () => {
        let state = select(initialEntitySelectionState);
        state = entitySelectionReducer(state, { type: 'open_transfer' });
        state = entitySelectionReducer(state, { type: 'close_transfer' });

        expect(state.transferOpen).toBe(false);
        expect(state.inspectorOpen).toBe(true);
        expect(state.selectedEntityId).toBe(42);
    });

    it('closing the inspector clears the selection (and any open transfer)', () => {
        let state = select(initialEntitySelectionState);
        state = entitySelectionReducer(state, { type: 'open_transfer' });
        state = entitySelectionReducer(state, { type: 'close_inspector' });

        expect(state.selectedEntityId).toBeNull();
        expect(state.selectedEntityType).toBeNull();
        expect(state.inspectorOpen).toBe(false);
        expect(state.transferOpen).toBe(false);
    });

    it('completing a transfer resets selection and raises a toast', () => {
        let state = select(initialEntitySelectionState);
        state = entitySelectionReducer(state, { type: 'open_transfer' });
        state = entitySelectionReducer(state, {
            type: 'transfer_complete',
            success: true,
            message: 'Moved to Reef',
        });

        expect(state.selectedEntityId).toBeNull();
        expect(state.inspectorOpen).toBe(false);
        expect(state.transferOpen).toBe(false);
        expect(state.transferMessage).toEqual({ type: 'success', text: 'Moved to Reef' });
    });

    it('a failed transfer raises an error toast', () => {
        let state = select(initialEntitySelectionState);
        state = entitySelectionReducer(state, {
            type: 'transfer_complete',
            success: false,
            message: 'Transfer failed',
        });
        expect(state.transferMessage).toEqual({ type: 'error', text: 'Transfer failed' });
    });

    it('clearing the toast leaves everything else untouched', () => {
        let state = select(initialEntitySelectionState);
        state = entitySelectionReducer(state, {
            type: 'transfer_complete',
            success: true,
            message: 'ok',
        });
        state = select(state, 9, 'fish');
        state = entitySelectionReducer(state, { type: 'clear_transfer_message' });

        expect(state.transferMessage).toBeNull();
        expect(state.selectedEntityId).toBe(9);
        expect(state.inspectorOpen).toBe(true);
    });

    it('keeps following opt-in and transfers it to a newly selected entity', () => {
        let state = select(initialEntitySelectionState);
        state = entitySelectionReducer(state, { type: 'toggle_follow' });
        expect(state.followEnabled).toBe(true);

        state = select(state, 77, 'fish');
        expect(state.selectedEntityId).toBe(77);
        expect(state.followEnabled).toBe(true);
    });

    it('double-click follow selects the fish and starts the camera without opening the inspector', () => {
        const state = entitySelectionReducer(initialEntitySelectionState, {
            type: 'select_and_follow',
            entityId: 77,
            entityType: 'fish',
        });

        expect(state.selectedEntityId).toBe(77);
        expect(state.inspectorOpen).toBe(false);
        expect(state.followEnabled).toBe(true);
    });

    it('a subsequent select on the followed fish opens the inspector without dropping follow', () => {
        let state = entitySelectionReducer(initialEntitySelectionState, {
            type: 'select_and_follow',
            entityId: 77,
            entityType: 'fish',
        });
        state = select(state, 77, 'fish');

        expect(state.inspectorOpen).toBe(true);
        expect(state.followEnabled).toBe(true);
    });

    it('stops following and explains when the selected entity disappears', () => {
        let state = select(initialEntitySelectionState);
        state = entitySelectionReducer(state, { type: 'toggle_follow' });
        state = entitySelectionReducer(state, { type: 'reconcile_entities', entityIds: [1, 2, 3] });

        expect(state.selectedEntityMissing).toBe(true);
        expect(state.followEnabled).toBe(false);
        expect(state.inspectorOpen).toBe(true);
        expect(state.transferOpen).toBe(false);
    });

    it('does not treat a full-state resync containing the selected entity as a disappearance', () => {
        let state = select(initialEntitySelectionState);
        state = entitySelectionReducer(state, { type: 'reconcile_entities', entityIds: [42, 99] });

        expect(state.selectedEntityMissing).toBe(false);
        expect(state.selectedEntityId).toBe(42);
    });
});
