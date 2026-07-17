import { useCallback, useState } from 'react';

export interface UseWatchModeResult {
    watchMode: boolean;
    /** Enters Watch Mode, cross-fading via the View Transitions API where
     * supported. The chrome-hidden/fullscreen layout swap mixes an
     * auto-height column with an explicit viewport-height one, which plain
     * CSS transitions can't interpolate between; startViewTransition
     * sidesteps that by cross-fading old/new frames instead, and simply
     * no-ops to an instant switch where unsupported. */
    enterWatchMode: () => void;
    /** Leaves Watch Mode outright (e.g. before navigating to a panel). */
    exitWatchMode: () => void;
}

function withViewTransition(apply: () => void): void {
    if (typeof document.startViewTransition === 'function') {
        document.startViewTransition(apply);
    } else {
        apply();
    }
}

export function useWatchMode(): UseWatchModeResult {
    const [watchMode, setWatchMode] = useState(false);

    const enterWatchMode = useCallback(() => withViewTransition(() => setWatchMode(true)), []);
    const exitWatchMode = useCallback(() => setWatchMode(false), []);

    return { watchMode, enterWatchMode, exitWatchMode };
}
