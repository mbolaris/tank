/**
 * Shot selection for the Cinematic Director - the pure half.
 *
 * The director's job is to turn the story-event stream into a sequence of
 * shots: point the camera at whoever the world just did something to, caption
 * it, then give the tank back. Everything here is a pure function of the
 * events, the entities currently alive, and a cursor, so the interesting
 * decisions can be tested without a clock, a camera, or a DOM.
 *
 * Two rules shape the whole design.
 *
 * **The backlog is not the story.** `useStoryEvents` backfills up to 200 past
 * events, so a director that simply looked at "the newest event" would, the
 * instant you switched it on, cut to something that happened ten minutes ago.
 * Shots are therefore only ever drawn from events *newer than the cursor
 * captured when the director started*.
 *
 * **A moment without a subject is still a moment.** `population_danger` is the
 * most dramatic thing the tank does and it names no individual. Rather than
 * skip it, a shot may carry no `entityId`: the caption runs and the camera
 * stays where the viewer left it. Requiring a subject would drop exactly the
 * events most worth showing.
 */

import type { EntityData } from '../types/simulation';
import type { StoryEvent } from '../types/story';

/** How long one shot holds before the director releases the camera. */
export const SHOT_DURATION_MS = 9000;

export interface DirectorShot {
    /** The event this shot is presenting; also the cursor for the next pick. */
    eventId: number;
    /**
     * Who to follow, or null for a caption-only shot. Null means either the
     * event named nobody or everybody it named is already gone.
     */
    entityId: number | null;
    entityType: string | null;
    title: string;
    eventType: StoryEvent['event_type'];
    severity: StoryEvent['severity'];
}

/**
 * The subject of an event: its first named entity that is still alive.
 *
 * Events name entities that may have died between the detector firing and the
 * viewer seeing it - which is not an error, just the tank being the tank - so a
 * dead subject degrades the shot to caption-only instead of discarding it.
 */
export function findSubject(
    event: StoryEvent,
    entities: readonly EntityData[]
): EntityData | null {
    for (const entityId of event.entity_ids) {
        const entity = entities.find((candidate) => candidate.id === entityId);
        if (entity) return entity;
    }
    return null;
}

/**
 * The next shot to run, or null if there is nothing new worth cutting to.
 *
 * Picks the *newest* eligible event rather than the oldest: when several land
 * between shots, the viewer should see what the tank is doing now, not work
 * through a queue. The skipped ones are gone, which is the right trade for a
 * surface whose whole job is to be glanceable.
 */
export function pickShot(
    events: readonly StoryEvent[],
    entities: readonly EntityData[],
    cursor: number
): DirectorShot | null {
    let best: StoryEvent | null = null;
    for (const event of events) {
        if (event.id <= cursor) continue;
        if (best === null || event.id > best.id) best = event;
    }
    if (best === null) return null;

    const subject = findSubject(best, entities);
    return {
        eventId: best.id,
        entityId: subject ? subject.id : null,
        entityType: subject ? subject.type : null,
        title: best.title,
        eventType: best.event_type,
        severity: best.severity,
    };
}

/**
 * The highest event id present, which becomes the starting cursor.
 *
 * Taken when the director is switched on so that everything already on screen
 * counts as seen.
 */
export function highestEventId(events: readonly StoryEvent[]): number {
    let highest = 0;
    for (const event of events) {
        if (event.id > highest) highest = event.id;
    }
    return highest;
}

/**
 * Whether the viewer has taken the camera back from the director.
 *
 * The director follows by driving the ordinary selection, so "the user took
 * over" is just "the selection is no longer the one I set". That keeps the
 * override implicit and total: any click, any follow toggle, any inspector
 * action ends the shot, with nothing to wire up per interaction.
 *
 * A caption-only shot owns no selection and so can never be interrupted this
 * way - it holds for its duration whatever the viewer clicks.
 */
export function viewerTookOver(
    shot: DirectorShot | null,
    selectedEntityId: number | null
): boolean {
    if (shot === null || shot.entityId === null) return false;
    return selectedEntityId !== shot.entityId;
}
