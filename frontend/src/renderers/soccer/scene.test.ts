import { describe, expect, it } from 'vitest';
import type { RenderFrame } from '../../rendering/types';
import type { SoccerMatchState } from '../../types/simulation';
import { soccerSceneFromFrame } from './scene';
import type { PitchTransform } from './usePitchTransform';

// A plain identity-ish transform: possession is about the participant join, not
// about pixel placement, so a literal keeps this test independent of layout.
const transform: PitchTransform = {
    scale: 4,
    originX: 400,
    originY: 225,
    toScreen: (x, y) => [400 + x * 4, 225 + y * 4],
    toField: (px, py) => [(px - 400) / 4, (py - 225) / 4],
};

function player(participantId: string, x: number, hasBallHint?: boolean) {
    return {
        id: Number(participantId.split('_')[1]),
        type: 'player' as const,
        x,
        y: 0,
        width: 0.6,
        height: 0.6,
        radius: 0.3,
        vel_x: 0,
        vel_y: 0,
        participant_id: participantId,
        team: 'left' as const,
        render_hint: { participant_id: participantId, has_ball: hasBallHint },
    };
}

function frameOf(state: Partial<SoccerMatchState>): RenderFrame {
    return {
        worldType: 'soccer',
        viewMode: 'topdown',
        snapshot: {
            match_id: 'm-1',
            game_over: false,
            winner_team: null,
            message: '',
            frame: 10,
            score: { left: 0, right: 0 },
            coord_space: 'legacy_render',
            entities: [],
            ...state,
        } as SoccerMatchState,
    } as RenderFrame;
}

describe('soccerSceneFromFrame possession', () => {
    it('marks only the participant named by ball_owner', () => {
        const scene = soccerSceneFromFrame(
            frameOf({ ball_owner: 'left_2', entities: [player('left_1', -5), player('left_2', 0), player('left_3', 5)] }),
            transform,
        );
        expect(scene.entities.filter((entity) => entity.has_ball)).toHaveLength(1);
        expect(scene.entities.find((entity) => entity.has_ball)?.participant?.participant_id ?? 'left_2').toBe('left_2');
        const owner = scene.entities.find((entity) => entity.has_ball);
        expect(owner?.id).toBe(2);
    });

    it('draws no possession ring for a loose ball', () => {
        const scene = soccerSceneFromFrame(
            // A stale legacy hint must not resurrect a ring once ball_owner is
            // explicitly null - that is the backend saying nobody controls it.
            frameOf({ ball_owner: null, entities: [player('left_1', 0, true), player('left_2', 9)] }),
            transform,
        );
        expect(scene.entities.every((entity) => !entity.has_ball)).toBe(true);
    });

    it('falls back to the legacy has_ball hint when ball_owner is absent', () => {
        const scene = soccerSceneFromFrame(
            frameOf({ entities: [player('left_1', 0, true), player('left_2', 9, false)] }),
            transform,
        );
        expect(scene.entities.filter((entity) => entity.has_ball)).toHaveLength(1);
        expect(scene.entities.find((entity) => entity.has_ball)?.id).toBe(1);
    });

    it('never marks the ball itself as a possessor', () => {
        const ball = {
            id: 99,
            type: 'ball' as const,
            x: 0,
            y: 0,
            width: 0.22,
            height: 0.22,
            radius: 0.11,
            vel_x: 0,
            vel_y: 0,
            has_ball: true,
        };
        const scene = soccerSceneFromFrame(frameOf({ ball_owner: 'left_1', entities: [ball, player('left_1', 0)] }), transform);
        expect(scene.entities.find((entity) => entity.type === 'ball')?.has_ball).toBe(false);
    });
});
