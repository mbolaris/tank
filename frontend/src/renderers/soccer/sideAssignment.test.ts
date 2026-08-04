import { describe, expect, it } from 'vitest';
import { resolveSideAssignment, sidesAreSwapped } from './sideAssignment';

const teams = { home_name: 'World A · A Team', away_name: 'Bot Balanced', home_id: 'A:A', away_id: 'Bot:Balanced' };

describe('resolveSideAssignment', () => {
    it('puts home on the left attacking right in the first half', () => {
        const sides = resolveSideAssignment({ ...teams, half: 1, sides_swapped: false });
        expect(sides.leftTeam).toBe('home');
        expect(sides.rightTeam).toBe('away');
        expect(sides.leftLabel).toBe('World A · A Team');
        expect(sides.rightLabel).toBe('Bot Balanced');
        expect(sides.leftAttackDirection).toBe(1);
        expect(sides.rightAttackDirection).toBe(-1);
    });

    it('puts away on the left attacking right in the second half', () => {
        const sides = resolveSideAssignment({ ...teams, half: 2, sides_swapped: true });
        expect(sides.leftTeam).toBe('away');
        expect(sides.rightTeam).toBe('home');
        expect(sides.leftLabel).toBe('Bot Balanced');
        expect(sides.rightLabel).toBe('World A · A Team');
        // Arrows belong to the side, not the team: left always attacks right.
        expect(sides.leftAttackDirection).toBe(1);
        expect(sides.rightAttackDirection).toBe(-1);
    });

    it('keeps each name attached to its team identity across the swap', () => {
        const first = resolveSideAssignment({ ...teams, sides_swapped: false });
        const second = resolveSideAssignment({ ...teams, sides_swapped: true });
        expect(first.leftLabel).toBe(second.rightLabel);
        expect(first.rightLabel).toBe(second.leftLabel);
    });

    it('defaults conservatively to the first half when the half is unknown', () => {
        expect(sidesAreSwapped(undefined)).toBe(false);
        expect(sidesAreSwapped(null)).toBe(false);
        expect(sidesAreSwapped({})).toBe(false);
        expect(resolveSideAssignment({}).leftTeam).toBe('home');
        expect(resolveSideAssignment({ ...teams }).leftLabel).toBe('World A · A Team');
    });

    it('prefers the engine side-swap flag over the derived half', () => {
        // A payload that disagrees resolves to the engine's own flag.
        expect(sidesAreSwapped({ half: 2, sides_swapped: false })).toBe(false);
        expect(sidesAreSwapped({ half: 1, sides_swapped: true })).toBe(true);
        // Legacy payloads without the flag still fall back to the half.
        expect(sidesAreSwapped({ half: 2 })).toBe(true);
    });

    it('falls back to team ids and then to generic labels', () => {
        expect(resolveSideAssignment({ home_id: 'A:A', away_id: 'B:A' }).leftLabel).toBe('A:A');
        expect(resolveSideAssignment({}).leftLabel).toBe('HOME');
        expect(resolveSideAssignment({}).rightLabel).toBe('AWAY');
    });
});
