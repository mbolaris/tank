import { useEffect, useRef, useState } from 'react';
import type { EntityData, SoccerMatchState } from '../types/simulation';

export interface AnimationClock {
    push(snapshot: SoccerMatchState, receivedAtMs: number): void;
    sample(nowMs: number): SoccerMatchState | null;
}

/**
 * How far behind real time the pitch renders.
 *
 * Interpolation needs two snapshots that *bracket* the render time. Sampling at
 * `now` never does: `now` is always at or after the newest arrival, so alpha
 * pins to 1 and every frame just shows the latest server state - the exact
 * stutter this replaces. Rendering at `now - delay` keeps the newest snapshot
 * in the future, so there is always a real interval to interpolate across.
 *
 * One soccer update interval (~100 ms) is the smallest delay that reliably
 * brackets, and it is short enough to stay imperceptible.
 */
export const DEFAULT_INTERPOLATION_DELAY_MS = 100;

/** Positions barely changed; skip the React update rather than re-rendering. */
const POSITION_EPSILON = 1e-3;

function entityKey(entity: EntityData): string {
    const participantId = (entity as EntityData & { participant_id?: string }).participant_id;
    return participantId ? `participant:${participantId}` : `${entity.type}:${entity.id}`;
}

function lerp(start: number, end: number, amount: number): number {
    return start + (end - start) * amount;
}

/** Interpolate along the short arc so a heading crossing ±π does not spin backwards. */
export function lerpAngle(startRad: number, endRad: number, alpha: number): number {
    const twoPi = Math.PI * 2;
    let diff = (endRad - startRad) % twoPi;
    if (diff > Math.PI) diff -= twoPi;
    if (diff < -Math.PI) diff += twoPi;
    return startRad + diff * alpha;
}

/**
 * Interpolate physical state only.
 *
 * Identity, events, score, participants, play mode and every other metadata
 * field come from the newest snapshot untouched - a half-interpolated score or
 * a resurrected event would be a lie, not a smoother picture.
 */
export function interpolateMatchState(
    previous: SoccerMatchState,
    newest: SoccerMatchState,
    amount: number,
): SoccerMatchState {
    const alpha = Math.max(0, Math.min(1, amount));
    const previousEntities = new Map(previous.entities.map((entity) => [entityKey(entity), entity]));
    return {
        ...newest,
        frame: Math.round(lerp(previous.frame, newest.frame, alpha)),
        entities: newest.entities.map((entity) => {
            // An entity that only exists in the newest snapshot (a substitution,
            // a respawned ball) renders at its true position immediately.
            const before = previousEntities.get(entityKey(entity));
            if (!before || before.type !== entity.type) return entity;
            return {
                ...entity,
                x: lerp(before.x, entity.x, alpha),
                y: lerp(before.y, entity.y, alpha),
                vel_x: lerp(before.vel_x ?? 0, entity.vel_x ?? 0, alpha),
                vel_y: lerp(before.vel_y ?? 0, entity.vel_y ?? 0, alpha),
                facing:
                    before.facing !== undefined && entity.facing !== undefined
                        ? lerpAngle(before.facing, entity.facing, alpha)
                        : entity.facing,
                stamina:
                    before.stamina !== undefined && entity.stamina !== undefined
                        ? lerp(before.stamina, entity.stamina, alpha)
                        : entity.stamina,
            };
        }),
    };
}

/** Two snapshots plus their arrival times, sampled on a delayed render clock. */
export class MatchAnimator implements AnimationClock {
    private previous: SoccerMatchState | null = null;
    private newest: SoccerMatchState | null = null;
    private previousAt = 0;
    private newestAt = 0;
    private readonly delayMs: number;

    constructor(delayMs: number = DEFAULT_INTERPOLATION_DELAY_MS) {
        this.delayMs = delayMs;
    }

    push(snapshot: SoccerMatchState, receivedAtMs: number): void {
        const isDiscontinuity =
            !this.newest ||
            this.newest.match_id !== snapshot.match_id ||
            snapshot.frame < this.newest.frame;

        if (isDiscontinuity) {
            // A new match or a rewound clock has nothing to interpolate from.
            this.reset();
            this.previous = snapshot;
            this.newest = snapshot;
            this.previousAt = receivedAtMs;
            this.newestAt = receivedAtMs;
            return;
        }

        // A redelivered frame carries no new motion; keep the existing interval.
        if (this.newest!.frame === snapshot.frame) return;

        this.previous = this.newest;
        this.previousAt = this.newestAt;
        this.newest = snapshot;
        this.newestAt = Math.max(receivedAtMs, this.previousAt);
    }

    sample(nowMs: number): SoccerMatchState | null {
        if (!this.newest) return null;
        if (!this.previous || this.newestAt <= this.previousAt) return this.newest;

        const renderTime = nowMs - this.delayMs;
        // Hold, never extrapolate: a guessed position past the newest snapshot
        // has to be corrected on the next arrival, which reads as a snap.
        if (renderTime <= this.previousAt) return this.previous;
        if (renderTime >= this.newestAt) return this.newest;

        const alpha = (renderTime - this.previousAt) / (this.newestAt - this.previousAt);
        return interpolateMatchState(this.previous, this.newest, alpha);
    }

    reset(): void {
        this.previous = null;
        this.newest = null;
        this.previousAt = 0;
        this.newestAt = 0;
    }
}

/** True when two sampled states would render identically. */
function isMateriallyUnchanged(current: SoccerMatchState, next: SoccerMatchState): boolean {
    if (current === next) return true;
    if (current.match_id !== next.match_id) return false;
    if (current.frame !== next.frame) return false;
    if (current.entities.length !== next.entities.length) return false;
    for (let index = 0; index < next.entities.length; index += 1) {
        const before = current.entities[index];
        const after = next.entities[index];
        if (before.id !== after.id || before.type !== after.type) return false;
        if (Math.abs(before.x - after.x) > POSITION_EPSILON) return false;
        if (Math.abs(before.y - after.y) > POSITION_EPSILON) return false;
        if (
            before.facing !== undefined &&
            after.facing !== undefined &&
            Math.abs(before.facing - after.facing) > POSITION_EPSILON
        ) {
            return false;
        }
    }
    return true;
}

/** Keep the canvas alive at display cadence while inputs arrive at websocket cadence. */
export function useMatchAnimator(snapshot: SoccerMatchState | null): SoccerMatchState | null {
    const animatorRef = useRef<MatchAnimator | null>(null);
    const [animated, setAnimated] = useState<SoccerMatchState | null>(snapshot);
    if (animatorRef.current == null) animatorRef.current = new MatchAnimator();

    useEffect(() => {
        const animator = animatorRef.current;
        if (!animator) return;
        if (snapshot) {
            const now = performance.now();
            animator.push(snapshot, now);
            // Sample immediately so the first arrival paints without waiting a
            // frame; the same guard keeps this from re-rendering needlessly.
            const sampled = animator.sample(now) ?? snapshot;
            setAnimated((current) => (current && isMateriallyUnchanged(current, sampled) ? current : sampled));
        } else {
            animator.reset();
            setAnimated(null);
        }
    }, [snapshot]);

    useEffect(() => {
        let frameHandle = 0;
        const tick = (nowMs: number) => {
            const sampled = animatorRef.current?.sample(nowMs) ?? null;
            setAnimated((current) => {
                if (!current || !sampled) return sampled;
                return isMateriallyUnchanged(current, sampled) ? current : sampled;
            });
            frameHandle = window.requestAnimationFrame(tick);
        };
        frameHandle = window.requestAnimationFrame(tick);
        return () => window.cancelAnimationFrame(frameHandle);
    }, []);

    return animated;
}
