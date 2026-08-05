/**
 * Tactical pass lines (§4.1), derived from `ball_owner` transitions.
 *
 * The engine emits no `pass` event - `_emit_event` only ever fires kickoff,
 * goal, half_time and full_time - so a pass has to be *derived*. `ball_owner`
 * is the authoritative "close enough to kick it this cycle" field
 * (`broadcast_metadata.compute_ball_owner`), which makes a change of owner the
 * one honest signal available.
 *
 * A pass is not an `A -> B` transition. The ball leaves A's kickable radius the
 * moment it is struck and only enters B's on arrival, so almost every real pass
 * reads as `A -> null -> B`. This tracks the last non-null owner and the
 * position they released from, then links to the next non-null owner.
 */

import type { SoccerRenderEntity } from './scene';
import type { PitchTransform } from './usePitchTransform';

const MATCH_FRAMES_PER_SECOND = 10;

/** §4.1: pass lines persist ~3 s. */
export const PASS_LINE_HOLD_FRAMES = 3 * MATCH_FRAMES_PER_SECOND;

/**
 * How long the ball may be loose and still link two owners as one pass.
 *
 * Beyond this the move has broken down - a goal reset, a stoppage, or a ball
 * bobbling untouched upfield - and joining the two ends would draw a pass that
 * nobody played.
 */
export const PASS_MAX_LOOSE_FRAMES = 3 * MATCH_FRAMES_PER_SECOND;

/** Bounds the buffer even if a caller stops calling `prune`. */
const MAX_RETAINED_PASSES = 32;

const TEAM_COLORS = { left: '#facc15', right: '#f87171' } as const;

export interface PassLine {
    fromX: number;
    fromY: number;
    toX: number;
    toY: number;
    side: 'left' | 'right';
    frame: number;
}

interface Release {
    participantId: string;
    side: 'left' | 'right' | undefined;
    x: number;
    y: number;
    frame: number;
}

export class PassLinesLayer {
    private passes: PassLine[] = [];
    private release: Release | null = null;
    private lastOwner: string | null = null;
    private lastFrame: number | null = null;
    private matchId: string | null = null;
    private sidesSwapped: boolean | null = null;

    /** Feed one match frame. Repeat and rewound frames are ignored. */
    observe(
        players: readonly SoccerRenderEntity[],
        ballOwner: string | null | undefined,
        frame: number,
        matchId: string | null = null,
        sidesSwapped = false,
    ): void {
        if (matchId !== this.matchId) {
            this.clear();
            this.matchId = matchId;
        }
        // Half time mirrors every position. A pending release recorded before
        // the swap would link to a receiver on the mirrored pitch, and lines
        // already drawn would hang at coordinates nobody is standing on.
        if (this.sidesSwapped !== null && this.sidesSwapped !== sidesSwapped) this.clear();
        this.sidesSwapped = sidesSwapped;
        if (this.lastFrame !== null && frame < this.lastFrame) this.clear();
        if (this.lastFrame === frame) return;
        this.lastFrame = frame;

        // `undefined` means a payload that predates ball_owner. Deriving passes
        // from the legacy per-entity `has_ball` would need its own ownership
        // model; drawing nothing is the honest degradation.
        if (ballOwner === undefined) return;

        const owner = ballOwner ?? null;
        if (owner === this.lastOwner) return;
        const previousOwner = this.lastOwner;
        this.lastOwner = owner;

        if (owner === null) {
            // Ball released. Remember where from, so the receiver can be linked.
            const releaser = previousOwner === null ? undefined : this.findPlayer(players, previousOwner);
            this.release = releaser
                ? {
                      participantId: previousOwner as string,
                      side: releaser.team,
                      x: releaser.fieldX,
                      y: releaser.fieldY,
                      frame,
                  }
                : null;
            return;
        }

        const receiver = this.findPlayer(players, owner);
        // A direct owner-to-owner change (a close-range handover) has no loose
        // phase, so the previous owner is the release point.
        const from =
            this.release ??
            (previousOwner === null
                ? null
                : this.releaseFromPlayer(previousOwner, this.findPlayer(players, previousOwner), frame));
        this.release = null;
        if (!receiver || !from) return;
        if (from.participantId === owner) return;
        if (frame - from.frame > PASS_MAX_LOOSE_FRAMES) return;
        // Only a completed pass is a pass. A change of side is a turnover, and
        // drawing it in the receiving team's colour would credit them with a
        // ball their opponent gave away.
        if (from.side === undefined || from.side !== receiver.team) return;

        this.passes.push({
            fromX: from.x,
            fromY: from.y,
            toX: receiver.fieldX,
            toY: receiver.fieldY,
            side: from.side,
            frame,
        });
        this.prune(frame);
    }

    private releaseFromPlayer(
        participantId: string,
        player: SoccerRenderEntity | undefined,
        frame: number,
    ): Release | null {
        if (!player) return null;
        return { participantId, side: player.team, x: player.fieldX, y: player.fieldY, frame };
    }

    private findPlayer(players: readonly SoccerRenderEntity[], participantId: string): SoccerRenderEntity | undefined {
        return players.find((player) => player.participant?.participant_id === participantId);
    }

    private prune(frame: number): void {
        this.passes = this.passes.filter((pass) => frame - pass.frame <= PASS_LINE_HOLD_FRAMES);
        if (this.passes.length > MAX_RETAINED_PASSES) {
            this.passes.splice(0, this.passes.length - MAX_RETAINED_PASSES);
        }
    }

    /** Currently visible pass lines, for tests and diagnostics. */
    activePasses(frame: number): readonly PassLine[] {
        return this.passes.filter((pass) => frame - pass.frame <= PASS_LINE_HOLD_FRAMES);
    }

    clear(): void {
        this.passes = [];
        this.release = null;
        this.lastOwner = null;
        this.lastFrame = null;
        this.sidesSwapped = null;
    }

    draw(ctx: CanvasRenderingContext2D, frame: number, transform: PitchTransform): void {
        const visible = this.activePasses(frame);
        if (!visible.length) return;
        ctx.save();
        try {
            ctx.lineCap = 'round';
            for (const pass of visible) {
                const age = Math.max(0, frame - pass.frame) / PASS_LINE_HOLD_FRAMES;
                const [fromX, fromY] = transform.toScreen(pass.fromX, pass.fromY);
                const [toX, toY] = transform.toScreen(pass.toX, pass.toY);
                ctx.strokeStyle = TEAM_COLORS[pass.side];
                ctx.globalAlpha = 0.75 * (1 - age);
                ctx.lineWidth = 2;
                ctx.setLineDash([6, 5]);
                ctx.beginPath();
                ctx.moveTo(fromX, fromY);
                ctx.lineTo(toX, toY);
                ctx.stroke();
                this.drawArrowHead(ctx, fromX, fromY, toX, toY);
            }
        } finally {
            ctx.restore();
        }
    }

    private drawArrowHead(
        ctx: CanvasRenderingContext2D,
        fromX: number,
        fromY: number,
        toX: number,
        toY: number,
    ): void {
        const angle = Math.atan2(toY - fromY, toX - fromX);
        const size = 7;
        ctx.setLineDash([]);
        ctx.beginPath();
        ctx.moveTo(toX, toY);
        ctx.lineTo(toX - size * Math.cos(angle - 0.4), toY - size * Math.sin(angle - 0.4));
        ctx.moveTo(toX, toY);
        ctx.lineTo(toX - size * Math.cos(angle + 0.4), toY - size * Math.sin(angle + 0.4));
        ctx.stroke();
    }
}
