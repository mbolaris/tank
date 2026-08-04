import { describe, expect, it } from 'vitest';
import { isTankRoute, parseTankIdFromPath } from './routes';

describe('parseTankIdFromPath', () => {
    it('reads the tank id from a tank route', () => {
        expect(parseTankIdFromPath('/tank/abc')).toBe('abc');
        expect(parseTankIdFromPath('/tank/abc/')).toBe('abc');
    });

    it('reads the same tank id from the soccer arena route', () => {
        // The greedy regex used to yield 'abc/soccer' here, which then made
        // world navigation build /tank/abc/soccer as if it were a world id.
        expect(parseTankIdFromPath('/tank/abc/soccer')).toBe('abc');
        expect(parseTankIdFromPath('/tank/abc/soccer/')).toBe('abc');
    });

    it('handles uuid-shaped world ids', () => {
        const id = '6f1a3c2e-6b41-4f0d-9a2c-2d5f0f9b1c77';
        expect(parseTankIdFromPath(`/tank/${id}`)).toBe(id);
        expect(parseTankIdFromPath(`/tank/${id}/soccer`)).toBe(id);
    });

    it('decodes an encoded segment', () => {
        expect(parseTankIdFromPath('/tank/world%20one/soccer')).toBe('world one');
    });

    it('produces no tank id for unrelated routes', () => {
        expect(parseTankIdFromPath('/')).toBeUndefined();
        expect(parseTankIdFromPath('/network')).toBeUndefined();
        expect(parseTankIdFromPath('/tank')).toBeUndefined();
        expect(parseTankIdFromPath('/tank/')).toBeUndefined();
        expect(parseTankIdFromPath('/tanks/abc')).toBeUndefined();
        expect(parseTankIdFromPath('/other/tank/abc')).toBeUndefined();
    });
});

describe('isTankRoute', () => {
    it.each(['/', '/tank/abc', '/tank/abc/soccer'])('treats %s as a tank view', (path) => {
        expect(isTankRoute(path)).toBe(true);
    });

    it.each(['/network', '/tanks/abc'])('treats %s as not a tank view', (path) => {
        expect(isTankRoute(path)).toBe(false);
    });
});

describe('world navigation targets', () => {
    it('navigates to a plain tank route, never a malformed soccer id', () => {
        // TankNavigator builds `/tank/${world_id}` from the resolved id.
        const worldId = parseTankIdFromPath('/tank/abc/soccer');
        expect(`/tank/${worldId}`).toBe('/tank/abc');
        expect(parseTankIdFromPath(`/tank/${worldId}`)).toBe('abc');
    });
});
