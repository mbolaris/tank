import { renderToString } from 'react-dom/server';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { SoccerArenaView } from './SoccerArenaView';
import { ARENA_VIEW_MODE_STORAGE_KEY, type ArenaViewMode } from './soccerViewMode';
import { PlayersLayer, avatarKindForEntity } from '../renderers/soccer/PlayersLayer';
import { soccerSceneFromFrame } from '../renderers/soccer/scene';
import type { SoccerRenderEntity } from '../renderers/soccer/scene';
import type { PitchTransform } from '../renderers/soccer/usePitchTransform';
import type { EntityData, SoccerLeagueLiveState, SoccerMatchState, SoccerParticipant } from '../types/simulation';
import fixture from './__fixtures__/rcss_11v11_show.json';

/**
 * An RCSS-shaped match, rendered end to end (§12 PR 5).
 *
 * The fixture is produced by `core/minigames/soccer/fake_server.py` and adapted
 * through `RcssMonitorAdapter`; `tests/test_rcss_fixture_contract.py` fails if
 * the committed copy drifts from what the server emits. So this suite renders
 * the same bytes the backend would send, not a hand-written approximation.
 */

interface FixturePlayer {
    participant_id: string;
    side: 'left' | 'right';
    uniform_number: number;
    position: { x: number; y: number };
    velocity: { x: number; y: number };
    facing_angle: number;
    stamina: number | null;
}

const players = fixture.canonical.players as FixturePlayer[];
const participants = fixture.participants as SoccerParticipant[];

function rcssMatch(overrides: Partial<SoccerMatchState> = {}): SoccerMatchState {
    const entities: EntityData[] = players.map((player, index) => ({
        id: index + 1,
        type: 'player',
        x: player.position.x,
        y: player.position.y,
        width: 0.6,
        height: 0.6,
        radius: 0.3,
        vel_x: player.velocity.x,
        vel_y: player.velocity.y,
        facing: player.facing_angle,
        stamina: player.stamina ?? undefined,
        team: player.side,
        participant_id: player.participant_id,
    } as unknown as EntityData));

    entities.push({
        id: 0,
        type: 'ball',
        x: fixture.canonical.ball.position.x,
        y: fixture.canonical.ball.position.y,
        width: 0.17,
        height: 0.17,
        radius: 0.085,
        vel_x: fixture.canonical.ball.velocity.x,
        vel_y: fixture.canonical.ball.velocity.y,
    } as unknown as EntityData);

    return {
        match_id: 'rcss-1',
        game_over: false,
        winner_team: null,
        message: 'live',
        frame: 12,
        score: { left: 0, right: 0 },
        entities,
        participants,
        coord_space: fixture.canonical.coord_space as 'canonical',
        geometry: {
            profile_id: 'rcss_standard_105x68',
            length: 105,
            width: 68,
            goal_width: 14.02,
            goal_depth: 2.44,
        },
        play_mode: fixture.canonical.play_mode ?? undefined,
        home_name: 'External Left',
        away_name: 'External Right',
        ...overrides,
    };
}

function stubArenaStorage(mode: ArenaViewMode) {
    const store = new Map<string, string>([
        [ARENA_VIEW_MODE_STORAGE_KEY, mode],
        ['tank_soccer_arena_left_rail', 'expanded'],
        ['tank_soccer_arena_right_rail', 'expanded'],
    ]);
    vi.stubGlobal('window', {
        localStorage: {
            getItem: (key: string) => store.get(key) ?? null,
            setItem: (key: string, value: string) => void store.set(key, value),
        },
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
    });
}

function renderArena(mode: ArenaViewMode, match: SoccerMatchState = rcssMatch()): string {
    stubArenaStorage(mode);
    const liveState = { leaderboard: [], availability: {}, active_match: match } as unknown as SoccerLeagueLiveState;
    return renderToString(
        <SoccerArenaView liveState={liveState} events={[]} worldId="world-1" onBack={() => undefined} />,
    );
}

afterEach(() => vi.unstubAllGlobals());

describe('RCSS fixture', () => {
    it('is a full 11v11 whose uniform numbers collide across sides', () => {
        expect(participants).toHaveLength(22);
        expect(new Set(participants.map((p) => p.participant_id)).size).toBe(22);
        // The exact reason participant_id is the render key (§10.2).
        expect(new Set(participants.map((p) => p.uniform_number)).size).toBe(11);
    });

    it('describes every player as external, never as a fish', () => {
        expect(new Set(participants.map((p) => p.avatar_kind))).toEqual(new Set(['external']));
    });

    it('carries a play mode that is honestly unknown rather than play_on', () => {
        // A numeric monitor play-mode index is not a mode name (§10.4 rule 5).
        expect(fixture.canonical.play_mode).toBe('pm:0');
        expect(fixture.canonical.play_mode).not.toBe('play_on');
    });
});

describe('11v11 layout', () => {
    it('lists all 22 players without assuming a squad size', () => {
        const html = renderArena('tactical');
        const rows = [...html.matchAll(/data-testid="lineup-row-([\w]+)"/g)].map((entry) => entry[1]);
        expect(rows).toHaveLength(22);
        expect(new Set(rows).size).toBe(22);
        expect(html).toMatch(/22<!-- --> players/);
    });

    it.each([3, 6, 11])('renders a %s-a-side roster from the same component', (teamSize) => {
        // §10.4 rule 4: player count is data-driven; no component hard-codes it.
        const subset = participants.filter((participant) => participant.uniform_number <= teamSize);
        const html = renderArena('tactical', rcssMatch({ participants: subset }));
        const rows = [...html.matchAll(/data-testid="lineup-row-[\w]+"/g)];
        expect(rows).toHaveLength(teamSize * 2);
    });

    it('keeps both 22-player teams distinguishable by name, not by number', () => {
        const html = renderArena('tactical');
        expect(html).toContain('External Left');
        expect(html).toContain('External Right');
    });

    it('does not change the pitch size between 3-a-side and 11v11', () => {
        // The canvas is sized from the field aspect, so a fuller pitch must not
        // shrink it - otherwise 11v11 would silently re-fit mid-match.
        const canvas = (html: string) => html.match(/<canvas[^>]*width="(\d+)"[^>]*height="(\d+)"/)?.slice(1, 3).join('x');
        const small = renderArena('tactical', rcssMatch({ participants: participants.slice(0, 6) }));
        expect(canvas(renderArena('tactical'))).toBe(canvas(small));
    });
});

describe('external participants on the pitch', () => {
    const transform = { toScreen: (x: number, y: number) => [x, y], scale: 10 } as unknown as PitchTransform;

    function scene(): SoccerRenderEntity[] {
        return soccerSceneFromFrame(
            { worldType: 'soccer', viewMode: 'topdown', snapshot: rcssMatch() },
            transform,
        ).entities.filter((entity) => entity.type === 'player');
    }

    it('joins every entity to its participant through participant_id', () => {
        const entities = scene();
        expect(entities).toHaveLength(22);
        expect(entities.every((entity) => entity.participant?.avatar_kind === 'external')).toBe(true);
    });

    it('takes the neutral avatar branch, because there is no genome to draw', () => {
        expect(new Set(scene().map(avatarKindForEntity))).toEqual(new Set(['external']));
    });

    it('flips canonical +y north to canvas +y down exactly once', () => {
        const entities = scene();
        for (const entity of entities) {
            const source = players.find((player) => player.participant_id === entity.participant?.participant_id);
            expect(source).toBeDefined();
            expect(entity.fieldY).toBeCloseTo(-source!.position.y, 6);
            expect(entity.fieldX).toBeCloseTo(source!.position.x, 6);
        }
    });

    it('draws all 22 without throwing on a missing genome', () => {
        const ctx = {
            save: vi.fn(), restore: vi.fn(), translate: vi.fn(), rotate: vi.fn(),
            beginPath: vi.fn(), arc: vi.fn(), moveTo: vi.fn(), lineTo: vi.fn(), closePath: vi.fn(),
            roundRect: vi.fn(), fill: vi.fn(), stroke: vi.fn(), fillText: vi.fn(), setLineDash: vi.fn(),
        } as unknown as CanvasRenderingContext2D;
        new PlayersLayer().draw(ctx, scene(), false, { enabled: true });
        expect(vi.mocked(ctx.translate).mock.calls).toHaveLength(22);
    });
});

describe('Analysis mode', () => {
    it('replaces the transient cards with a metrics stack and a timeline', () => {
        const html = renderArena('analysis');
        expect(html).toContain('data-testid="soccer-analysis-panel"');
        expect(html).toContain('data-testid="soccer-match-timeline"');
        expect(html).not.toContain('data-testid="soccer-event-presenter"');
        expect(html).not.toContain('data-testid="soccer-formation-panel"');
    });

    it('tabulates every player, not a truncated top few', () => {
        const html = renderArena('analysis');
        expect([...html.matchAll(/data-testid="analysis-row-[\w]+"/g)]).toHaveLength(22);
    });

    it('reads absent metrics as blank rather than inventing a number', () => {
        // The fixture carries no possession field.
        expect(renderArena('analysis')).toContain('—');
    });
});
