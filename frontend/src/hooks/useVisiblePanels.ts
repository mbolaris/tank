import { useCallback, useMemo, useState } from 'react';

export type PanelId = 'soccer' | 'poker' | 'ecosystem' | 'genetics';

const STORAGE_KEY = 'tankview.visiblePanels.v1';
const ALL_PANELS: PanelId[] = ['soccer', 'poker', 'ecosystem', 'genetics'];

function sanitizePanels(value: unknown, fallback: PanelId[]): PanelId[] {
    if (!Array.isArray(value)) return fallback;
    const filtered = value.filter((v): v is PanelId => ALL_PANELS.includes(v as PanelId));
    return filtered.length ? Array.from(new Set(filtered)) : fallback;
}

export function useVisiblePanels(defaultPanels: PanelId[] = ['soccer', 'poker']): {
    visible: PanelId[];
    isVisible: (id: PanelId) => boolean;
    toggle: (id: PanelId) => void;
    setVisible: (ids: PanelId[]) => void;
    showOnly: (id: PanelId) => void;
    showAll: () => void;
    hideAll: () => void;
} {
    const [visible, setVisibleState] = useState<PanelId[]>(() => {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) return defaultPanels;
            return sanitizePanels(JSON.parse(raw), defaultPanels);
        } catch {
            return defaultPanels;
        }
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

    const toggle = useCallback(
        (id: PanelId) => {
            persist(visible.includes(id) ? visible.filter((p) => p !== id) : [...visible, id]);
        },
        [persist, visible]
    );

    const setVisible = useCallback(
        (ids: PanelId[]) => {
            persist(sanitizePanels(ids, defaultPanels));
        },
        [persist, defaultPanels]
    );

    const showOnly = useCallback((id: PanelId) => persist([id]), [persist]);
    const showAll = useCallback(() => persist([...ALL_PANELS]), [persist]);
    const hideAll = useCallback(() => persist([]), [persist]);

    return useMemo(
        () => ({
            visible,
            isVisible,
            toggle,
            setVisible,
            showOnly,
            showAll,
            hideAll,
        }),
        [visible, isVisible, toggle, setVisible, showOnly, showAll, hideAll]
    );
}
