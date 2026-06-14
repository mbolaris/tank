import type { EntityData } from '../types/simulation';

const SIMULATION_FRAME_MS = 1000 / 30;
const CORRECTION_DURATION_MS = 100;
const MAX_EXTRAPOLATION_MS = 200;
const MAX_INTERPOLATION_DISTANCE = 96;

interface PositionTrack {
    x: number;
    y: number;
    velX: number;
    velY: number;
    acceptedAtMs: number;
    correctionX: number;
    correctionY: number;
}

function clamp(value: number, min: number, max: number): number {
    return Math.max(min, Math.min(max, value));
}

function sampleTrack(track: PositionTrack, nowMs: number): { x: number; y: number } {
    const elapsedMs = clamp(nowMs - track.acceptedAtMs, 0, MAX_EXTRAPOLATION_MS);
    const elapsedFrames = elapsedMs / SIMULATION_FRAME_MS;
    const correctionScale = 1 - clamp(elapsedMs / CORRECTION_DURATION_MS, 0, 1);
    return {
        x: track.x + track.velX * elapsedFrames + track.correctionX * correctionScale,
        y: track.y + track.velY * elapsedFrames + track.correctionY * correctionScale,
    };
}

/**
 * Smooths display positions between lower-frequency server snapshots using
 * short-horizon dead reckoning and correction blending.
 * Source entities remain untouched and authoritative.
 */
export class EntityPositionInterpolator {
    private tracks = new Map<number, PositionTrack>();
    private lastEntities: EntityData[] | null = null;

    reset(): void {
        this.tracks.clear();
        this.lastEntities = null;
    }

    interpolate(entities: EntityData[], nowMs: number): EntityData[] {
        if (entities !== this.lastEntities) {
            this.acceptSnapshot(entities, nowMs);
        }

        let hasInterpolatedPosition = false;
        const renderedEntities = entities.map((entity) => {
            const track = this.tracks.get(entity.id);
            if (!track) return entity;

            const position = sampleTrack(track, nowMs);
            if (position.x === entity.x && position.y === entity.y) {
                return entity;
            }

            hasInterpolatedPosition = true;
            return { ...entity, x: position.x, y: position.y };
        });

        return hasInterpolatedPosition ? renderedEntities : entities;
    }

    private acceptSnapshot(entities: EntityData[], nowMs: number): void {
        const nextTracks = new Map<number, PositionTrack>();

        for (const entity of entities) {
            const previousTrack = this.tracks.get(entity.id);
            const previousPosition = previousTrack
                ? sampleTrack(previousTrack, nowMs)
                : { x: entity.x, y: entity.y };
            const correctionX = previousPosition.x - entity.x;
            const correctionY = previousPosition.y - entity.y;
            const shouldSnap = (
                !previousTrack
                || (correctionX * correctionX + correctionY * correctionY)
                    > MAX_INTERPOLATION_DISTANCE * MAX_INTERPOLATION_DISTANCE
            );

            nextTracks.set(entity.id, {
                x: entity.x,
                y: entity.y,
                velX: entity.vel_x ?? 0,
                velY: entity.vel_y ?? 0,
                acceptedAtMs: nowMs,
                correctionX: shouldSnap ? 0 : correctionX,
                correctionY: shouldSnap ? 0 : correctionY,
            });
        }

        this.tracks = nextTracks;
        this.lastEntities = entities;
    }
}
