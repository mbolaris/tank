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

    it('presents a completed match instead of letting it disappear', () => {
        const html = renderToString(
            <SoccerArenaView
                liveState={{
                    leaderboard: [],
                    availability: {},
                    active_match: null,
                    presentation_match: {
                        match_id: 'match-1',
                        game_over: true,
                        winner_team: 'left',
                        message: 'Left Team Wins! (2-1)',
                        frame: 600,
                        score: { left: 2, right: 1 },
                        entities: [],
                        play_mode: 'time_over',
                        home_name: 'World 1A',
                        away_name: 'Bot Balanced',
                        events: [{ frame: 600, seq: 4, kind: 'full_time', event_id: 'match-1-full_time-600-4' }],
                    },
                }}
                events={[]}
                worldId="world-1"
                onBack={() => undefined}
            />
        );

        expect(html).toContain('Full time');
        expect(html).toContain('FULL TIME');
        // Final score and both team names survive the hold.
        expect(html).toContain('World 1A');
        expect(html).toContain('Bot Balanced');
        // The pitch keeps rendering the final positions rather than emptying.
        expect(html).toContain('<canvas');
    });

    it('labels a held frame as stale rather than live while reconnecting', () => {
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
                        frame: 300,
                        score: { left: 1, right: 0 },
                        entities: [],
                    },
                }}
                events={[]}
                worldId="world-1"
                connectionState="disconnected"
                lastArrivalMs={0}
                onBack={() => undefined}
            />
        );

        expect(html).toContain('Connection interrupted');
        expect(html).toContain('DISCONNECTED');
        expect(html).toContain('Reconnecting');
        expect(html).not.toContain('Live match');
        // Nothing is cleared: the stale frame is still on the pitch.
        expect(html).toContain('<canvas');
    });

    it('surfaces an arena error instead of a normal live match', () => {
        const html = renderToString(
            <SoccerArenaView
                liveState={null}
                events={[]}
                worldId="world-1"
                connectionState="error"
                errorMessage="soccer payload failed schema validation"
                onBack={() => undefined}
            />
        );

        expect(html).toContain('Arena unavailable');
        expect(html).toContain('soccer payload failed schema validation');
        expect(html).not.toContain('Live match');
    });

    it('keeps the broadcast presenter on the pitch while the progress rail is collapsed', () => {
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
                        frame: 100,
                        score: { left: 1, right: 0 },
                        entities: [],
                        events: [{ frame: 98, seq: 1, kind: 'goal', side: 'left', event_id: 'match-1-goal-98-1' }],
                    },
                }}
                events={[]}
                worldId="world-1"
                onBack={() => undefined}
            />
        );

        // Rails default to collapsed. The presenter lives on the pitch, not in
        // the rail, so its lifetime cannot depend on the rail being expanded.
        expect(html).toContain('Expand Progress');
        expect(html).not.toContain('data-testid="soccer-team-progress"');
        expect(html).toContain('data-testid="soccer-event-presenter"');
        expect(html).toContain('soccer-goal-card');
    });
});
