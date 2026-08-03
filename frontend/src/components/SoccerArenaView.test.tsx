import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { SoccerArenaView } from './SoccerArenaView';

describe('SoccerArenaView', () => {
    it('mounts a venue with a waiting state when there is no active match', () => {
        const html = renderToString(
            <SoccerArenaView liveState={null} events={[]} worldId="world-1" onBack={() => undefined} />
        );

        expect(html).toContain('data-testid="soccer-arena-view"');
        expect(html).toContain('Soccer Arena');
        expect(html).toContain('Waiting for scheduled match');
        expect(html).toContain('Expand Lineup');
        expect(html).toContain('Expand Progress');
    });

    it('keeps the existing pitch embedded when a match is active', () => {
        const html = renderToString(
            <SoccerArenaView
                liveState={{
                    leaderboard: [],
                    availability: {},
                    active_match: {
                        match_id: 'match-1',
                        game_over: false,
                        winner_team: null,
                        message: 'live',
                        frame: 30,
                        score: { left: 1, right: 0 },
                        entities: [],
                        home_id: 'left',
                        away_id: 'right',
                    },
                }}
                events={[]}
                onBack={() => undefined}
            />
        );

        expect(html).toContain('Live match');
        expect(html).toContain('<canvas');
    });
});
