import { useEffect, useRef, useState } from 'react';
import type { EntityData, SoccerMatchState } from '../types/simulation';

export interface AnimationClock {
    push(snapshot: SoccerMatchState, receivedAtMs: number): void;
    sample(nowMs: number): SoccerMatchState | null;
}

function entityKey(entity: EntityData): string {
    const participantId = (entity as EntityData & { participant_id?: string }).participant_id;
    return participantId ? `participant:${participantId}` : `${entity.type}:${entity.id}`;
}

function lerp(start: number, end: number, amount: number): number {
    return start + (end - start) * amount;
}

/** Interpolate only physical entity state; events and identity stay newest. */
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
            const before = previousEntities.get(entityKey(entity));
            if (!before || before.type !== entity.type) return entity;
            return {
                ...entity,
                x: lerp(before.x, entity.x, alpha),
                y: lerp(before.y, entity.y, alpha),
                vel_x: lerp(before.vel_x ?? 0, entity.vel_x ?? 0, alpha),
                vel_y: lerp(before.vel_y ?? 0, entity.vel_y ?? 0, alpha),
            };
        }),
    };
}

export class MatchAnimator implements AnimationClock {
    private previous: SoccerMatchState | null = null;
    private newest: SoccerMatchState | null = null;
    private previousAt = 0;
    private newestAt = 0;

    push(snapshot: SoccerMatchState, receivedAtMs: number): void {
        if (this.newest?.match_id === snapshot.match_id && this.newest.frame === snapshot.frame) return;
        if (this.newest) {
            this.previous = this.newest;
            this.previousAt = this.newestAt;
        }
        this.newest = snapshot;
        this.newestAt = Math.max(receivedAtMs, this.previousAt);
    }

    sample(nowMs: number): SoccerMatchState | null {
        if (!this.newest) return null;
        if (!this.previous || this.newestAt <= this.previousAt) return this.newest;
        const amount = Math.max(0, Math.min(1, (nowMs - this.previousAt) / (this.newestAt - this.previousAt)));
        return interpolateMatchState(this.previous, this.newest, amount);
    }
}

/** Keep the canvas alive at display cadence while inputs arrive at websocket cadence. */
export function useMatchAnimator(snapshot: SoccerMatchState | null): SoccerMatchState | null {
    const animatorRef = useRef<MatchAnimator | null>(null);
    const [animated, setAnimated] = useState<SoccerMatchState | null>(snapshot);
    if (animatorRef.current == null) animatorRef.current = new MatchAnimator();

    useEffect(() => {
        if (snapshot) {
            animatorRef.current?.push(snapshot, performance.now());
            setAnimated(animatorRef.current?.sample(performance.now()) ?? snapshot);
        } else {
            animatorRef.current = new MatchAnimator();
            setAnimated(null);
        }
    }, [snapshot]);

    useEffect(() => {
        let frameHandle = 0;
        const tick = (nowMs: number) => {
            setAnimated(animatorRef.current?.sample(nowMs) ?? null);
            frameHandle = window.requestAnimationFrame(tick);
        };
        frameHandle = window.requestAnimationFrame(tick);
        return () => window.cancelAnimationFrame(frameHandle);
    }, []);

    return animated;
}
