import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { SkillLadderList } from './SkillLadderPanel';
import type { SkillLadder } from '../types/skill';

function pokerLadder(overrides: Partial<SkillLadder> = {}): SkillLadder {
    return {
        domain: 'poker',
        benchmark_id: 'poker/ladder_20k',
        metric_name: 'bb_per_100',
        skill_index: 100,
        rungs_beaten: 4,
        total_rungs: 4,
        rungs: [
            { rung: 'L0', rung_id: 'random', metric: 1063.2, beaten: true },
            { rung: 'L3', rung_id: 'gto_expert', metric: 588.7, beaten: true },
        ],
        notes: 'ceiling saturated',
        ...overrides,
    };
}

describe('SkillLadderList', () => {
    it('renders each domain and its rungs', () => {
        const html = renderToString(<SkillLadderList ladders={[pokerLadder()]} />);
        expect(html).toContain('poker');
        expect(html).toContain('poker/ladder_20k');
        expect(html).toContain('gto_expert');
        expect(html).toContain('4/4 rungs');
        expect(html).toContain('100');
    });

    it('marks unbeaten rungs distinctly', () => {
        const html = renderToString(
            <SkillLadderList
                ladders={[
                    pokerLadder({
                        skill_index: 50,
                        rungs_beaten: 1,
                        total_rungs: 2,
                        rungs: [
                            { rung: 'L0', rung_id: 'random', metric: 500, beaten: true },
                            { rung: 'L1', rung_id: 'tag', metric: -20, beaten: false },
                        ],
                    }),
                ]}
            />,
        );
        expect(html).toContain('beaten');
        expect(html).toContain('not yet');
    });

    it('shows an empty-state message when there are no ladders', () => {
        const html = renderToString(<SkillLadderList ladders={[]} />);
        expect(html).toContain('No skill ladders recorded yet');
    });
});
