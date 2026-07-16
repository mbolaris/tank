import { useCallback, useMemo, useState } from 'react';

export type PanelId = 'skills' | 'soccer' | 'poker' | 'ecosystem' | 'genetics' | 'trends' | 'insights';

// v3 changes the dashboard from a stack of independently-open panels to a
// focused workspace.  A new key deliberately gives existing users the new
// compact default instead of restoring the old, very tall stack.
const STORAGE_KEY = 'tankview.visiblePanels.v3';
const ALL_PANELS: PanelId[] = ['skills', 'soccer', 'poker', 'ecosystem', 'genetics', 'trends', 'insights'];

function sanitizePanels(value: unknown): PanelId[] | null {
    if (!Array.isArray(value)) return null;
    const filtered = value.filter((v): v is PanelId => ALL_PANELS.includes(v as PanelId));
    // The workspace intentionally permits no open panel, but never more than
    // one.  Keeping the latest selection is most useful to callers that pass
    // a list while restoring state.
    return Array.from(new Set(filtered)).slice(-1);
}

export function useVisiblePanels(defaultPanels: PanelId[] = ['trends']): {
    visible: PanelId[];
    isVisible: (id: PanelId) => boolean;
    toggle: (id: PanelId) => void;
    setVisible: (ids: PanelId[]) => void;
    showOnly: (id: PanelId) => void;
    hideAll: () => void;
} {
    const focusedDefault = defaultPanels.slice(-1);
    const [visible, setVisibleState] = useState<PanelId[]>(() => {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (raw) return sanitizePanels(JSON.parse(raw)) ?? focusedDefault;
        } catch {
            // Fall through to the focused default when storage is malformed
            // or unavailable.
        }
        return focusedDefault;
    });

    const persist = useCallback((next: PanelId[]) => {
        setVisibleState(next);
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
        } catch {
            // ignore storage failures (private mode, quota, etc.)
        }
    }, []);

    const isVisible = useCallback((id: PanelId) => visible.includes(id), [visible]);

    const toggle = useCallback((id: PanelId) => {
        setVisibleState((prev) => {
            const next = prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id];
            try {
                localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
            } catch {
                // ignore storage failures (private mode, quota, etc.)
            }
            return next;
        });
    }, []);

    const setVisible = useCallback(
        (ids: PanelId[]) => {
            persist(sanitizePanels(ids) ?? focusedDefault);
        },
        [persist, focusedDefault]
    );

    const showOnly = useCallback((id: PanelId) => persist([id]), [persist]);
    const hideAll = useCallback(() => persist([]), [persist]);

    return useMemo(
        () => ({
            visible,
            isVisible,
            toggle,
            setVisible,
            showOnly,
            hideAll,
        }),
        [visible, isVisible, toggle, setVisible, showOnly, hideAll]
    );
}
