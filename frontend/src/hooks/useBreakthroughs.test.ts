import { describe, expect, it } from 'vitest';
import type { SkillBreakthrough } from '../types/skill';
import { dedupeBreakthroughs, selectBreakthroughPresentation } from './useBreakthroughs';

function record(id: string, frame: number): SkillBreakthrough {
    return { event_id: id, kind: 'team_skill_record', source_id: 'tank', frame };
}

const NONE = new Set<string>();

describe('dedupeBreakthroughs', () => {
    it('deduplicates persisted records by event id and preserves frame order', () => {
        const records = dedupeBreakthroughs([
            { event_id: 'b-2', kind: 'team_skill_record', source_id: 'tank', frame: 20 },
            { event_id: 'b-1', kind: 'ladder_rung_cleared', source_id: 'tank', frame: 10 },
            { event_id: 'b-2', kind: 'team_skill_record', source_id: 'tank', frame: 20, detail: { skill_index: 80 } },
        ]);
        expect(records.map((r) => r.event_id)).toEqual(['b-1', 'b-2']);
    });
});

describe('selectBreakthroughPresentation', () => {
    it('presents one at a time and queues the rest deterministically', () => {
        const records = [record('b-3', 30), record('b-1', 10), record('b-2', 20)];
        const first = selectBreakthroughPresentation(records, NONE);
        expect(first.presenting?.event_id).toBe('b-1');
        expect(first.queued.map((r) => r.event_id)).toEqual(['b-2', 'b-3']);

        // The order does not depend on the arrival order of the records.
        const shuffled = selectBreakthroughPresentation([...records].reverse(), NONE);
        expect(shuffled.presenting?.event_id).toBe('b-1');
        expect(shuffled.queued.map((r) => r.event_id)).toEqual(['b-2', 'b-3']);
    });

    it('keeps presenting the same record across ordinary rerenders', () => {
        const records = [record('b-1', 10), record('b-2', 20)];
        // Merely re-deriving must not advance or drop the presentation.
        for (let i = 0; i < 5; i += 1) {
            expect(selectBreakthroughPresentation(records, NONE, { holding: 'b-1' }).presenting?.event_id).toBe('b-1');
        }
    });

    it('advances to the next record only after the current one is acknowledged', () => {
        const records = [record('b-1', 10), record('b-2', 20)];
        const acknowledged = new Set(['b-1']);
        const next = selectBreakthroughPresentation(records, acknowledged, { holding: null });
        expect(next.presenting?.event_id).toBe('b-2');
        expect(next.acknowledged.map((r) => r.event_id)).toEqual(['b-1']);
    });

    it('does not replay an acknowledged record', () => {
        const records = [record('b-1', 10)];
        const result = selectBreakthroughPresentation(records, new Set(['b-1']));
        expect(result.presenting).toBeNull();
        expect(result.queued).toHaveLength(0);
        // It survives as compact history for the Progress rail.
        expect(result.acknowledged.map((r) => r.event_id)).toEqual(['b-1']);
    });

    it('waits while a goal or full-time card owns the major slot', () => {
        const records = [record('b-1', 10)];
        const blocked = selectBreakthroughPresentation(records, NONE, { blocked: true });
        expect(blocked.presenting).toBeNull();
        expect(blocked.queued.map((r) => r.event_id)).toEqual(['b-1']);

        // It is not lost: it presents as soon as the slot frees up.
        expect(selectBreakthroughPresentation(records, NONE, { blocked: false }).presenting?.event_id).toBe('b-1');
    });

    it('lets a card already on screen finish even if the slot becomes blocked', () => {
        const records = [record('b-1', 10)];
        const held = selectBreakthroughPresentation(records, NONE, { blocked: true, holding: 'b-1' });
        expect(held.presenting?.event_id).toBe('b-1');
    });

    it('does not hold a record that has since been acknowledged', () => {
        const records = [record('b-1', 10), record('b-2', 20)];
        const result = selectBreakthroughPresentation(records, new Set(['b-1']), { holding: 'b-1' });
        expect(result.presenting?.event_id).toBe('b-2');
    });

    it('holds an earlier record already on screen against a late arrival', () => {
        const records = [record('b-0', 5), record('b-1', 10)];
        const result = selectBreakthroughPresentation(records, NONE, { holding: 'b-1' });
        expect(result.presenting?.event_id).toBe('b-1');
        expect(result.queued.map((r) => r.event_id)).toEqual(['b-0']);
    });

    it('presents nothing when there is nothing to present', () => {
        expect(selectBreakthroughPresentation([], NONE).presenting).toBeNull();
    });
});
