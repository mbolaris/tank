import { renderToString } from 'react-dom/server';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { SoccerArenaView } from './SoccerArenaView';
import { ARENA_VIEW_MODE_STORAGE_KEY, type ArenaViewMode } from './soccerViewMode';
import type { SoccerLeagueLiveState } from '../types/simulation';

/**
 * The suite renders through `renderToString`, so it asserts what each mode
 * *mounts* rather than driving clicks - the project has no DOM test
 * environment. Interaction wiring is covered by the pure units either side of
 * it: `soccerViewMode` for the hotkeys, `LineupPanel` for the selected row,
 * and `PlayersLayer` for the ring the selection draws on the pitch.
 */

const RAIL_KEYS = {
    left: 'tank_soccer_arena_left_rail',
    right: 'tank_soccer_arena_right_rail',
};

function stubArenaStorage(mode: ArenaViewMode, railsExpanded = true) {
    const store = new Map<string, string>([
        [ARENA_VIEW_MODE_STORAGE_KEY, mode],
        [RAIL_KEYS.left, railsExpanded ? 'expanded' : 'collapsed'],
        [RAIL_KEYS.right, railsExpanded ? 'expanded' : 'collapsed'],
    ]);
    vi.stubGlobal('window', {
        localStorage: {
            getItem: (key: string) => store.get(key) ?? null,
            setItem: (key: string, value: string) => void store.set(key, value),
        },
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        matchMedia: undefined,
    });
}

afterEach(() => vi.unstubAllGlobals());

const liveState: SoccerLeagueLiveState = {
    leaderboard: [],
    availability: {},
    active_match: {
        match_id: 'match-1',
        game_over: false,
        winner_team: null,
        message: 'live',
        frame: 120,
        score: { left: 1, right: 0 },
        entities: [],
        home_name: 'World 1A',
        away_name: 'Reef Delta',
        ball_owner: 'left_1',
        participants: [
            { participant_id: 'left_1', side: 'left', team_id: 'left', uniform_number: 1, avatar_kind: 'fish', fish_id: 284, generation: 41 },
            { participant_id: 'right_1', side: 'right', team_id: 'right', uniform_number: 1, avatar_kind: 'fish', fish_id: 12, generation: 33 },
        ],
        events: [{ frame: 118, seq: 3, kind: 'goal', side: 'left', actor: 'left_1', event_id: 'match-1-goal-118-3' }],
    },
};

function renderArena(mode: ArenaViewMode, railsExpanded = true): string {
    stubArenaStorage(mode, railsExpanded);
    return renderToString(
        <SoccerArenaView liveState={liveState} events={[]} worldId="world-1" onBack={() => undefined} />,
    );
}

function canvasAttributes(html: string): string {
    const match = html.match(/<canvas[^>]*>/);
    if (!match) throw new Error('the arena rendered no pitch canvas');
    const width = match[0].match(/width="(\d+)"/);
    const height = match[0].match(/height="(\d+)"/);
    return `${width?.[1]}x${height?.[1]}`;
}

describe('SoccerArenaView view modes', () => {
    it('switching mode does not re-fit or jump the pitch', () => {
        // §7: the pitch box is sized from the host width and the field aspect,
        // and view mode is not an input to either. A change that made the pitch
        // depend on the mode would fail here.
        expect(canvasAttributes(renderArena('tactical'))).toBe(canvasAttributes(renderArena('broadcast')));
    });

    it('restores the persisted mode on mount', () => {
        expect(renderArena('tactical')).toContain('data-view-mode="tactical"');
        expect(renderArena('broadcast')).toContain('data-view-mode="broadcast"');
    });

    it('offers both modes as one exclusive control', () => {
        const html = renderArena('tactical');
        expect(html).toContain('data-testid="arena-view-mode-broadcast"');
        expect(html).toContain('data-testid="arena-view-mode-tactical"');
        expect(html).toMatch(/role="radio" aria-checked="true"[^>]*arena-view-mode-tactical/);
    });
});

describe('Tactical mode', () => {
    it('covers no part of the pitch with event cards', () => {
        // §3.1 gives Tactical a 0% occlusion budget: the goal in the fixture
        // must reach the viewer through the timeline, never over the field.
        const tactical = renderArena('tactical');
        expect(tactical).not.toContain('data-testid="soccer-event-presenter"');
        expect(tactical).toContain('data-testid="soccer-match-timeline"');
        expect(tactical).toContain('GOAL');
    });

    it('keeps the broadcast cards on the pitch in Broadcast', () => {
        const broadcast = renderArena('broadcast');
        expect(broadcast).toContain('data-testid="soccer-event-presenter"');
        expect(broadcast).not.toContain('data-testid="soccer-match-timeline"');
    });

    it('swaps the right rail from Progress to Formation & Spacing', () => {
        expect(renderArena('tactical')).toContain('data-testid="soccer-formation-panel"');
        expect(renderArena('tactical')).not.toContain('data-testid="soccer-team-progress"');
        expect(renderArena('broadcast')).toContain('data-testid="soccer-team-progress"');
    });

    it('fills the left rail with the real lineup in both modes', () => {
        expect(renderArena('tactical')).toContain('data-testid="lineup-row-left_1"');
        expect(renderArena('broadcast')).toContain('data-testid="lineup-row-right_1"');
    });

    it('compresses the scoreboard', () => {
        expect(renderArena('tactical')).toContain('data-compact="true"');
        expect(renderArena('broadcast')).not.toContain('data-compact="true"');
    });

    it('waits for samples instead of reporting a confident zero', () => {
        // One SSR pass feeds the metrics no frames, so the rail must say so.
        expect(renderArena('tactical')).toContain('Sampling play');
    });
});
