
import { useState, useCallback, useEffect } from 'react';
import type { ViewMode } from '../rendering/types';
import type { WorldType } from '../types/world';
import { isTopDownOnly } from '../types/world';
import { config } from '../config';

const STORAGE_KEY = 'tank_view_mode_override';
const WORLD_TYPE_KEY = 'tank_world_type';

function isValidWorldType(value: string): boolean {
    return value === 'tank' || value === 'petri' || value === 'soccer_training' || value === 'soccer';
}

export interface UseViewModeResult {
    effectiveViewMode: ViewMode;
    overrideViewMode: ViewMode | null;
    setOverrideViewMode: (mode: ViewMode | null) => void;
    clearOverride: () => void;
    worldType: WorldType;
    setWorldType: (worldType: WorldType) => void;
}

export function useViewMode(serverViewMode?: ViewMode, serverWorldType?: string, tankId?: string): UseViewModeResult {
    // Initialize from local storage if available
    const [overrideViewMode, setStateOverrideViewMode] = useState<ViewMode | null>(() => {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored === 'side' || stored === 'topdown') {
            return stored;
        }
        return null;
    });

    // World type state - defaults to 'tank'
    const [worldType, setStateWorldType] = useState<WorldType>(() => {
        // Server world type takes precedence
        if (serverWorldType && isValidWorldType(serverWorldType)) {
            return serverWorldType as WorldType;
        }
        // Check localStorage for saved preference
        const stored = localStorage.getItem(WORLD_TYPE_KEY);
        if (stored && isValidWorldType(stored)) {
            return stored as WorldType;
        }
        // Default to Tank mode
        return 'tank';
    });

    // Track incomplete optimistic updates to prevent flickering
    const [optimisticState, setOptimisticState] = useState<{
        targetWorldType: WorldType;
        timestamp: number;
    } | null>(null);

    // Sync local world type with server state
    // Server is authoritative - we only show optimistic updates during explicit user toggles
    useEffect(() => {
        if (!serverWorldType || !isValidWorldType(serverWorldType)) return;

        const serverType = serverWorldType as WorldType;

        // If we have an optimistic update pending, handle it
        if (optimisticState) {
            // If server has caught up to our optimistic target, clear the optimistic state
            if (serverType === optimisticState.targetWorldType) {
                setOptimisticState(null);
                setStateWorldType(serverType);
                return;
            }

            // If pending update is too old (> 2 seconds), discard it and trust server
            if (Date.now() - optimisticState.timestamp > 2000) {
                setOptimisticState(null);
                setStateWorldType(serverType);
                return;
            }

            // Otherwise, keep showing optimistic state (don't update from server yet)
            return;
        }

        // No optimistic update - server is authoritative
        // On initial load or after user interaction completes, sync from server
        setStateWorldType(serverType);
    }, [serverWorldType, optimisticState]);



    const setOverrideViewMode = useCallback((mode: ViewMode | null) => {
        setStateOverrideViewMode(mode);
        if (mode) {
            localStorage.setItem(STORAGE_KEY, mode);
        } else {
            localStorage.removeItem(STORAGE_KEY);
        }
    }, []);

    const setWorldType = useCallback(async (newWorldType: WorldType) => {
        // Optimistic update
        setStateWorldType(newWorldType);
        setOptimisticState({
            targetWorldType: newWorldType,
            timestamp: Date.now()
        });

        // If connected to a specific tank, persist mode to server
        if (tankId) {
            try {
                await fetch(`${config.apiBaseUrl}/api/worlds/${tankId}/mode`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ world_type: newWorldType })
                });
            } catch (error) {
                console.error('Failed to update tank mode:', error);
                // On error, clear optimistic state so next server update fixes it
                setOptimisticState(null);
            }
        }

        // If switching to Tank mode, reset view to side (default)
        // This prevents getting stuck in forced top-down views
        if (newWorldType === 'tank') {
            setOverrideViewMode(null);
        }

        localStorage.setItem(WORLD_TYPE_KEY, newWorldType);
    }, [tankId, setOverrideViewMode]);


    const clearOverride = useCallback(() => {
        setOverrideViewMode(null);
    }, [setOverrideViewMode]);

    // Effective mode prioritizes override -> server -> default ('side')
    let effectiveViewMode = overrideViewMode ?? serverViewMode ?? 'side';

    // Top-down only modes (petri, soccer_training, soccer) force top-down view
    if (isTopDownOnly(worldType)) {
        effectiveViewMode = 'topdown';
    }

    return {
        effectiveViewMode,
        overrideViewMode,
        setOverrideViewMode,
        clearOverride,
        worldType,
        setWorldType,
    };
}
