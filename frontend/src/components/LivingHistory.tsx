/**
 * LivingHistory - the world's memory, as one surface (E4 + E5).
 *
 * Composes the "since your last visit" recap above the event timeline. They
 * are two views of the same story-event stream and share one fetch, so they
 * are assembled here rather than wired separately into TankView.
 *
 * This component owns the *visit* state - the viewer's stored baseline and the
 * arrival ceiling - keeping both out of the timeline, which only ever renders
 * the events it is handed.
 *
 * The legends roster joins it here (U8b): legends are the same history at a
 * longer timescale - what the tank remembers rather than what just happened.
 */

import { useEffect, useRef } from 'react';
import type { StoryEvent } from '../types/story';
import { useFrozenCeiling, useLastSeenStoryEvent } from '../hooks/useLastSeenStoryEvent';
import { useLegends } from '../hooks/useLegends';
import { LegendsRoster } from './LegendsRoster';
import { StoryRecap } from './StoryRecap';
import { StoryTimeline } from './StoryTimeline';

interface LivingHistoryProps {
    worldId: string | undefined;
    events: StoryEvent[];
    currentFrame: number;
    liveEntityIds?: ReadonlySet<number>;
    onInspectEntity?: (entityId: number) => void;
}

export function LivingHistory({
    worldId,
    events,
    currentFrame,
    liveEntityIds,
    onInspectEntity,
}: LivingHistoryProps) {
    const { baselineId, ready, markSeen } = useLastSeenStoryEvent(worldId);
    const { legends } = useLegends(worldId);
    const ceilingId = useFrozenCeiling(events, ready);

    // A first visit (or cleared storage) shows no recap - the viewer has not
    // been away from anything yet - but it must still seed a baseline, or they
    // would never get a recap on any future visit either.
    useEffect(() => {
        if (ready && baselineId === null && ceilingId !== null) {
            markSeen(ceilingId);
        }
    }, [ready, baselineId, ceilingId, markSeen]);

    // Leaving marks what was on screen as seen. Without this the recap fires on
    // any reload the moment two more events land, which is not "since your
    // last visit" - the viewer never left. A visit ends when the page is
    // hidden or the world is switched, and that is what the baseline records.
    const latestIdRef = useRef(0);
    useEffect(() => {
        latestIdRef.current = events.reduce((max, e) => Math.max(max, e.id), latestIdRef.current);
    }, [events]);

    useEffect(() => {
        // A new world is a new id space; do not carry a high-water mark across.
        latestIdRef.current = 0;
        const markLatestSeen = () => {
            if (latestIdRef.current > 0) markSeen(latestIdRef.current);
        };
        // `pagehide` rather than `unload`: it is the one that still fires when
        // a mobile browser backgrounds the tab.
        window.addEventListener('pagehide', markLatestSeen);
        return () => {
            window.removeEventListener('pagehide', markLatestSeen);
            markLatestSeen();
        };
    }, [markSeen]);

    return (
        <>
            {ready && (
                <StoryRecap
                    events={events}
                    baselineId={baselineId}
                    ceilingId={ceilingId}
                    onDismiss={markSeen}
                    liveEntityIds={liveEntityIds}
                    onInspectEntity={onInspectEntity}
                />
            )}
            <StoryTimeline
                events={events}
                currentFrame={currentFrame}
                liveEntityIds={liveEntityIds}
                onInspectEntity={onInspectEntity}
            />
            <LegendsRoster
                legends={legends}
                liveEntityIds={liveEntityIds}
                onInspectEntity={onInspectEntity}
            />
        </>
    );
}
