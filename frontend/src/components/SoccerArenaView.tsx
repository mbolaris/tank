import { useCallback, useEffect, useMemo, useState } from 'react';
import type { SoccerEventData, SoccerLeagueLiveState } from '../types/simulation';
import { AnalysisPanel } from './AnalysisPanel';
import { ArenaViewModeControl } from './ArenaViewModeControl';
import { FormationPanel } from './FormationPanel';
import { LineupPanel } from './LineupPanel';
import { MatchTimeline } from './MatchTimeline';
import { PitchCanvas } from './PitchCanvas';
import { PlayerCard } from './PlayerCard';
import { Scoreboard } from './Scoreboard';
import { SoccerProgressStrip } from './SoccerProgressStrip';
import { EventPresenter } from './EventPresenter';
import { SoccerEffectsLayer } from './SoccerEffectsLayer';
import { TeamProgressPanel } from './TeamProgressPanel';
import { activeEffectEvent, hasMajorMatchEvent, type SoccerBroadcastMatch } from './soccerEvents';
import { deriveArenaState, type ArenaConnectionState, type ArenaPresentation } from './soccerArenaState';
import { isAnalyticalMode, readStoredViewMode, viewModeForHotkey, writeStoredViewMode, type ArenaViewMode } from './soccerViewMode';
import styles from './SoccerArenaView.module.css';

import { useFormationMetrics } from '../hooks/useFormationMetrics';
import { useSkillSnapshots } from '../hooks/useSkillSnapshots';
import { useBreakthroughs } from '../hooks/useBreakthroughs';
import { usePrefersReducedMotion } from '../hooks/usePrefersReducedMotion';
import { useStaleClock } from '../hooks/useStaleClock';

interface SoccerArenaViewProps {
    liveState: SoccerLeagueLiveState | null;
    events: SoccerEventData[];
    worldId?: string;
    onBack: () => void;
    connectionState?: ArenaConnectionState;
    errorMessage?: string | null;
    lastArrivalMs?: number;
    onRetry?: () => void;
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

function presentationTitle(presentation: ArenaPresentation): string {
    const titles: Record<ArenaPresentation, string> = {
        empty: 'Waiting for scheduled match',
        loading: 'Warming up',
        live: 'Live match',
        paused: 'Match paused',
        halftime: 'Halftime',
        finished: 'Full time',
        disconnected: 'Connection interrupted',
        skipped: 'Match skipped',
        error: 'Arena unavailable',
    };
    return titles[presentation];
}

function PitchStateOverlay({ presentation, staleLabel }: { presentation: ArenaPresentation; staleLabel?: string }) {
    if (presentation === 'live' || presentation === 'empty' || presentation === 'loading' || presentation === 'finished') return null;
    const copy: Record<Exclude<ArenaPresentation, 'live' | 'empty' | 'loading' | 'finished'>, string> = {
        paused: '❚❚ PAUSED',
        halftime: 'HALF TIME',
        disconnected: staleLabel ?? 'DISCONNECTED · LAST FRAME HELD',
        skipped: 'MATCH SKIPPED',
        error: 'ARENA ERROR',
    };
    const className = `pitchState${presentation[0].toUpperCase()}${presentation.slice(1)}` as keyof typeof styles;
    return <div className={`${styles.pitchStateOverlay} ${styles[className]}`} role="status">{copy[presentation]}</div>;
}

export function SoccerArenaView({ liveState, events, worldId, onBack, connectionState, errorMessage, lastArrivalMs, onRetry }: SoccerArenaViewProps) {
    const [leftRailExpanded, setLeftRailExpanded] = useState(() => readStoredRail(LEFT_RAIL_STORAGE_KEY));
    const [rightRailExpanded, setRightRailExpanded] = useState(() => readStoredRail(RIGHT_RAIL_STORAGE_KEY));
    const [viewMode, setViewMode] = useState<ArenaViewMode>(() => readStoredViewMode());
    const [selectedParticipantId, setSelectedParticipantId] = useState<string | null>(null);
    const [previousPresentation, setPreviousPresentation] = useState<ArenaPresentation>('live');
    const reducedMotion = usePrefersReducedMotion();
    const { data: skillData } = useSkillSnapshots(worldId);
    const analysisMode = viewMode === 'analysis';
    // Tactical and Analysis share the annotated pitch and the zero-occlusion
    // budget (§3.1); they differ in what the right rail carries.
    const annotatedMode = isAnalyticalMode(viewMode);

    // The stale age only ticks while disconnected, so a healthy feed does not
    // re-render once a second for nothing.
    const isStale = connectionState === 'disconnected';
    const staleNowMs = useStaleClock(isStale);
    const arenaState = deriveArenaState({
        liveState,
        connectionState,
        errorMessage,
        previousPresentation,
        lastArrivalMs,
        nowMs: staleNowMs,
    });
    const activeMatch = arenaState.match;
    const broadcastMatch = activeMatch as SoccerBroadcastMatch | null;

    // A goal or full-time card owns the major slot first; the breakthrough
    // queues behind it rather than overlapping. Rail state is irrelevant here -
    // the broadcast card lives on the pitch, not in the Progress rail.
    const { presenting: presentedBreakthrough } = useBreakthroughs(
        skillData?.breakthroughs ?? [],
        worldId,
        { blocked: hasMajorMatchEvent(activeMatch) },
    );

    const metrics = useFormationMetrics(activeMatch, annotatedMode);
    const selectedParticipant =
        activeMatch?.participants?.find((participant) => participant.participant_id === selectedParticipantId) ?? null;
    // A selected player who leaves the pitch (substitution, a new match) must
    // not keep a dashed ring on a participant that is no longer there.
    useEffect(() => {
        if (selectedParticipantId && !selectedParticipant) setSelectedParticipantId(null);
    }, [selectedParticipantId, selectedParticipant]);

    const tactical = useMemo(
        () => ({ enabled: annotatedMode, roles: metrics.roles, selectedParticipantId }),
        [annotatedMode, metrics.roles, selectedParticipantId],
    );

    const changeViewMode = useCallback((next: ArenaViewMode) => {
        setViewMode(next);
        writeStoredViewMode(next);
    }, []);

    useEffect(() => {
        if (!arenaState.unknownStage) {
            setPreviousPresentation((current) => current === arenaState.presentation ? current : arenaState.presentation);
        }
    }, [arenaState.presentation, arenaState.unknownStage]);
    useEffect(() => writeStoredRail(LEFT_RAIL_STORAGE_KEY, leftRailExpanded), [leftRailExpanded]);
    useEffect(() => writeStoredRail(RIGHT_RAIL_STORAGE_KEY, rightRailExpanded), [rightRailExpanded]);

    // §7 keyboard: B/T switch modes, Escape deselects. Typing in a field must
    // never be swallowed, so the handler stands down while an editable element
    // or any other widget with its own key handling has focus.
    useEffect(() => {
        const onKeyDown = (event: KeyboardEvent) => {
            const target = event.target as HTMLElement | null;
            if (target?.isContentEditable) return;
            const tag = target?.tagName;
            if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
            if (event.key === 'Escape') {
                setSelectedParticipantId((current) => (current === null ? current : null));
                return;
            }
            const nextMode = viewModeForHotkey(event);
            if (nextMode) changeViewMode(nextMode);
        };
        window.addEventListener('keydown', onKeyDown);
        return () => window.removeEventListener('keydown', onKeyDown);
    }, [changeViewMode]);

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
                    <ArenaViewModeControl mode={viewMode} onChange={changeViewMode} />
                </div>
            </header>

            <div className={styles.arenaGrid} data-view-mode={viewMode}>
                <aside className={`${styles.rail} ${leftRailExpanded ? styles.railExpanded : styles.railCollapsed}`}>
                    <RailToggle label="Lineup" expanded={leftRailExpanded} onClick={() => setLeftRailExpanded((expanded) => !expanded)} />
                    {leftRailExpanded && (
                        <div className={styles.railScroll}>
                            <LineupPanel
                                match={activeMatch}
                                roles={metrics.roles}
                                selectedParticipantId={selectedParticipantId}
                                onSelect={setSelectedParticipantId}
                            />
                            {selectedParticipant && (
                                <div className={styles.railCardSlot}>
                                    <PlayerCard
                                        participant={selectedParticipant}
                                        role={metrics.roles[selectedParticipant.participant_id]}
                                        meanX={metrics.summaries.find((summary) => summary.participantId === selectedParticipant.participant_id)?.meanX}
                                    />
                                </div>
                            )}
                        </div>
                    )}
                </aside>

                <main className={styles.stage}>
                    <Scoreboard
                        match={activeMatch}
                        presentation={arenaState.presentation}
                        unknownStage={arenaState.unknownStage}
                        skippedReason={arenaState.skippedReason}
                        errorMessage={arenaState.errorMessage}
                        compact={annotatedMode}
                    />
                    <div className={styles.pitchHeader}>
                        <div>
                            <div className={styles.eyebrow}>Arena preview</div>
                            <h2>{presentationTitle(arenaState.presentation)}</h2>
                        </div>
                        <div className={styles.matchMeta}>
                            {activeMatch ? `${activeMatch.home_name || activeMatch.home_id || 'Home'} vs ${activeMatch.away_name || activeMatch.away_id || 'Away'}` : 'No active fixture'}
                        </div>
                    </div>

                    <div className={styles.pitchFrame} data-state={arenaState.presentation}>
                        {activeMatch ? (
                            <PitchCanvas gameState={activeMatch} tactical={tactical} />
                        ) : (
                            <div className={styles.emptyPitch} role="status">
                                <span className={styles.emptyPitchIcon} aria-hidden="true">⚽</span>
                                <span>{arenaState.skippedReason || arenaState.errorMessage || presentationTitle(arenaState.presentation)}</span>
                                {arenaState.presentation === 'error' && onRetry && <button type="button" onClick={onRetry}>Retry</button>}
                            </div>
                        )}
                        {/*
                          * §3.1: Tactical permits no field-covering overlays at
                          * all, so the effects layer and the event cards are not
                          * mounted - the same events route to the timeline below.
                          */}
                        {!annotatedMode && (
                            <>
                                <SoccerEffectsLayer event={activeEffectEvent(broadcastMatch)} reducedMotion={reducedMotion} />
                                <EventPresenter match={activeMatch} breakthrough={presentedBreakthrough} reducedMotion={reducedMotion} />
                            </>
                        )}
                        <PitchStateOverlay presentation={arenaState.presentation} staleLabel={arenaState.staleLabel} />
                    </div>

                    <SoccerProgressStrip liveState={liveState} match={activeMatch} presentation={arenaState.presentation} />

                    {annotatedMode ? (
                        <div className={styles.drawerPanel}>
                            <MatchTimeline match={activeMatch} />
                        </div>
                    ) : (
                        <div className={styles.drawer}>
                            <div>
                                <div className={styles.eyebrow}>Arena drawer</div>
                                <strong>{events.length ? `${events.length} match event${events.length === 1 ? '' : 's'} recorded` : 'Match history is ready when the arena is live'}</strong>
                            </div>
                            <span className={styles.drawerHint}>Open a rail for context</span>
                        </div>
                    )}
                </main>

                {/*
                  * §4.2: Analysis turns the right column into a full metrics
                  * stack, so the rail is always open and wider there. The pitch
                  * is the flex child and gives up the width, which is the same
                  * sanctioned rail-driven re-fit as §3.1 - not a mode-driven
                  * one, so the §7 "pitch never jumps on a mode switch"
                  * invariant still holds for equal rail state.
                  */}
                <aside
                    className={`${styles.rail} ${analysisMode ? styles.railAnalysis : rightRailExpanded ? styles.railExpanded : styles.railCollapsed}`}
                >
                    {!analysisMode && (
                        <RailToggle
                            label={annotatedMode ? 'Formation' : 'Progress'}
                            expanded={rightRailExpanded}
                            onClick={() => setRightRailExpanded((expanded) => !expanded)}
                        />
                    )}
                    {(rightRailExpanded || analysisMode) && (
                        <div className={styles.railScroll}>
                            {analysisMode
                                ? <AnalysisPanel match={activeMatch} metrics={metrics} />
                                : annotatedMode
                                    ? <FormationPanel match={activeMatch} metrics={metrics} />
                                    : <TeamProgressPanel worldId={worldId} liveState={liveState} />}
                        </div>
                    )}
                </aside>
            </div>
        </section>
    );
}
