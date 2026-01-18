import type { ReactNode } from 'react';
import { TAB_IDS, type TabId } from './useActiveTab';
import styles from './TankTabs.module.css';

interface Tab {
    id: TabId;
    label: string;
    icon: ReactNode;
}

const TAB_LABELS: Record<TabId, string> = {
    play: 'Play',
    soccer: 'Soccer',
    poker: 'Poker',
    ecosystem: 'Ecosystem',
    genetics: 'Genetics',
};

const TAB_ICONS: Record<TabId, ReactNode> = {
    play: <span className={styles.tabIcon}>▶</span>,
    soccer: <span className={styles.tabIcon}>⚽</span>,
    poker: <span className={styles.tabIcon}>♠</span>,
    ecosystem: <span className={styles.tabIcon}>🌿</span>,
    genetics: <span className={styles.tabIcon}>🧬</span>,
};

const TABS: Tab[] = TAB_IDS.map((id) => ({
    id,
    label: TAB_LABELS[id],
    icon: TAB_ICONS[id],
}));

interface TankTabsProps {
    activeTab: TabId;
    onTabChange: (tab: TabId) => void;
}

export function TankTabs({ activeTab, onTabChange }: TankTabsProps) {
    return (
        <div className={styles.tabBar}>
            {TABS.map((tab) => (
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
