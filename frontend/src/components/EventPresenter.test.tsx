import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import type { SoccerMatchState } from '../types/simulation';
import { EventPresenter } from './EventPresenter';
import { SoccerEffectsLayer } from './SoccerEffectsLayer';

function match(events: SoccerMatchState['events'] = [], frame = 100): SoccerMatchState {
    return {
        match_id: 'broadcast-fixture',
        game_over: false,
        winner_team: null,
        message: 'Match in progress',
        frame,
        score: { left: 2, right: 0 },
        entities: [],
        home_name: 'World 1A',
        away_name: 'Reef Delta',
        participants: [
            { participant_id: 'left_1', side: 'left', team_id: 'world-1a', uniform_number: 9, avatar_kind: 'fish', fish_id: 284, generation: 41 },
        ],
        events,
    };
}

describe('EventPresenter', () => {
    it('renders goal content from a fixture event', () => {
        const html = renderToString(<EventPresenter match={match([{ frame: 100, seq: 1, kind: 'goal', side: 'left', actor: 'left_1', event_id: 'goal-1' }])} />);
        expect(html).toContain('soccer-goal-card');
        expect(html).toContain('World 1A');
        expect(html).toContain('leads');
        expect(html).toContain('Fish #284');
        expect(html).toContain('SIM 0:10');
    });

    it('renders halftime and full-time cards without changing scoreboard ownership', () => {
        const halftime = renderToString(<EventPresenter match={match([{ frame: 100, seq: 1, kind: 'half_time', event_id: 'half-1' }])} />);
        const fullTime = renderToString(<EventPresenter match={match([{ frame: 100, seq: 1, kind: 'full_time', event_id: 'full-1' }])} />);
        expect(halftime).toContain('soccer-half-time-card');
        expect(halftime).toContain('Teams switch attacking directions.');
        expect(fullTime).toContain('soccer-full-time-card');
        expect(fullTime).toContain('2 – 0');
    });

    it('keeps effect overlays separate from event cards', () => {
        const html = renderToString(<SoccerEffectsLayer event={{ frame: 100, seq: 1, kind: 'goal' }} />);
        expect(html).toContain('soccer-effects-layer');
        expect(html).toContain('effectsLayer');
    });
});
