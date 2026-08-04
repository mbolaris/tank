import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { calculatePitchViewport, resolvePitchMaxWidth } from './pitchViewport';
import { SoccerPitch } from './SoccerPitch';
import type { SoccerMatchState } from '../types/simulation';

const GEOMETRY = { length: 105, width: 68 };

function matchState(): SoccerMatchState {
    return {
        match_id: 'm-1',
        game_over: false,
        winner_team: null,
        message: '',
        frame: 10,
        score: { left: 0, right: 0 },
        entities: [],
        geometry: {
            length: 105,
            width: 68,
            goal_width: 14.02,
            goal_depth: 2.44,
        } as SoccerMatchState['geometry'],
    };
}

describe('calculatePitchViewport', () => {
    it('keeps the display aspect ratio from the active field profile', () => {
        const viewport = calculatePitchViewport(900, { length: 100, width: 60 }, 800, 1);
        expect(viewport).toEqual({ width: 800, height: 480, dpr: 1 });
    });

    it('matches the backing store to DPR without changing CSS dimensions', () => {
        const dprOne = calculatePitchViewport(600, GEOMETRY, 800, 1);
        const dprTwo = calculatePitchViewport(600, GEOMETRY, 800, 2);
        expect(dprTwo.width).toBe(dprOne.width);
        expect(dprTwo.height).toBe(dprOne.height);
        expect(dprTwo.dpr).toBe(2);
        expect(dprTwo.width * dprTwo.dpr).toBe(dprOne.width * 2);
        expect(dprTwo.height * dprTwo.dpr).toBe(dprOne.height * 2);
    });

    it.each([700, 1000, 1400])('fills a responsive arena host at %i CSS px', (hostWidth) => {
        // The arena passes no cap, so the cap resolves to the host width.
        const viewport = calculatePitchViewport(hostWidth, GEOMETRY, hostWidth, 2);

        expect(viewport.width).toBe(hostWidth);
        // Never the old 800x450 backing store scaled up.
        expect(viewport.width).not.toBe(800);
        expect(viewport.height).not.toBe(450);
        // Real field aspect preserved at every width.
        expect(viewport.width / viewport.height).toBeCloseTo(GEOMETRY.length / GEOMETRY.width, 6);
        // DPR-aware backing store.
        expect(viewport.width * viewport.dpr).toBe(hostWidth * 2);
    });

    it('still honours a legacy fixed cap on a wide host', () => {
        expect(calculatePitchViewport(1400, GEOMETRY, 800, 1).width).toBe(800);
    });
});

describe('resolvePitchMaxWidth', () => {
    it('leaves a pitch uncapped when neither a width nor a cap is given', () => {
        expect(resolvePitchMaxWidth(undefined, undefined)).toBeUndefined();
    });

    it('treats an explicit fixed width as a deliberate cap', () => {
        expect(resolvePitchMaxWidth(800, undefined)).toBe(800);
    });

    it('lets an explicit cap override a fixed width', () => {
        expect(resolvePitchMaxWidth(800, 1200)).toBe(1200);
    });
});

describe('SoccerPitch sizing', () => {
    it('renders the arena pitch with no max-width so it fills the stage', () => {
        const html = renderToString(<SoccerPitch gameState={matchState()} />);
        expect(html).toContain('data-testid="soccer-pitch-host"');
        expect(html).not.toContain('max-width');
        expect(html).toContain('aspect-ratio:105/68');
    });

    it('keeps a legacy fixed-size usage capped', () => {
        const html = renderToString(<SoccerPitch gameState={matchState()} width={800} height={450} />);
        expect(html).toContain('max-width:800px');
    });

    it('keeps a legacy panel cap when only maxWidth is given', () => {
        const html = renderToString(<SoccerPitch gameState={matchState()} maxWidth={800} />);
        expect(html).toContain('max-width:800px');
    });

    it('uses the real field aspect over any legacy width/height hint', () => {
        const html = renderToString(<SoccerPitch gameState={matchState()} width={800} height={450} />);
        expect(html).toContain('aspect-ratio:105/68');
        expect(html).not.toContain('aspect-ratio:800/450');
    });
});
