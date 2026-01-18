
import type { EntityData } from '../../types/simulation';
import type { FishGenomeData } from '../../types/simulation';

export interface PokerEffectState {
    status: string;
    amount: number;
    target_id?: number;
    target_type?: string;
}

export interface TankEntity {
    id: number;
    x: number;
    y: number;
    width: number;
    height: number;
    radius: number;
    headingRad?: number; // Not always available in snapshot, but maybe inferred from velocity?
    kind: string; // 'fish', 'food', etc.
    team?: string; // For soccer goal zones
    energy?: number;
    food_type?: string;
    plant_type?: number;
    genome_data?: FishGenomeData;
    plant_genome?: Record<string, unknown>;
    size_multiplier?: number;
    iterations?: number;
    nectar_ready?: boolean;
    vel_x?: number;
    vel_y?: number;
    death_effect_state?: { cause: string };
    poker_effect_state?: PokerEffectState;
    birth_effect_timer?: number;
}

export interface TankScene {
    width: number;
    height: number;
    entities: TankEntity[];
    time: number;
}

// Helper to infer radius from width/height (approximate for circle)
function getRadius(width: number, height: number): number {
    return Math.max(width, height) / 2;
}

export function buildTankScene(snapshot: any): TankScene {
    // Snapshot is expected to be SimulationUpdate
    // But we use 'any' to decouple for now, or we can type it if available.
    // Ideally we assume it matches the structure used in TankSideRenderer.

    const entities: TankEntity[] = [];

    const rawEntities = snapshot.snapshot?.entities ?? snapshot.entities;
    if (rawEntities && Array.isArray(rawEntities)) {
        rawEntities.forEach((e: EntityData) => {
            // Calculate heading from velocity if available
            let headingRad = undefined;
            if (e.vel_x !== undefined && e.vel_y !== undefined && (e.vel_x !== 0 || e.vel_y !== 0)) {
                headingRad = Math.atan2(e.vel_y, e.vel_x);
            }

            // Some entities (goalzone, ball) use center coords already;
            // others use top-left corner coords and need offset
            const useCenterCoords = e.type === 'goal_zone' || e.type === 'goalzone' || e.type === 'ball';
            const entityX = useCenterCoords ? e.x : e.x + e.width / 2;
            const entityY = useCenterCoords ? e.y : e.y + e.height / 2;

            entities.push({
                id: e.id,
                x: entityX,
                y: entityY,
                width: e.width,
                height: e.height,
                radius: getRadius(e.width, e.height),
                headingRad,
                kind: e.type,
                team: (e as any).team,
                energy: e.energy,
                food_type: e.food_type,
                plant_type: e.plant_type,
                genome_data: e.genome_data,
                plant_genome: (e as any).genome as Record<string, unknown> | undefined,
                size_multiplier: (e as any).size_multiplier as number | undefined,
                iterations: (e as any).iterations as number | undefined,
                nectar_ready: (e as any).nectar_ready as boolean | undefined,
                vel_x: e.vel_x,
                vel_y: e.vel_y,
                death_effect_state: (e as any).death_effect_state as { cause: string } | undefined,
                poker_effect_state: e.poker_effect_state,
                birth_effect_timer: e.birth_effect_timer,
            });
        });
    }

    const stats = snapshot.snapshot?.stats ?? snapshot.stats;

    return {
        width: 1088, // Constant for now, or read from snapshot if available
        height: 612,
        entities,
        time: stats?.time || 0
    };
}
