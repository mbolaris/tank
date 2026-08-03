import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { MatchClock } from './MatchClock';
import { Scoreboard } from './Scoreboard';
import type { ArenaPresentation } from './soccerArenaState';

describe('Scoreboard', () => {
    it.each(['empty', 'loading', 'live', 'paused', 'halftime', 'finished', 'disconnected', 'skipped', 'error'] as ArenaPresentation[])(
        'keeps fixed team and center slots in the %s state',
        (presentation) => {
            const html = renderToString(<Scoreboard match={null} presentation={presentation} />);
            const status = {
                empty: 'IDLE', loading: 'WARMING UP', live: 'LIVE', paused: 'PAUSED', halftime: 'HALF TIME',
                finished: 'FULL TIME', disconnected: 'DISCONNECTED', skipped: 'MATCH SKIPPED', error: 'ARENA ERROR',
            }[presentation];
            expect(html).toContain('data-testid="soccer-scoreboard"');
            expect(html).toContain('data-testid="team-block-left"');
            expect(html).toContain('data-testid="team-block-right"');
            expect(html).toContain(status);
        },
    );

    it('shows unknown mode text in the stage slot without changing the score layout', () => {
        const html = renderToString(<Scoreboard match={null} presentation="paused" unknownStage="UNKNOWN: future_mode" />);
        expect(html).toContain('UNKNOWN: future_mode');
        expect(html).toContain('PAUSED');
    });

    it('labels the simulation clock and does not invent a wall-clock value', () => {
        expect(renderToString(<MatchClock frame={724} />)).toContain('SIM 1:12');
        expect(renderToString(<MatchClock />)).toContain('--:--');
    });
});
