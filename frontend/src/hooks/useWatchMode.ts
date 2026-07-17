import { useCallback, useState } from 'react';

export interface UseWatchModeResult {
    watchMode: boolean;
    /** Leaves Watch Mode outright (e.g. before navigating to a panel). */
    exitWatchMode: () => void;
    /** Toggles Watch Mode, cross-fading via the View Transitions API where
     * supported. The chrome-hidden/fullscreen layout swap mixes an
     * auto-height column with an explicit viewport-height one, which plain
     * CSS transitions can't interpolate between; startViewTransition
     * sidesteps that by cross-fading old/new frames instead, and simply
     * no-ops to an instant toggle where unsupported. */
    toggleWatchMode: () => void;
}

export function useWatchMode(): UseWatchModeResult {
    const [watchMode, setWatchMode] = useState(false);

    const exitWatchMode = useCallback(() => setWatchMode(false), []);

    const toggleWatchMode = useCallback(() => {
        const applyToggle = () => setWatchMode((prev) => !prev);
        if (typeof document.startViewTransition === 'function') {
            document.startViewTransition(applyToggle);
        } else {
            applyToggle();
        }
    }, []);

    return { watchMode, exitWatchMode, toggleWatchMode };
}
