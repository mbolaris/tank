import React, { useState, useEffect, useCallback } from 'react';
import styles from './TankTabs.module.css';

export type TabId = 'play' | 'soccer' | 'poker' | 'ecosystem' | 'genetics';

interface Tab {
    id: TabId;
    label: string;
    icon: React.ReactNode;
}

const TABS: Tab[] = [
    { id: 'play', label: 'Play', icon: <span className={styles.tabIcon}>▶</span> },
    { id: 'soccer', label: 'Soccer', icon: <span className={styles.tabIcon}>⚽</span> },
    { id: 'poker', label: 'Poker', icon: <span className={styles.tabIcon}>♠</span> },
    { id: 'ecosystem', label: 'Ecosystem', icon: <span className={styles.tabIcon}>🌿</span> },
    { id: 'genetics', label: 'Genetics', icon: <span className={styles.tabIcon}>🧬</span> },
];

const STORAGE_KEY = 'tankview-active-tab';

function getInitialTab(): TabId {
    // Check URL params first
    const params = new URLSearchParams(window.location.search);
    const urlTab = params.get('tab') as TabId | null;
    if (urlTab && TABS.some(t => t.id === urlTab)) {
        return urlTab;
    }

    // Fall back to localStorage
    const stored = localStorage.getItem(STORAGE_KEY) as TabId | null;
    if (stored && TABS.some(t => t.id === stored)) {
        return stored;
    }

    return 'play';
}

interface TankTabsProps {
    activeTab: TabId;
    onTabChange: (tab: TabId) => void;
}

export function TankTabs({ activeTab, onTabChange }: TankTabsProps) {
    return (
        <div className={styles.tabBar}>
            {TABS.map(tab => (
                <button
                    key={tab.id}
                    className={`${styles.tab} ${activeTab === tab.id ? styles.active : ''}`}
                    onClick={() => onTabChange(tab.id)}
                    aria-selected={activeTab === tab.id}
                    role="tab"
                >
                    {tab.icon}
                    <span className={styles.tabLabel}>{tab.label}</span>
                </button>
            ))}
        </div>
    );
}

export function useActiveTab(): [TabId, (tab: TabId) => void] {
    const [activeTab, setActiveTab] = useState<TabId>(getInitialTab);

    const handleTabChange = useCallback((tab: TabId) => {
        setActiveTab(tab);
        localStorage.setItem(STORAGE_KEY, tab);

        // Update URL without page reload
        const url = new URL(window.location.href);
        url.searchParams.set('tab', tab);
        window.history.replaceState({}, '', url.toString());
    }, []);

    // Listen for popstate (browser back/forward)
    useEffect(() => {
        const handlePopState = () => {
            const params = new URLSearchParams(window.location.search);
            const urlTab = params.get('tab') as TabId | null;
            if (urlTab && TABS.some(t => t.id === urlTab)) {
                setActiveTab(urlTab);
            }
        };

        window.addEventListener('popstate', handlePopState);
        return () => window.removeEventListener('popstate', handlePopState);
    }, []);

    return [activeTab, handleTabChange];
}
