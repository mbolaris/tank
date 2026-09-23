import { useCallback, useEffect, useRef, useState } from 'react';
import type { Command } from '../types/simulation';

/**
 * The tank's soccer-ball toggle: follows the server's `tank_soccer_enabled`
 * until the user flips it, after which the user's choice wins.
 *
 * `toggleSoccer` keeps its identity across WebSocket payloads so memoized
 * controls that receive it do not re-render with every message.
 */
export function useTankSoccerToggle(
    serverEnabled: boolean | undefined,
    sendCommand: (command: Command) => void
): { showSoccer: boolean; toggleSoccer: () => void } {
    const [showSoccer, setShowSoccer] = useState<boolean | null>(null); // null = not yet synced from server
    const userToggled = useRef(false);

    // Sync from the server on initial load and ongoing updates
    useEffect(() => {
        if (serverEnabled !== undefined && !userToggled.current) {
            setShowSoccer(serverEnabled);
        }
    }, [serverEnabled]);

    // null (unknown) reads as false until the server confirms
    const effective = showSoccer ?? false;

    const toggleSoccer = useCallback(() => {
        userToggled.current = true;
        const next = !effective;
        setShowSoccer(next);
        sendCommand({ command: 'set_tank_soccer_enabled', data: { enabled: next } });
    }, [effective, sendCommand]);

    return { showSoccer: effective, toggleSoccer };
}
