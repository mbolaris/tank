import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { FormChips } from './FormChips';
import { ReferenceLadder } from './ReferenceLadder';
import { TopPerformers } from './TopPerformers';
import type { SkillLadder } from '../types/skill';

function ladder(beaten: boolean[]): SkillLadder {
    return {
        domain: 'soccer',
        benchmark_id: 'soccer/ladder_live',
        metric_name: 'goal_diff_per_match',
        skill_index: beaten.filter(Boolean).length * 25,
        rungs_beaten: beaten.filter(Boolean).length,
        total_rungs: beaten.length,
        rungs: beaten.map((isBeaten, index) => ({ rung: `L${index}`, rung_id: `rung-${index}`, metric: index, beaten: isBeaten })),
    };
}

describe('TeamProgressPanel', () => {
    it.each([[[], 'No frozen-ruler evaluation yet.'], [[false, true, false, false], 'Next: L0 (rung-0)'], [[true, true, true, true], 'all current rungs cleared']])(
        'renders ladder state for %j', (beaten, expected) => {
            const html = renderToString(<ReferenceLadder ladder={beaten.length ? ladder(beaten) : undefined} />);
            if (expected === 'Next: L0 (rung-0)') {
                expect(html).toContain('L0');
                expect(html).toContain('rung-0');
            } else {
                expect(html).toContain(expected);
            }
        },
    );

    it('keeps league form distinct from skill', () => {
        const html = renderToString(<FormChips form={['W', 'D', 'L']} />);
        expect(html).toContain('Recent league form');
        expect(html).toContain('formW');
        expect(html).toContain('formD');
        expect(html).toContain('formL');
    });

    it('renders match-record performers without presenting goals as skill', () => {
        const html = renderToString(<TopPerformers leaders={[{ fish_id: 284, matches: 4, wins: 3, draws: 0, losses: 1, goals: 7, assists: 3, net_energy: 12 }]} />);
        expect(html).toContain('Fish #');
        expect(html).toContain('284');
        expect(html).toContain('7');
        expect(html).toContain('3');
        expect(html).not.toContain('skill');
    });
});
