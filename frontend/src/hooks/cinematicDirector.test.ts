/**
 * Shot-selection rules for the Cinematic Director.
 *
 * The cases that matter are the ones that would make an auto-camera obnoxious:
 * replaying a backlog the moment it is switched on, queueing stale moments
 * while the tank moves on, fighting the viewer for the camera, or dropping the
 * most dramatic events because they name no individual.
 */

import { describe, expect, it } from 'vitest';

import type { EntityData } from '../types/simulation';
import type { StoryEvent } from '../types/story';
import { findSubject, highestEventId, pickShot, viewerTookOver } from './cinematicDirector';

function event(id: number, overrides: Partial<StoryEvent> = {}): StoryEvent {
    return {
        id,
        schema_version: 1,
        event_type: 'generation_milestone',
        frame: id * 100,
        simulation_time: id,
        severity: 'info',
        title: `Event ${id}`,
        entity_ids: [],
        lineage_ids: [],
        metrics_before: {},
        metrics_after: {},
        detector_name: 'test',
        detector_threshold: {},
        replay_ref: null,
        ...overrides,
    };
}

function fish(id: number): EntityData {
    return { id, type: 'fish', x: 0, y: 0, width: 10, height: 10 } as unknown as EntityData;
}

describe('pickShot', () => {
    it('ignores everything at or below the cursor, so switching on does not replay history', () => {
        const backlog = [event(1), event(2), event(3)];
        expect(pickShot(backlog, [], highestEventId(backlog))).toBeNull();
    });

    it('takes the newest eligible event rather than working through a queue', () => {
        // Three landed while the previous shot was holding. The viewer should
        // see what the tank is doing now, not the oldest of the three.
        const shot = pickShot([event(7), event(9), event(8)], [], 6);
        expect(shot?.eventId).toBe(9);
    });

    it('is not fooled by newest-first or oldest-first ordering', () => {
        const ascending = pickShot([event(7), event(8), event(9)], [], 6);
        const descending = pickShot([event(9), event(8), event(7)], [], 6);
        expect(ascending?.eventId).toBe(9);
        expect(descending?.eventId).toBe(9);
    });

    it('carries the event\'s own words and severity into the shot', () => {
        const shot = pickShot(
            [event(4, { title: 'Generation 9 reached', severity: 'insight', event_type: 'generation_milestone' })],
            [],
            0
        );
        expect(shot?.title).toBe('Generation 9 reached');
        expect(shot?.severity).toBe('insight');
        expect(shot?.eventType).toBe('generation_milestone');
    });
});

describe('a shot with no filmable subject', () => {
    it('still runs for an event that names nobody', () => {
        // population_danger is the most dramatic thing the tank does and names
        // no individual. Dropping it would lose exactly the best moments.
        const shot = pickShot(
            [event(2, { event_type: 'population_danger', severity: 'concern', entity_ids: [] })],
            [fish(1)],
            0
        );
        expect(shot).not.toBeNull();
        expect(shot?.entityId).toBeNull();
    });

    it('degrades to caption-only when every named entity has already died', () => {
        const shot = pickShot([event(2, { entity_ids: [404, 405] })], [fish(1)], 0);
        expect(shot?.entityId).toBeNull();
        expect(shot?.title).toBe('Event 2');
    });

    it('follows the first named entity that is still alive', () => {
        const shot = pickShot([event(2, { entity_ids: [404, 7] })], [fish(1), fish(7)], 0);
        expect(shot?.entityId).toBe(7);
        expect(shot?.entityType).toBe('fish');
    });
});

describe('findSubject', () => {
    it('returns null rather than a dead entity', () => {
        expect(findSubject(event(1, { entity_ids: [9] }), [fish(1)])).toBeNull();
    });
});

describe('highestEventId', () => {
    it('is zero for an empty stream, so a fresh world is not treated as seen', () => {
        expect(highestEventId([])).toBe(0);
    });

    it('does not assume the stream is sorted', () => {
        expect(highestEventId([event(3), event(11), event(7)])).toBe(11);
    });
});

describe('viewerTookOver', () => {
    const shot = { eventId: 1, entityId: 42, entityType: 'fish', title: 't', eventType: 'lineage_dominant', severity: 'info' } as const;

    it('is false while the selection is still the one the director set', () => {
        expect(viewerTookOver(shot, 42)).toBe(false);
    });

    it('is true once the viewer selects something else', () => {
        expect(viewerTookOver(shot, 7)).toBe(true);
    });

    it('is true when the viewer clears the selection', () => {
        expect(viewerTookOver(shot, null)).toBe(true);
    });

    it('never interrupts a caption-only shot, which owns no selection', () => {
        const captionOnly = { ...shot, entityId: null, entityType: null };
        expect(viewerTookOver(captionOnly, null)).toBe(false);
        expect(viewerTookOver(captionOnly, 7)).toBe(false);
    });

    it('is false when there is no shot at all', () => {
        expect(viewerTookOver(null, 7)).toBe(false);
    });
});
