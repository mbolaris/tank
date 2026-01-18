import { useState, useCallback, useEffect } from 'react';

export type TabId = 'play' | 'soccer' | 'poker' | 'ecosystem' | 'genetics';

export const TAB_IDS: TabId[] = ['play', 'soccer', 'poker', 'ecosystem', 'genetics'];

const STORAGE_KEY = 'tankview-active-tab';

function isValidTabId(value: string): value is TabId {
    return TAB_IDS.includes(value as TabId);
}

function getInitialTab(): TabId {
    const params = new URLSearchParams(window.location.search);
    const urlTab = params.get('tab');
    if (urlTab && isValidTabId(urlTab)) {
        return urlTab;
    }

    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && isValidTabId(stored)) {
        return stored;
    }

    return 'play';
}

export function useActiveTab(): [TabId, (tab: TabId) => void] {
    const [activeTab, setActiveTab] = useState<TabId>(getInitialTab);

    const handleTabChange = useCallback((tab: TabId) => {
        setActiveTab(tab);
        localStorage.setItem(STORAGE_KEY, tab);

        const url = new URL(window.location.href);
        url.searchParams.set('tab', tab);
        window.history.replaceState({}, '', url.toString());
    }, []);

    useEffect(() => {
        const handlePopState = () => {
            const params = new URLSearchParams(window.location.search);
            const urlTab = params.get('tab');
            if (urlTab && isValidTabId(urlTab)) {
                setActiveTab(urlTab);
            }
        };

        window.addEventListener('popstate', handlePopState);
        return () => window.removeEventListener('popstate', handlePopState);
    }, []);

    return [activeTab, handleTabChange];
}
