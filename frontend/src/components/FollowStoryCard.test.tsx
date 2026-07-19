/**
 * Render tests for the compact Follow overlay (renderToString — no DOM in
 * the test env, matching the rest of this suite). The load-bearing contract
 * lives in useEntitySelection.test.ts (select_and_follow never opens the
 * inspector); this file only checks what actually reaches the page.
 */

import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { EntityData } from '../types/simulation';
import { FollowStoryCard } from './FollowStoryCard';

const fishEntity: EntityData = {
    id: 77,
    type: 'fish',
    x: 100,
    y: 100,
    width: 20,
    height: 12,
    energy: 54.6,
    generation: 3,
    common_name: 'Azure Needlefin',
};

const noop = () => undefined;

describe('FollowStoryCard', () => {
    it('renders the followed fish name, id, generation, and rounded energy', () => {
        const html = renderToString(<FollowStoryCard fish={fishEntity} onStop={noop} onInspect={noop} />);

        // renderToString inserts <!-- --> markers between adjacent JSX
        // expressions, so text spanning an expression boundary (id,
        // generation) is matched with a marker-tolerant regex instead of a
        // plain substring.
        expect(html).toContain('Following');
        expect(html).toContain('Azure Needlefin');
        expect(html).toMatch(/#(?:<!-- -->)?77/);
        expect(html).toMatch(/Generation\s*(?:<!-- -->)?3/);
        expect(html).toContain('55 energy');
    });

    it('falls back to a generic name and "Exploring" when data is sparse', () => {
        const sparse: EntityData = { id: 5, type: 'fish', x: 0, y: 0, width: 10, height: 10 };
        const html = renderToString(<FollowStoryCard fish={sparse} onStop={noop} onInspect={noop} />);

        expect(html).toContain('Tank fish');
        expect(html).toMatch(/Generation\s*(?:<!-- -->)?0/);
        expect(html).toContain('Exploring');
    });

    it('offers both Inspect and Stop following as separate actions', () => {
        const html = renderToString(<FollowStoryCard fish={fishEntity} onStop={noop} onInspect={noop} />);

        expect(html).toContain('Inspect');
        expect(html).toContain('Stop following');
    });
});
