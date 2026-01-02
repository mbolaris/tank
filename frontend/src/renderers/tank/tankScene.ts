
import type { EntityData } from '../../types/simulation';

export interface TankEntity {
    id: number;
    x: number;
    y: number;
    radius: number;
    headingRad?: number; // Not always available in snapshot, but maybe inferred from velocity?
    kind: string; // 'fish', 'food', etc.
    energy?: number;
    colorHue?: number;
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

            entities.push({
                id: e.id,
                x: e.x,
                y: e.y,
                radius: getRadius(e.width, e.height),
                headingRad,
                kind: e.type,
                energy: e.energy,
                colorHue: e.genome_data?.color_hue
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
