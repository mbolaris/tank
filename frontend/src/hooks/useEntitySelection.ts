/**
 * Entity selection state machine for the tank canvas (U4/E1).
 *
 * Clicking an entity selects it and opens the inspector drawer; transfer is
 * an explicit secondary action launched from inside the inspector, never a
 * direct result of a canvas click. Modeled as a pure reducer so the
 * interaction contract is unit-testable without a DOM.
 */

import { useCallback, useEffect, useReducer } from 'react';

export interface TransferMessage {
    type: 'success' | 'error';
    text: string;
}

export interface EntitySelectionState {
    selectedEntityId: number | null;
    selectedEntityType: string | null;
    inspectorOpen: boolean;
    transferOpen: boolean;
    transferMessage: TransferMessage | null;
}

export type EntitySelectionAction =
    | { type: 'select'; entityId: number; entityType: string }
    | { type: 'close_inspector' }
    | { type: 'open_transfer' }
    | { type: 'close_transfer' }
    | { type: 'transfer_complete'; success: boolean; message: string }
    | { type: 'clear_transfer_message' };

export const initialEntitySelectionState: EntitySelectionState = {
    selectedEntityId: null,
    selectedEntityType: null,
    inspectorOpen: false,
    transferOpen: false,
    transferMessage: null,
};

export function entitySelectionReducer(
    state: EntitySelectionState,
    action: EntitySelectionAction
): EntitySelectionState {
    switch (action.type) {
        case 'select':
            // A canvas click always lands in the inspector — never in transfer.
            return {
                ...state,
                selectedEntityId: action.entityId,
                selectedEntityType: action.entityType,
                inspectorOpen: true,
                transferOpen: false,
            };
        case 'close_inspector':
            return { ...initialEntitySelectionState, transferMessage: state.transferMessage };
        case 'open_transfer':
            // Transfer is only reachable from an active selection.
            return state.selectedEntityId === null ? state : { ...state, transferOpen: true };
        case 'close_transfer':
            // Cancelling transfer returns to the inspector with selection intact.
            return { ...state, transferOpen: false };
        case 'transfer_complete':
            return {
                ...initialEntitySelectionState,
                transferMessage: {
                    type: action.success ? 'success' : 'error',
                    text: action.message,
                },
            };
        case 'clear_transfer_message':
            return { ...state, transferMessage: null };
    }
}

const TRANSFER_MESSAGE_TIMEOUT_MS = 5000;

export function useEntitySelection() {
    const [state, dispatch] = useReducer(entitySelectionReducer, initialEntitySelectionState);

    // Auto-dismiss the transfer toast (matches previous TankView behavior).
    useEffect(() => {
        if (!state.transferMessage) return;
        const timer = window.setTimeout(
            () => dispatch({ type: 'clear_transfer_message' }),
            TRANSFER_MESSAGE_TIMEOUT_MS
        );
        return () => window.clearTimeout(timer);
    }, [state.transferMessage]);

    const selectEntity = useCallback(
        (entityId: number, entityType: string) => dispatch({ type: 'select', entityId, entityType }),
        []
    );
    const closeInspector = useCallback(() => dispatch({ type: 'close_inspector' }), []);
    const openTransfer = useCallback(() => dispatch({ type: 'open_transfer' }), []);
    const closeTransfer = useCallback(() => dispatch({ type: 'close_transfer' }), []);
    const completeTransfer = useCallback(
        (success: boolean, message: string) =>
            dispatch({ type: 'transfer_complete', success, message }),
        []
    );

    return {
        ...state,
        selectEntity,
        closeInspector,
        openTransfer,
        closeTransfer,
        completeTransfer,
    };
}
