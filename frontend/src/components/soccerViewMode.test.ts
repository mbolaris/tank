import { afterEach, describe, expect, it, vi } from 'vitest';
import {
    ARENA_VIEW_MODE_STORAGE_KEY,
    arenaViewModeLabel,
    isAnalyticalMode,
    isArenaViewMode,
    readStoredViewMode,
    viewModeForHotkey,
    writeStoredViewMode,
} from './soccerViewMode';

function stubStorage(initial: Record<string, string> = {}) {
    const store = new Map(Object.entries(initial));
    vi.stubGlobal('window', {
        localStorage: {
            getItem: (key: string) => store.get(key) ?? null,
            setItem: (key: string, value: string) => void store.set(key, value),
        },
    });
    return store;
}

afterEach(() => vi.unstubAllGlobals());

describe('arena view mode', () => {
    it('round-trips through storage', () => {
        const store = stubStorage();
        writeStoredViewMode('tactical');
        expect(store.get(ARENA_VIEW_MODE_STORAGE_KEY)).toBe('tactical');
        expect(readStoredViewMode()).toBe('tactical');
    });

    it('treats an unrecognised stored mode as absent rather than rendering it', () => {
        // What a downgrade from a build with more modes leaves behind.
        stubStorage({ [ARENA_VIEW_MODE_STORAGE_KEY]: 'holographic' });
        expect(readStoredViewMode()).toBe('broadcast');
        expect(isArenaViewMode('holographic')).toBe(false);
    });

    it('falls back to broadcast when storage throws', () => {
        vi.stubGlobal('window', {
            localStorage: {
                getItem: () => {
                    throw new Error('storage disabled');
                },
                setItem: () => {
                    throw new Error('storage disabled');
                },
            },
        });
        expect(readStoredViewMode()).toBe('broadcast');
        expect(() => writeStoredViewMode('tactical')).not.toThrow();
    });

    it('maps B, T and A to their modes, case-insensitively', () => {
        expect(viewModeForHotkey({ key: 'b', ctrlKey: false, metaKey: false, altKey: false })).toBe('broadcast');
        expect(viewModeForHotkey({ key: 'T', ctrlKey: false, metaKey: false, altKey: false })).toBe('tactical');
        expect(viewModeForHotkey({ key: 'a', ctrlKey: false, metaKey: false, altKey: false })).toBe('analysis');
        expect(viewModeForHotkey({ key: 'q', ctrlKey: false, metaKey: false, altKey: false })).toBeNull();
    });

    it('marks the two modes that annotate the pitch', () => {
        expect(isAnalyticalMode('tactical')).toBe(true);
        expect(isAnalyticalMode('analysis')).toBe(true);
        expect(isAnalyticalMode('broadcast')).toBe(false);
    });

    it('never steals a modified keystroke from the browser', () => {
        expect(viewModeForHotkey({ key: 'b', ctrlKey: true, metaKey: false, altKey: false })).toBeNull();
        expect(viewModeForHotkey({ key: 't', ctrlKey: false, metaKey: true, altKey: false })).toBeNull();
        expect(viewModeForHotkey({ key: 't', ctrlKey: false, metaKey: false, altKey: true })).toBeNull();
    });

    it('labels each mode', () => {
        expect(arenaViewModeLabel('broadcast')).toBe('Broadcast');
        expect(arenaViewModeLabel('tactical')).toBe('Tactical');
        expect(arenaViewModeLabel('analysis')).toBe('Analysis');
    });
});
