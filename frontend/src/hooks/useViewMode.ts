
import { useState, useCallback, useEffect, useRef } from 'react';
import type { ViewMode } from '../rendering/types';
import { config } from '../config';

const STORAGE_KEY = 'tank_view_mode_override';
const PETRI_MODE_KEY = 'tank_petri_mode';

export interface UseViewModeResult {
    effectiveViewMode: ViewMode;
    overrideViewMode: ViewMode | null;
    setOverrideViewMode: (mode: ViewMode | null) => void;
    clearOverride: () => void;
    petriMode: boolean;
    setPetriMode: (enabled: boolean) => void;
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

    // Petri mode toggle (circular dish rendering) - defaults to false (Tank mode)
    const [petriMode, setStatePetriMode] = useState<boolean>(() => {
        // Server world type takes precedence
        if (serverWorldType) return serverWorldType === 'petri';
        // Check localStorage for saved preference
        const stored = localStorage.getItem(PETRI_MODE_KEY);
        if (stored !== null) return stored === 'true';
        // Default to Tank mode (false)
        return false;
    });

    // Track incomplete optimistic updates to prevent flickering
    const [optimisticState, setOptimisticState] = useState<{
        targetMode: boolean;
        timestamp: number;
    } | null>(null);

    // Track if user has ever explicitly set mode this session (vs just loading)
    const hasUserInteractedRef = useRef(false);

    // Sync local petri mode with server state, but ONLY when:
    // 1. User explicitly made a mode change (optimistic update pending)
    // 2. NOT on initial load (we want frontend default to win on startup)
    useEffect(() => {
        if (!serverWorldType) return;

        const serverIsPetri = serverWorldType === 'petri';

        // Only process server updates if user has explicitly changed mode
        // This prevents server from overriding default Tank mode on startup
        if (!optimisticState && !hasUserInteractedRef.current) {
            // Initial load - don't sync from server, keep frontend default
            return;
        }

        if (optimisticState) {
            // If server has caught up to our optimistic target, clear the optimistic state
            if (serverIsPetri === optimisticState.targetMode) {
                setOptimisticState(null);
                setStatePetriMode(serverIsPetri);
                return;
            }

            // If pending update is too old (> 2 seconds), discard it and trust server
            if (Date.now() - optimisticState.timestamp > 2000) {
                setOptimisticState(null);
                setStatePetriMode(serverIsPetri);
                return;
            }

            // Otherwise, keep showing optimistic state (don't update from server yet)
            return;
        }

        setStatePetriMode(serverIsPetri);
    }, [serverWorldType, optimisticState]);

    // Force server to sync with frontend's default mode on startup
    // This ensures the server sends the correct entity data matching the frontend's mode
    const hasInitializedServerModeRef = useRef(false);
    useEffect(() => {
        // Only run once on initial mount when we have a tankId
        if (hasInitializedServerModeRef.current || !tankId) {
            return;
        }

        // Wait for serverWorldType to be available
        if (!serverWorldType) {
            return;
        }

        hasInitializedServerModeRef.current = true;

        const serverIsPetri = serverWorldType === 'petri';

        // If server is in petri mode but frontend defaulted to tank mode (petriMode === false),
        // force the server to switch to tank mode
        if (serverIsPetri && !petriMode) {
            console.log('[useViewMode] Server is petri but frontend defaulted to tank, forcing server sync');
            fetch(`${config.apiBaseUrl}/api/tanks/${tankId}/mode`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ world_type: 'tank' })
            }).catch(error => {
                console.error('Failed to sync server mode to tank:', error);
            });
        }
    }, [tankId, serverWorldType, petriMode]);

    const setOverrideViewMode = useCallback((mode: ViewMode | null) => {
        setStateOverrideViewMode(mode);
        if (mode) {
            localStorage.setItem(STORAGE_KEY, mode);
        } else {
            localStorage.removeItem(STORAGE_KEY);
        }
    }, []);

    const setPetriMode = useCallback(async (enabled: boolean) => {
        // Mark that user has explicitly interacted with mode toggle
        hasUserInteractedRef.current = true;

        // Optimistic update
        setStatePetriMode(enabled);
        setOptimisticState({
            targetMode: enabled,
            timestamp: Date.now()
        });

        // If connected to a specific tank, persist mode to server
        if (tankId) {
            try {
                const targetMode = enabled ? 'petri' : 'tank';
                await fetch(`${config.apiBaseUrl}/api/tanks/${tankId}/mode`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ world_type: targetMode })
                });
            } catch (error) {
                console.error('Failed to update tank mode:', error);
                // On error, clear optimistic state so next server update fixes it
                setOptimisticState(null);
            }
        }

        // If switching to Tank mode, reset view to side (default)
        // This prevents getting stuck in "Top Down" view which renders fish as microbes
        if (!enabled) {
            setOverrideViewMode(null);
        }

        localStorage.setItem(PETRI_MODE_KEY, enabled ? 'true' : 'false');
    }, [tankId, setOverrideViewMode]);

    const clearOverride = useCallback(() => {
        setOverrideViewMode(null);
    }, [setOverrideViewMode]);

    // Effective mode prioritizes override -> server -> default ('side')
    let effectiveViewMode = overrideViewMode ?? serverViewMode ?? 'side';

    // Petri mode only supports top-down view
    if (petriMode) {
        effectiveViewMode = 'topdown';
    }

    return {
        effectiveViewMode,
        overrideViewMode,
        setOverrideViewMode,
        clearOverride,
        petriMode,
        setPetriMode,
    };
}
