import { describe, expect, it } from 'vitest';
import {
    dedupeEvents,
    eventKey,
    eventTier,
    presentEvents,
    type BroadcastEvent,
} from './soccerEvents';

function event(overrides: Partial<BroadcastEvent>): BroadcastEvent {
    return { frame: 100, seq: 0, kind: 'shot', ...overrides };
}

describe('soccer broadcast events', () => {
    it('classifies major, notable, and ambient events', () => {
        expect(eventTier('goal')).toBe('major');
        expect(eventTier('half_time')).toBe('notable');
        expect(eventTier('possession_change')).toBe('ambient');
    });

    it('deduplicates by stable event id and falls back to sequence identity', () => {
        const first = event({ event_id: 'match-goal-10-4', kind: 'goal', seq: 4 });
        expect(dedupeEvents([first, { ...first, actor: 'different' }])).toEqual([first]);
        expect(eventKey(event({ seq: 7, frame: 12, kind: 'save' }))).toContain('seq:7');
    });

    it('lets a major event preempt notable toasts', () => {
        const result = presentEvents([
            event({ frame: 88, seq: 1, kind: 'kickoff' }),
            event({ frame: 100, seq: 2, kind: 'goal', event_id: 'goal-100' }),
        ], 100);
        expect(result.major?.kind).toBe('goal');
        expect(result.notable).toEqual([]);
    });

    it('rate-limits notable events and reports collapsed overflow', () => {
        const result = presentEvents([
            event({ frame: 88, seq: 1, kind: 'shot' }),
            event({ frame: 90, seq: 2, kind: 'save' }),
            event({ frame: 100, seq: 3, kind: 'kickoff' }),
        ], 100);
        expect(result.notable).toHaveLength(2);
        expect(result.collapsedNotable).toBe(1);
    });

    it('does not present stale or future events', () => {
        const result = presentEvents([
            event({ frame: 10, seq: 1, kind: 'goal' }),
            event({ frame: 101, seq: 2, kind: 'shot' }),
        ], 100);
        expect(result.major).toBeNull();
        expect(result.notable).toEqual([]);
    });
});
