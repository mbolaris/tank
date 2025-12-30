
import { useState, useEffect, useCallback } from 'react';
import type { ViewMode } from '../rendering/types';

const STORAGE_KEY = 'tank_view_mode_override';

export interface UseViewModeResult {
    effectiveViewMode: ViewMode;
    overrideViewMode: ViewMode | null;
    setOverrideViewMode: (mode: ViewMode | null) => void;
    clearOverride: () => void;
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

    const setOverrideViewMode = useCallback((mode: ViewMode | null) => {
        setStateOverrideViewMode(mode);
        if (mode) {
            localStorage.setItem(STORAGE_KEY, mode);
        } else {
            localStorage.removeItem(STORAGE_KEY);
        }
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
        clearOverride
    };
}
