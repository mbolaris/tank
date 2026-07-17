import { useCallback, useState } from 'react';
import type { UiMode } from '../components/ModeSwitch';
import type { Command } from '../types/simulation';
import type { PanelId } from './useVisiblePanels';

export type BuildObjectKind = 'algae_reef' | 'protein_grotto' | 'decorative_rock' | 'castle';

interface UseUiModeArgs {
    watchMode: boolean;
    enterWatchMode: () => void;
    exitWatchMode: () => void;
    visibleCount: number;
    showOnly: (id: PanelId) => void;
    sendCommand: (command: Command) => void;
}

export interface UseUiModeResult {
    /** The one active top-level composition, or null when Analyze has no panel open. */
    uiMode: UiMode | null;
    /** Switches to the given mode, exiting whichever of the other two was active. */
    selectMode: (mode: UiMode) => void;
    buildMode: boolean;
    buildKind: BuildObjectKind | null;
    setBuildKind: (kind: BuildObjectKind | null) => void;
    buildSelectedObjectId: number | null;
    setBuildSelectedObjectId: (id: number | null) => void;
}

/** Owns Build Mode's state and derives the single active Watch/Build/Analyze
 * mode for ModeSwitch. Analyze has no dedicated boolean - it's "on" whenever
 * a panel is visible - so selecting it restores the last-open panel,
 * defaulting to Trends only if none was ever open. */
export function useUiMode({
    watchMode,
    enterWatchMode,
    exitWatchMode,
    visibleCount,
    showOnly,
    sendCommand,
}: UseUiModeArgs): UseUiModeResult {
    const [buildMode, setBuildMode] = useState(false);
    const [buildKind, setBuildKind] = useState<BuildObjectKind | null>(null);
    const [buildSelectedObjectId, setBuildSelectedObjectId] = useState<number | null>(null);

    const enterBuildMode = useCallback(() => {
        if (buildMode) return;
        setBuildMode(true);
        setBuildKind(null);
        setBuildSelectedObjectId(null);
        sendCommand({ command: 'pause' });
    }, [buildMode, sendCommand]);

    const exitBuildMode = useCallback(() => {
        if (!buildMode) return;
        setBuildMode(false);
        setBuildKind(null);
        setBuildSelectedObjectId(null);
        sendCommand({ command: 'resume' });
    }, [buildMode, sendCommand]);

    const uiMode: UiMode | null = watchMode ? 'watch' : buildMode ? 'build' : visibleCount > 0 ? 'analyze' : null;

    const selectMode = useCallback((mode: UiMode) => {
        if (mode === 'watch') {
            exitBuildMode();
            enterWatchMode();
            return;
        }
        exitWatchMode();
        if (mode === 'build') {
            enterBuildMode();
        } else {
            exitBuildMode();
            if (visibleCount === 0) showOnly('trends');
        }
    }, [exitBuildMode, enterWatchMode, exitWatchMode, enterBuildMode, visibleCount, showOnly]);

    return {
        uiMode,
        selectMode,
        buildMode,
        buildKind,
        setBuildKind,
        buildSelectedObjectId,
        setBuildSelectedObjectId,
    };
}
