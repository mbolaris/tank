import { describe, expect, it, vi } from 'vitest';
import { PlayersLayer, avatarKindForEntity } from './PlayersLayer';
import type { SoccerRenderEntity } from './scene';

const player = (avatar_kind?: 'fish' | 'reference' | 'external' | 'bot'): SoccerRenderEntity => ({
    id: 1,
    type: 'player',
    x: 0,
    y: 0,
    fieldX: 0,
    fieldY: 0,
    radius: 10,
    vel_x: 0,
    vel_y: 0,
    fieldVelX: 0,
    fieldVelY: 0,
    speed: 0,
    participant: avatar_kind ? {
        participant_id: 'p1',
        side: 'left',
        team_id: 'left',
        uniform_number: 1,
        avatar_kind,
    } : undefined,
});

describe('avatarKindForEntity', () => {
    it.each(['fish', 'reference', 'external', 'bot'] as const)('keeps the %s participant branch', (kind) => {
        expect(avatarKindForEntity(player(kind))).toBe(kind);
    });

    it('defaults legacy player payloads to fish', () => {
        expect(avatarKindForEntity(player())).toBe('fish');
    });
});

function context(): CanvasRenderingContext2D {
    return {
        save: vi.fn(),
        restore: vi.fn(),
        translate: vi.fn(),
        rotate: vi.fn(),
        beginPath: vi.fn(),
        arc: vi.fn(),
        moveTo: vi.fn(),
        lineTo: vi.fn(),
        closePath: vi.fn(),
        roundRect: vi.fn(),
        fill: vi.fn(),
        stroke: vi.fn(),
        fillText: vi.fn(),
        setLineDash: vi.fn(),
    } as unknown as CanvasRenderingContext2D;
}

describe('PlayersLayer tactical cues', () => {
    const subject = (overrides: Partial<SoccerRenderEntity> = {}): SoccerRenderEntity => ({
        ...player('fish'),
        stamina: 0.5,
        ...overrides,
    });

    it('draws no role glyph or stamina arc in Broadcast', () => {
        const ctx = context();
        new PlayersLayer().draw(ctx, [subject()], false, { enabled: false, roles: { p1: 'M' } });
        expect(ctx.fillText).not.toHaveBeenCalledWith('M', expect.any(Number), expect.any(Number));
    });

    it('draws the handed-down role glyph in Tactical', () => {
        const ctx = context();
        new PlayersLayer().draw(ctx, [subject()], false, { enabled: true, roles: { p1: 'F' } });
        expect(ctx.fillText).toHaveBeenCalledWith('F', expect.any(Number), expect.any(Number));
    });

    it('never invents a role the caller did not supply', () => {
        const ctx = context();
        new PlayersLayer().draw(ctx, [subject()], false, { enabled: true, roles: {} });
        for (const call of vi.mocked(ctx.fillText).mock.calls) {
            expect(['D', 'M', 'F']).not.toContain(call[0]);
        }
    });

    it('omits the stamina arc entirely when the payload carries no stamina', () => {
        const withStamina = context();
        new PlayersLayer().draw(withStamina, [subject({ stamina: 0.5 })], false, { enabled: true });
        const withoutStamina = context();
        new PlayersLayer().draw(withoutStamina, [subject({ stamina: undefined })], false, { enabled: true });
        // A missing value must not read as a full bar, so the arc is skipped -
        // which is two fewer strokes than the drawn-and-empty case.
        expect(vi.mocked(withoutStamina.stroke).mock.calls.length).toBeLessThan(
            vi.mocked(withStamina.stroke).mock.calls.length,
        );
    });

    it('draws a dashed selection ring only for the selected participant', () => {
        const selected = context();
        new PlayersLayer().draw(selected, [subject()], false, { enabled: true, selectedParticipantId: 'p1' });
        expect(selected.setLineDash).toHaveBeenCalledWith([4, 4]);

        const other = context();
        new PlayersLayer().draw(other, [subject()], false, { enabled: true, selectedParticipantId: 'p2' });
        expect(other.setLineDash).not.toHaveBeenCalledWith([4, 4]);
    });
});
