import type { RenderSnapshot } from '../../rendering/types';
import type { SoccerFieldGeometry, SoccerMatchState, SimulationUpdate } from '../../types/simulation';

export interface ResolvedSoccerFieldGeometry {
    profile_id: string;
    length: number;
    width: number;
    goal_width: number;
    goal_depth: number;
    centre_circle_radius: number;
    penalty_area_depth: number;
    penalty_area_width: number;
    goal_area_depth: number;
    goal_area_width: number;
    penalty_spot_distance: number;
    corner_arc_radius: number;
}

export const DEFAULT_SOCCER_GEOMETRY: ResolvedSoccerFieldGeometry = {
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
};

const warnedProfiles = new Set<string>();

function isSimulationUpdate(snapshot: RenderSnapshot): snapshot is SimulationUpdate {
    return (snapshot as SimulationUpdate).snapshot !== undefined;
}

export function soccerMatchSnapshot(snapshot: RenderSnapshot): SoccerMatchState {
    if (isSimulationUpdate(snapshot)) {
        return ((snapshot.snapshot ?? snapshot) as unknown) as SoccerMatchState;
    }
    return snapshot as SoccerMatchState;
}

function hasGeometryValues(geometry: SoccerFieldGeometry | undefined): geometry is SoccerFieldGeometry {
    return Boolean(geometry && geometry.length > 0 && geometry.width > 0);
}

/** Resolve additive PR 0 geometry, retaining legacy dimensions when necessary. */
export function resolveSoccerGeometry(snapshot: RenderSnapshot): ResolvedSoccerFieldGeometry {
    const state = soccerMatchSnapshot(snapshot);
    const supplied = state.geometry;
    const legacy = state.field;

    if (!hasGeometryValues(supplied)) {
        return {
            ...DEFAULT_SOCCER_GEOMETRY,
            length: legacy?.length ?? DEFAULT_SOCCER_GEOMETRY.length,
            width: legacy?.width ?? DEFAULT_SOCCER_GEOMETRY.width,
            goal_width: legacy?.goal_width ?? DEFAULT_SOCCER_GEOMETRY.goal_width,
            goal_depth: legacy?.goal_depth ?? DEFAULT_SOCCER_GEOMETRY.goal_depth,
        };
    }

    const profileId = supplied.profile_id || DEFAULT_SOCCER_GEOMETRY.profile_id;
    if (profileId !== DEFAULT_SOCCER_GEOMETRY.profile_id && profileId !== 'tank_small_sided' && !warnedProfiles.has(profileId)) {
        warnedProfiles.add(profileId);
        console.warn(`Unknown soccer field profile "${profileId}"; falling back to the standard profile.`);
    }
    if (profileId !== DEFAULT_SOCCER_GEOMETRY.profile_id && profileId !== 'tank_small_sided') {
        return { ...DEFAULT_SOCCER_GEOMETRY };
    }

    return {
        profile_id: profileId,
        length: supplied.length,
        width: supplied.width,
        goal_width: supplied.goal_width,
        goal_depth: supplied.goal_depth,
        centre_circle_radius: supplied.centre_circle_radius ?? DEFAULT_SOCCER_GEOMETRY.centre_circle_radius,
        penalty_area_depth: supplied.penalty_area_depth ?? DEFAULT_SOCCER_GEOMETRY.penalty_area_depth,
        penalty_area_width: supplied.penalty_area_width ?? DEFAULT_SOCCER_GEOMETRY.penalty_area_width,
        goal_area_depth: supplied.goal_area_depth ?? DEFAULT_SOCCER_GEOMETRY.goal_area_depth,
        goal_area_width: supplied.goal_area_width ?? DEFAULT_SOCCER_GEOMETRY.goal_area_width,
        penalty_spot_distance: supplied.penalty_spot_distance ?? DEFAULT_SOCCER_GEOMETRY.penalty_spot_distance,
        corner_arc_radius: supplied.corner_arc_radius ?? DEFAULT_SOCCER_GEOMETRY.corner_arc_radius,
    };
}

export function resetSoccerGeometryWarningState(): void {
    warnedProfiles.clear();
}
