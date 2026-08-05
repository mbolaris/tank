/**
 * Tactical player trails (§4.1).
 *
 * Samples are stored in **canonical field metres**, never in pixels: a rail
 * opening or a window resize changes the transform, and a pixel-space history
 * would bend every trail already on screen.
 */

import type { SoccerRenderEntity } from './scene';
import type { PitchTransform } from './usePitchTransform';

/** §4.1 "last ~90 frames". Bounds memory at 90 samples per player, forever. */
export const TRAIL_CAPACITY = 90;

const TEAM_COLORS = { left: '#facc15', right: '#f87171' } as const;

export interface TrailSample {
    x: number;
    y: number;
}

/**
 * The trail key. `participant_id` is the render key (§10.2); entity id is only
 * a fallback for legacy payloads that carry no participants, and is namespaced
 * so it can never collide with a participant id.
 */
export function trailKey(player: SoccerRenderEntity): string {
    const participantId = player.participant?.participant_id;
    return participantId !== undefined ? `participant:${participantId}` : `entity:${player.id}`;
}

export class TrailsLayer {
    private readonly trails = new Map<string, TrailSample[]>();
    private lastRecordedFrame: number | null = null;
    private matchId: string | null = null;

    /**
     * Append one sample per player for `frame`.
     *
     * The rAF loop runs ~6x faster than match snapshots arrive, and every tick
     * in between carries interpolated positions. Recording those would fill the
     * buffer with a fraction of a second of history, so a frame is sampled
     * exactly once and repeat ticks are dropped.
     */
    record(players: readonly SoccerRenderEntity[], frame: number, matchId: string | null = null): void {
        if (matchId !== this.matchId) {
            // A different match shares nothing with the previous one's history.
            this.clear();
            this.matchId = matchId;
        }
        // A rewound frame means a replay seek or a restarted match; holding the
        // old future would draw a trail the player has not walked yet.
        if (this.lastRecordedFrame !== null && frame < this.lastRecordedFrame) this.clear();
        if (this.lastRecordedFrame === frame) return;
        this.lastRecordedFrame = frame;

        const live = new Set<string>();
        for (const player of players) {
            const key = trailKey(player);
            live.add(key);
            const samples = this.trails.get(key) ?? [];
            samples.push({ x: player.fieldX, y: player.fieldY });
            if (samples.length > TRAIL_CAPACITY) samples.splice(0, samples.length - TRAIL_CAPACITY);
            this.trails.set(key, samples);
        }

        // Substituted-out and removed players must not leak an entry per match.
        for (const key of [...this.trails.keys()]) {
            if (!live.has(key)) this.trails.delete(key);
        }
    }

    /** Sample count for a player, for tests and diagnostics. */
    samplesFor(key: string): readonly TrailSample[] {
        return this.trails.get(key) ?? [];
    }

    get size(): number {
        return this.trails.size;
    }

    clear(): void {
        this.trails.clear();
        this.lastRecordedFrame = null;
    }

    draw(
        ctx: CanvasRenderingContext2D,
        players: readonly SoccerRenderEntity[],
        transform: PitchTransform,
        selectedParticipantId?: string,
    ): void {
        for (const player of players) {
            const samples = this.trails.get(trailKey(player));
            if (!samples || samples.length < 2) continue;
            const selected =
                selectedParticipantId !== undefined &&
                player.participant?.participant_id === selectedParticipantId;
            this.drawTrail(ctx, samples, transform, player.team, selected);
        }
    }

    private drawTrail(
        ctx: CanvasRenderingContext2D,
        samples: readonly TrailSample[],
        transform: PitchTransform,
        team: SoccerRenderEntity['team'],
        selected: boolean,
    ): void {
        const color = team ? TEAM_COLORS[team] : '#cbd5e1';
        ctx.save();
        try {
            ctx.strokeStyle = color;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            // Segment-wise so the tail fades: a single path can only carry one
            // alpha, and a uniform trail reads as a smear rather than a path.
            for (let index = 1; index < samples.length; index += 1) {
                const progress = index / (samples.length - 1);
                const [fromX, fromY] = transform.toScreen(samples[index - 1].x, samples[index - 1].y);
                const [toX, toY] = transform.toScreen(samples[index].x, samples[index].y);
                ctx.globalAlpha = (selected ? 0.7 : 0.38) * progress;
                ctx.lineWidth = (selected ? 3 : 2) * (0.4 + 0.6 * progress);
                ctx.beginPath();
                ctx.moveTo(fromX, fromY);
                ctx.lineTo(toX, toY);
                ctx.stroke();
            }
        } finally {
            ctx.restore();
        }
    }
}
