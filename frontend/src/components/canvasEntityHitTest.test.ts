import { describe, expect, it } from 'vitest';

import type { EntityData } from '../types/simulation';
import { findEntityAtPoint } from './canvasEntityHitTest';

function entity(overrides: Partial<EntityData> & Pick<EntityData, 'id'>): EntityData {
    return { type: 'fish', x: 0, y: 0, width: 20, height: 20, ...overrides };
}

describe('findEntityAtPoint', () => {
    it('returns the entity whose box contains the point', () => {
        const fish = entity({ id: 1, x: 100, y: 100, width: 20, height: 20 });
        expect(findEntityAtPoint([fish], 100, 100, () => true)?.id).toBe(1);
    });

    it('returns undefined when the point is outside every box', () => {
        const fish = entity({ id: 1, x: 100, y: 100, width: 20, height: 20 });
        expect(findEntityAtPoint([fish], 500, 500, () => true)).toBeUndefined();
    });

    it('treats x/y as the box center, not the top-left corner', () => {
        const fish = entity({ id: 1, x: 100, y: 100, width: 20, height: 20 });
        // Just inside the top-left corner of the box: (90, 90).
        expect(findEntityAtPoint([fish], 91, 91, () => true)?.id).toBe(1);
        // Just outside it.
        expect(findEntityAtPoint([fish], 89, 89, () => true)).toBeUndefined();
    });

    it('prefers the last (topmost) entity when boxes overlap', () => {
        const back = entity({ id: 1, x: 100, y: 100, width: 40, height: 40 });
        const front = entity({ id: 2, x: 100, y: 100, width: 40, height: 40 });
        expect(findEntityAtPoint([back, front], 100, 100, () => true)?.id).toBe(2);
    });

    it('skips entities the predicate rejects, even if the point hits their box', () => {
        const rock = entity({ id: 1, type: 'decorative_rock', x: 100, y: 100, width: 40, height: 40 });
        expect(findEntityAtPoint([rock], 100, 100, (e) => e.type === 'fish')).toBeUndefined();
    });
});
