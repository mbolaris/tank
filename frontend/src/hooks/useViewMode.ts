
import { useState, useCallback } from 'react';
import type { ViewMode } from '../rendering/types';

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

export function useViewMode(serverViewMode?: ViewMode): UseViewModeResult {
    // Initialize from local storage if available
    const [overrideViewMode, setStateOverrideViewMode] = useState<ViewMode | null>(() => {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored === 'side' || stored === 'topdown') {
            return stored;
        }
        return null;
    });

    // Petri mode toggle (circular dish rendering)
    const [petriMode, setStatePetriMode] = useState<boolean>(() => {
        return localStorage.getItem(PETRI_MODE_KEY) === 'true';
    });

    const setOverrideViewMode = useCallback((mode: ViewMode | null) => {
        setStateOverrideViewMode(mode);
        if (mode) {
            localStorage.setItem(STORAGE_KEY, mode);
        } else {
            localStorage.removeItem(STORAGE_KEY);
        }
    }, []);

    const setPetriMode = useCallback((enabled: boolean) => {
        setStatePetriMode(enabled);
        localStorage.setItem(PETRI_MODE_KEY, enabled ? 'true' : 'false');
    }, []);

    const clearOverride = useCallback(() => {
        setOverrideViewMode(null);
    }, [setOverrideViewMode]);

    // Effective mode prioritizes override -> server -> default ('side')
    const effectiveViewMode = overrideViewMode ?? serverViewMode ?? 'side';

    return {
        effectiveViewMode,
        overrideViewMode,
        setOverrideViewMode,
        clearOverride,
        petriMode,
        setPetriMode,
    };
}
