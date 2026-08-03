import { describe, expect, it } from 'vitest';
import { avatarKindForEntity } from './PlayersLayer';
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
