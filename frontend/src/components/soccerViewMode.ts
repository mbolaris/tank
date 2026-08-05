/**
 * Arena view modes (§4).
 *
 * Deliberately **not** the same concept as `SoccerMatchState.view_mode`, which
 * selects a renderer projection ('side' / 'topdown'). This is the arena's
 * presentation mode: which rails are mounted, how much the scoreboard is
 * compressed, and whether the pitch carries tactical overlays.
 */

export type ArenaViewMode = 'broadcast' | 'tactical';

export const ARENA_VIEW_MODES: readonly ArenaViewMode[] = ['broadcast', 'tactical'];

export const ARENA_VIEW_MODE_STORAGE_KEY = 'tank_soccer_arena_view_mode';

const VIEW_MODE_LABELS: Record<ArenaViewMode, string> = {
    broadcast: 'Broadcast',
    tactical: 'Tactical',
};

/** §7: `B` / `T` switch modes. Matched case-insensitively on `KeyboardEvent.key`. */
const VIEW_MODE_HOTKEYS: Record<string, ArenaViewMode> = {
    b: 'broadcast',
    t: 'tactical',
};

export function isArenaViewMode(value: unknown): value is ArenaViewMode {
    return typeof value === 'string' && (ARENA_VIEW_MODES as readonly string[]).includes(value);
}

export function arenaViewModeLabel(mode: ArenaViewMode): string {
    return VIEW_MODE_LABELS[mode];
}

/**
 * The mode a keystroke selects, or null when the key is not a mode hotkey.
 *
 * Returns null for any modified keystroke so the arena never steals `Ctrl+B`
 * and friends from the browser.
 */
export function viewModeForHotkey(event: Pick<KeyboardEvent, 'key' | 'ctrlKey' | 'metaKey' | 'altKey'>): ArenaViewMode | null {
    if (event.ctrlKey || event.metaKey || event.altKey) return null;
    return VIEW_MODE_HOTKEYS[event.key.toLowerCase()] ?? null;
}

export function readStoredViewMode(): ArenaViewMode {
    if (typeof window === 'undefined') return 'broadcast';
    try {
        const stored = window.localStorage.getItem(ARENA_VIEW_MODE_STORAGE_KEY);
        // An unknown stored value is treated as absent rather than as an error:
        // it is what a downgrade from a build with more modes leaves behind.
        return isArenaViewMode(stored) ? stored : 'broadcast';
    } catch {
        return 'broadcast';
    }
}

export function writeStoredViewMode(mode: ArenaViewMode): void {
    try {
        window.localStorage.setItem(ARENA_VIEW_MODE_STORAGE_KEY, mode);
    } catch {
        // Private browsing and storage-disabled contexts still get a usable arena.
    }
}
