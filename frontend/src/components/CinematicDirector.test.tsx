/**
 * SSR-level checks for the Director's surface. Effects do not run under
 * `renderToString`, so this covers what must be true before any shot starts:
 * the toggle is always there and reports its state, and nothing narrates yet.
 */

import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { CinematicDirector } from './CinematicDirector';

function render(enabled: boolean) {
    return renderToString(
        <CinematicDirector
            enabled={enabled}
            onToggle={() => undefined}
            events={[]}
            entities={[]}
            selectedEntityId={null}
            onFollow={() => undefined}
            onRelease={() => undefined}
        />
    );
}

describe('CinematicDirector', () => {
    it('offers the toggle even with no events, so the feature is discoverable in a quiet tank', () => {
        expect(render(false)).toContain('Director');
    });

    it('reports its state to assistive technology rather than by colour alone', () => {
        expect(render(false)).toContain('aria-pressed="false"');
        expect(render(true)).toContain('aria-pressed="true"');
    });

    it('shows no caption until a shot actually starts', () => {
        expect(render(true)).not.toContain('role="status"');
    });
});
