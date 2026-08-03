import { describe, expect, it } from 'vitest';
import { dedupeBreakthroughs } from './useBreakthroughs';

describe('useBreakthroughs', () => {
    it('deduplicates persisted records by event id and preserves frame order', () => {
        const records = dedupeBreakthroughs([
            { event_id: 'b-2', kind: 'team_skill_record', source_id: 'tank', frame: 20 },
            { event_id: 'b-1', kind: 'ladder_rung_cleared', source_id: 'tank', frame: 10 },
            { event_id: 'b-2', kind: 'team_skill_record', source_id: 'tank', frame: 20, detail: { skill_index: 80 } },
        ]);
        expect(records.map((record) => record.event_id)).toEqual(['b-1', 'b-2']);
    });
});
