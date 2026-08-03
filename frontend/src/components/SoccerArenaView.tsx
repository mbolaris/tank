import { useEffect, useState } from 'react';
import type { SoccerEventData, SoccerLeagueLiveState } from '../types/simulation';
import { SoccerPitch } from './SoccerPitch';
import styles from './SoccerArenaView.module.css';

interface SoccerArenaViewProps {
    liveState: SoccerLeagueLiveState | null;
    events: SoccerEventData[];
    worldId?: string;
    onBack: () => void;
}

const LEFT_RAIL_STORAGE_KEY = 'tank_soccer_arena_left_rail';
const RIGHT_RAIL_STORAGE_KEY = 'tank_soccer_arena_right_rail';

function readStoredRail(key: string): boolean {
    if (typeof window === 'undefined') return false;
    try {
        return window.localStorage.getItem(key) === 'expanded';
    } catch {
        return false;
    }
}

function writeStoredRail(key: string, expanded: boolean): void {
    try {
        window.localStorage.setItem(key, expanded ? 'expanded' : 'collapsed');
    } catch {
        // Private browsing and storage-disabled contexts still get a usable arena.
    }
}

function RailToggle({ label, expanded, onClick }: { label: string; expanded: boolean; onClick: () => void }) {
    return (
        <button
            type="button"
            className={styles.railToggle}
            onClick={onClick}
            aria-expanded={expanded}
            aria-label={`${expanded ? 'Collapse' : 'Expand'} ${label}`}
            title={`${expanded ? 'Collapse' : 'Expand'} ${label}`}
        >
            <span aria-hidden="true">{expanded ? '‹' : '›'}</span>
            <span className={styles.railToggleLabel}>{expanded ? label : label.slice(0, 1)}</span>
        </button>
    );
}

function RailPlaceholder({ title, detail }: { title: string; detail: string }) {
    return (
        <div className={styles.railContent}>
            <div className={styles.eyebrow}>{title}</div>
            <p>{detail}</p>
        </div>
    );
}

export function SoccerArenaView({ liveState, events, worldId, onBack }: SoccerArenaViewProps) {
    const [leftRailExpanded, setLeftRailExpanded] = useState(() => readStoredRail(LEFT_RAIL_STORAGE_KEY));
    const [rightRailExpanded, setRightRailExpanded] = useState(() => readStoredRail(RIGHT_RAIL_STORAGE_KEY));
    const activeMatch = liveState?.active_match ?? null;

    useEffect(() => {
        writeStoredRail(LEFT_RAIL_STORAGE_KEY, leftRailExpanded);
    }, [leftRailExpanded]);

    useEffect(() => {
        writeStoredRail(RIGHT_RAIL_STORAGE_KEY, rightRailExpanded);
    }, [rightRailExpanded]);

    return (
        <section className={styles.arena} data-testid="soccer-arena-view" aria-label="Soccer Arena">
            <header className={styles.header}>
                <button type="button" className={styles.backButton} onClick={onBack}>
                    <span aria-hidden="true">←</span> Back to {worldId ? `World ${worldId}` : 'tank'}
                </button>
                <div className={styles.titleBlock}>
                    <div className={styles.eyebrow}>Live competition venue</div>
                    <h1>Soccer Arena</h1>
                </div>
                <div className={styles.headerActions} aria-label="Arena view controls">
                    <span className={styles.viewLabel}>Broadcast</span>
                </div>
            </header>

            <div className={styles.arenaGrid}>
                <aside className={`${styles.rail} ${leftRailExpanded ? styles.railExpanded : styles.railCollapsed}`}>
                    <RailToggle
                        label="Lineup"
                        expanded={leftRailExpanded}
                        onClick={() => setLeftRailExpanded((expanded) => !expanded)}
                    />
                    {leftRailExpanded && (
                        <RailPlaceholder title="Lineup" detail="Roster details will appear here. The arena shell keeps the pitch as the primary surface." />
                    )}
                </aside>

                <main className={styles.stage}>
                    <div className={styles.pitchHeader}>
                        <div>
                            <div className={styles.eyebrow}>Arena preview</div>
                            <h2>{activeMatch ? 'Live match' : 'Waiting for scheduled match'}</h2>
                        </div>
                        <div className={styles.matchMeta}>
                            {activeMatch ? `${activeMatch.home_name || activeMatch.home_id || 'Home'} vs ${activeMatch.away_name || activeMatch.away_id || 'Away'}` : 'No active fixture'}
                        </div>
                    </div>

                    <div className={styles.pitchFrame}>
                        {activeMatch ? (
                            <SoccerPitch gameState={activeMatch} width={800} height={450} />
                        ) : (
                            <div className={styles.emptyPitch} role="status">
                                <span className={styles.emptyPitchIcon} aria-hidden="true">⚽</span>
                                <span>Waiting for scheduled match...</span>
                            </div>
                        )}
                    </div>

                    <div className={styles.drawer}>
                        <div>
                            <div className={styles.eyebrow}>Arena drawer</div>
                            <strong>{events.length ? `${events.length} match event${events.length === 1 ? '' : 's'} recorded` : 'Match history is ready when the arena is live'}</strong>
                        </div>
                        <span className={styles.drawerHint}>Open a rail for context</span>
                    </div>
                </main>

                <aside className={`${styles.rail} ${rightRailExpanded ? styles.railExpanded : styles.railCollapsed}`}>
                    <RailToggle
                        label="Progress"
                        expanded={rightRailExpanded}
                        onClick={() => setRightRailExpanded((expanded) => !expanded)}
                    />
                    {rightRailExpanded && (
                        <RailPlaceholder title="Progress" detail="Team skill and ladder progress will appear here in the next arena stage." />
                    )}
                </aside>
            </div>
        </section>
    );
}
