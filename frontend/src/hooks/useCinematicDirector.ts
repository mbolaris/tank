/**
 * The Cinematic Director - the effectful half. See `cinematicDirector.ts` for
 * the shot-selection rules this drives.
 *
 * Opt-in auto-camera: while enabled, new story events become short shots that
 * follow their subject and caption it, then hand the tank back. The decisions
 * live in pure functions; what is here is the clock, the cursor, and the
 * handoff to the ordinary entity selection.
 *
 * The one behaviour worth stating out loud: **the viewer always wins.** The
 * director follows by driving the same selection a click would, so any click,
 * follow toggle, or inspector action ends the current shot immediately
 * (`viewerTookOver`). It does not fight back, and it does not re-cut to the
 * thing the viewer just navigated away from, because that event is already
 * behind the cursor.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type { EntityData } from '../types/simulation';
import type { StoryEvent } from '../types/story';
import {
    SHOT_DURATION_MS,
    type DirectorShot,
    highestEventId,
    pickShot,
    viewerTookOver,
} from './cinematicDirector';

export interface UseCinematicDirectorOptions {
    enabled: boolean;
    events: readonly StoryEvent[];
    entities: readonly EntityData[];
    selectedEntityId: number | null;
    /** Drives the camera by selecting and following, exactly as a click does. */
    onFollow: (entityId: number, entityType: string) => void;
    /** Releases the camera at the end of a shot. */
    onRelease: () => void;
    /**
     * When true the director narrates without moving the camera: captions run,
     * shots are still consumed, but nothing is followed. A viewer who has asked
     * the system not to move things should not be handed an auto-panning
     * camera.
     */
    reducedMotion?: boolean;
}

export interface UseCinematicDirectorResult {
    /** The shot on screen now, or null between shots. */
    shot: DirectorShot | null;
}

export function useCinematicDirector({
    enabled,
    events,
    entities,
    selectedEntityId,
    onFollow,
    onRelease,
    reducedMotion = false,
}: UseCinematicDirectorOptions): UseCinematicDirectorResult {
    const [shot, setShot] = useState<DirectorShot | null>(null);

    /** Events at or below this are "already seen" and can never become shots. */
    const cursorRef = useRef(0);
    /** Latest inputs, so the shot timer does not have to re-arm when they change. */
    const eventsRef = useRef(events);
    const entitiesRef = useRef(entities);
    const onFollowRef = useRef(onFollow);
    const onReleaseRef = useRef(onRelease);
    const reducedMotionRef = useRef(reducedMotion);
    const shotRef = useRef<DirectorShot | null>(null);

    useEffect(() => {
        eventsRef.current = events;
        entitiesRef.current = entities;
        onFollowRef.current = onFollow;
        onReleaseRef.current = onRelease;
        reducedMotionRef.current = reducedMotion;
        shotRef.current = shot;
    }, [events, entities, onFollow, onRelease, reducedMotion, shot]);

    const endShot = useCallback(() => {
        const ending = shotRef.current;
        setShot(null);
        shotRef.current = null;
        if (ending && ending.entityId !== null && !reducedMotionRef.current) {
            onReleaseRef.current();
        }
    }, []);

    // Switching on adopts the current head of the stream as the cursor, so the
    // backfilled history does not replay. Switching off ends any live shot.
    useEffect(() => {
        if (enabled) {
            cursorRef.current = highestEventId(eventsRef.current);
        } else {
            endShot();
        }
    }, [enabled, endShot]);

    // Hand the camera back the moment the viewer steers it themselves.
    //
    // Deliberately drops the shot *without* calling `onRelease`: releasing
    // clears the selection, and the selection is now the viewer's. Ending a
    // shot this way must not undo the click that ended it.
    useEffect(() => {
        if (!enabled || shot === null) return;
        if (viewerTookOver(shot, selectedEntityId)) {
            setShot(null);
            shotRef.current = null;
        }
    }, [enabled, shot, selectedEntityId]);

    // Poll for the next shot. Story events arrive by polling anyway, so a timer
    // here costs nothing and keeps the start of a shot off the render path.
    useEffect(() => {
        if (!enabled || shot !== null) return;
        const timer = window.setInterval(() => {
            const next = pickShot(eventsRef.current, entitiesRef.current, cursorRef.current);
            if (next === null) return;
            cursorRef.current = next.eventId;
            setShot(next);
            shotRef.current = next;
            if (next.entityId !== null && next.entityType !== null && !reducedMotionRef.current) {
                onFollowRef.current(next.entityId, next.entityType);
            }
        }, 500);
        return () => window.clearInterval(timer);
    }, [enabled, shot]);

    // Hold the shot, then release.
    useEffect(() => {
        if (shot === null) return;
        const timer = window.setTimeout(endShot, SHOT_DURATION_MS);
        return () => window.clearTimeout(timer);
    }, [shot, endShot]);

    return { shot };
}
