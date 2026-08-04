import { useEffect, useState } from 'react';

/**
 * A once-a-second clock, running only while data is stale.
 *
 * "last update 14s ago" has to keep counting even though no payload is
 * arriving to trigger a re-render. This is presentation-only: it uses browser
 * monotonic time and never reaches simulation state, replay, fingerprints, or
 * deterministic event ids.
 *
 * Returns undefined when not stale, so nothing re-renders on a healthy feed.
 */
export function useStaleClock(active: boolean, intervalMs = 1000): number | undefined {
    const [nowMs, setNowMs] = useState<number | undefined>(undefined);

    useEffect(() => {
        if (!active) {
            setNowMs(undefined);
            return;
        }
        setNowMs(performance.now());
        const timer = setInterval(() => setNowMs(performance.now()), intervalMs);
        return () => clearInterval(timer);
    }, [active, intervalMs]);

    return nowMs;
}
