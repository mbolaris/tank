import { afterEach, describe, expect, it, vi } from 'vitest';
import {
    DEFAULT_SOCCER_GEOMETRY,
    resetSoccerGeometryWarningState,
    resolveSoccerGeometry,
} from './fieldGeometry';
import type { SoccerMatchState } from '../../types/simulation';

const state = (geometry: SoccerMatchState['geometry']): SoccerMatchState => ({
    match_id: 'test',
    game_over: false,
    winner_team: null,
    message: '',
    frame: 0,
    score: { left: 0, right: 0 },
    entities: [],
    geometry,
});

describe('resolveSoccerGeometry', () => {
    afterEach(() => {
        resetSoccerGeometryWarningState();
        vi.restoreAllMocks();
    });

    it('retains the exact marking offsets for both shipped profiles', () => {
        const standard = resolveSoccerGeometry(state({
            profile_id: 'rcss_standard_105x68',
            length: 105,
            width: 68,
            goal_width: 14.02,
            goal_depth: 2.44,
            centre_circle_radius: 9.15,
            penalty_area_depth: 16.5,
            penalty_area_width: 40.32,
            goal_area_depth: 5.5,
            goal_area_width: 18.32,
            penalty_spot_distance: 11,
            corner_arc_radius: 1,
        }));
        const small = resolveSoccerGeometry(state({
            profile_id: 'tank_small_sided',
            length: 100,
            width: 60,
            goal_width: 13,
            goal_depth: 2,
            centre_circle_radius: 7,
            penalty_area_depth: 10,
            penalty_area_width: 28,
            goal_area_depth: 3.5,
            goal_area_width: 16,
            penalty_spot_distance: 8,
            corner_arc_radius: 0.75,
        }));

        expect(standard.penalty_area_depth).toBe(16.5);
        expect(standard.penalty_spot_distance).toBe(11);
        expect(small.penalty_area_depth).toBe(10);
        expect(small.penalty_spot_distance).toBe(8);
        expect(small.corner_arc_radius).toBe(0.75);
    });

    it('preserves zero-valued markings so the layer can omit them', () => {
        const geometry = resolveSoccerGeometry(state({
            ...DEFAULT_SOCCER_GEOMETRY,
            profile_id: 'tank_small_sided',
            centre_circle_radius: 0,
            corner_arc_radius: 0,
        }));
        expect(geometry.centre_circle_radius).toBe(0);
        expect(geometry.corner_arc_radius).toBe(0);
    });

    it('falls back to the standard profile and warns once for an unknown profile', () => {
        const warn = vi.spyOn(console, 'warn').mockImplementation(() => undefined);
        const unknown = state({
            ...DEFAULT_SOCCER_GEOMETRY,
            profile_id: 'made_up_profile',
            length: 1,
            width: 1,
        });
        expect(resolveSoccerGeometry(unknown)).toEqual(DEFAULT_SOCCER_GEOMETRY);
        expect(resolveSoccerGeometry(unknown)).toEqual(DEFAULT_SOCCER_GEOMETRY);
        expect(warn).toHaveBeenCalledTimes(1);
    });
});
