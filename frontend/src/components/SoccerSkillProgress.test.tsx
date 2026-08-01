import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { SoccerSkillProgress } from './SoccerSkillProgress';
import { getRungHumanName } from '../utils/rungMapping';


describe('getRungHumanName', () => {
    it('maps standard rung IDs to human-readable names', () => {
        expect(getRungHumanName('stationary_v1')).toBe('Stationary');
        expect(getRungHumanName('random_walk_v1')).toBe('Random Walk');
        expect(getRungHumanName('chase_shoot_v1')).toBe('Chase-and-Shoot');
        expect(getRungHumanName('formation_v1')).toBe('Formation');
    });

    it('falls back to provided name or raw rung ID', () => {
        expect(getRungHumanName('custom_v1', 'Custom Rung')).toBe('Custom Rung');
        expect(getRungHumanName('unknown_v1')).toBe('unknown_v1');
    });
});

describe('SoccerSkillProgress', () => {
    it('renders empty state initially when awaiting evaluation', () => {
        const html = renderToString(<SoccerSkillProgress worldId="default" />);

        expect(html).toContain('Soccer Progress');
        expect(html).toContain('Awaiting first ladder evaluation');
    });
});
