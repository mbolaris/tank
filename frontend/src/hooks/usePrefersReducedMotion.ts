import { useEffect, useState } from 'react';

const QUERY = '(prefers-reduced-motion: reduce)';

/**
 * Whether the viewer has asked for reduced motion.
 *
 * Broadcast cards still appear and still hold long enough to read - only their
 * entrance animation is suppressed. Suppressing the card itself would hide
 * information, not motion.
 */
export function usePrefersReducedMotion(): boolean {
    const [prefersReduced, setPrefersReduced] = useState(false);

    useEffect(() => {
        if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return;
        const query = window.matchMedia(QUERY);
        setPrefersReduced(query.matches);
        const onChange = (event: MediaQueryListEvent) => setPrefersReduced(event.matches);
        query.addEventListener('change', onChange);
        return () => query.removeEventListener('change', onChange);
    }, []);

    return prefersReduced;
}
