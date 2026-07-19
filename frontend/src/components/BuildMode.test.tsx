/**
 * Render tests for the Build Mode object inspector (renderToString — no DOM
 * in the test env, matching the rest of this suite). These lock in that the
 * inspector reads the raw backend TankObject.object_id from render_hint, not
 * entity.id — entity.id carries a wire-only +5,000,000 offset
 * (core/worlds/shared/identity.py) that backend object commands don't
 * understand, so sending it as move_tank_object/delete_tank_object's
 * object_id silently fails to find the object.
 */

import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { EntityData } from '../types/simulation';
import { BuildMode } from './BuildMode';

const noop = () => undefined;

const castleWithRawId: EntityData = {
    id: 5000004,
    type: 'castle',
    x: 620,
    y: 446,
    width: 120,
    height: 120,
    render_hint: { style: 'tank_object', kind: 'castle', object_id: 4, rotation: 0 },
};

describe('BuildMode object inspector', () => {
    it('displays the raw object_id from render_hint, not the wire-offset entity id', () => {
        const html = renderToString(
            <BuildMode
                entities={[castleWithRawId]}
                onCommand={noop}
                onDelete={noop}
                selectedObjectId={5000004}
                selectedKind={null}
                onSelectKind={noop}
            />
        );

        expect(html).toMatch(/placed object #(?:<!-- -->)?4(?:<!-- -->)?</);
        expect(html).not.toContain('5000004');
        expect(html).toContain('Delete');
        expect(html).toContain('Keep here');
    });

    it('hides the Delete/Keep-here controls when render_hint carries no raw object_id', () => {
        const withoutRawId: EntityData = { ...castleWithRawId, render_hint: { style: 'tank_object', kind: 'castle' } };

        const html = renderToString(
            <BuildMode
                entities={[withoutRawId]}
                onCommand={noop}
                onDelete={noop}
                selectedObjectId={5000004}
                selectedKind={null}
                onSelectKind={noop}
            />
        );

        expect(html).not.toContain('Delete');
        expect(html).not.toContain('Keep here');
    });

    it('does not show the inspector when nothing is selected', () => {
        const html = renderToString(
            <BuildMode
                entities={[castleWithRawId]}
                onCommand={noop}
                onDelete={noop}
                selectedObjectId={null}
                selectedKind={null}
                onSelectKind={noop}
            />
        );

        expect(html).not.toContain('placed object #');
        expect(html).not.toContain('Delete');
    });
});
