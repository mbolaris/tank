import { describe, expect, it } from 'vitest';
import type { EntityData } from '../types/simulation';
import { EntityPositionInterpolator } from './entityPositionInterpolator';

function fish(id: number, x: number, y: number, velX = 0, velY = 0): EntityData {
    return {
        id,
        type: 'fish',
        x,
        y,
        width: 20,
        height: 10,
        vel_x: velX,
        vel_y: velY,
    };
}

describe('EntityPositionInterpolator', () => {
    it('continues movement from velocity between server snapshots without mutating source entities', () => {
        const interpolator = new EntityPositionInterpolator();
        const snapshot = [fish(1, 10, 20, 2, -1)];

        expect(interpolator.interpolate(snapshot, 0)[0]).toBe(snapshot[0]);
        const predicted = interpolator.interpolate(snapshot, 50)[0];
        expect(predicted.x).toBe(13);
        expect(predicted.y).toBe(18.5);
        expect(snapshot[0].x).toBe(10);
        expect(snapshot[0].y).toBe(20);
    });

    it('blends small snapshot corrections without jumping', () => {
        const interpolator = new EntityPositionInterpolator();
        const first = [fish(1, 0, 0, 1, 0)];
        const corrected = [fish(1, 1, 0, 1, 0)];

        interpolator.interpolate(first, 0);
        expect(interpolator.interpolate(first, 50)[0].x).toBe(1.5);

        expect(interpolator.interpolate(corrected, 50)[0].x).toBe(1.5);
        expect(interpolator.interpolate(corrected, 100)[0].x).toBeCloseTo(2.75);
    });

    it('snaps new entities and teleports immediately before resuming movement', () => {
        const interpolator = new EntityPositionInterpolator();
        const first = [fish(1, 0, 0, 1, 0)];
        const teleported = [fish(1, 200, 0, 1, 0), fish(2, 20, 20)];

        interpolator.interpolate(first, 0);
        const rendered = interpolator.interpolate(teleported, 60);

        expect(rendered).toBe(teleported);
        expect(interpolator.interpolate(teleported, 110)[0].x).toBe(201.5);
    });

    it('drops tracks for removed entities', () => {
        const interpolator = new EntityPositionInterpolator();
        interpolator.interpolate([fish(1, 0, 0), fish(2, 10, 0)], 0);
        interpolator.interpolate([fish(1, 10, 0)], 60);

        const readded = [fish(1, 20, 0), fish(2, 100, 0)];
        const rendered = interpolator.interpolate(readded, 120);

        expect(rendered[1]).toBe(readded[1]);
    });
});
