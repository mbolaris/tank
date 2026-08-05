/** Soccer renderer: static pitch plus an rAF-driven dynamic scene. */

import type { RenderContext, RenderFrame, Renderer } from '../../rendering/types';
import { clearAvatarPathCache } from '../avatar_renderer';
import { resolveSoccerGeometry, soccerMatchSnapshot, type ResolvedSoccerFieldGeometry } from './fieldGeometry';
import { BallLayer } from './BallLayer';
import { LabelsLayer } from './LabelsLayer';
import { PassLinesLayer } from './PassLinesLayer';
import { PlayersLayer } from './PlayersLayer';
import { TrailsLayer } from './TrailsLayer';
import { drawDynamicSoccerLayers } from './DynamicLayers';
import { soccerSceneFromFrame } from './scene';
import { sidesAreSwapped } from './sideAssignment';
import { StaticFieldLayer } from './StaticFieldLayer';
import { usePitchTransform, type PitchTransform } from './usePitchTransform';

export class SoccerTopDownRenderer implements Renderer {
    id = 'soccer-topdown';
    private readonly staticFieldLayer = new StaticFieldLayer();
    private readonly playersLayer = new PlayersLayer();
    private readonly ballLayer = new BallLayer();
    private readonly labelsLayer = new LabelsLayer();
    private readonly trailsLayer = new TrailsLayer();
    private readonly passLinesLayer = new PassLinesLayer();

    dispose(): void {
        clearAvatarPathCache();
        this.trailsLayer.clear();
        this.passLinesLayer.clear();
    }

    render(frame: RenderFrame, rc: RenderContext): void {
        const { ctx, canvas } = rc;
        const geometry = resolveSoccerGeometry(frame.snapshot);
        // This is a pure metres-to-pixels transform, not a React hook.
        // eslint-disable-next-line react-hooks/rules-of-hooks
        const transform = usePitchTransform(
            geometry,
            { width: canvas.width, height: canvas.height },
            20 * Math.max(rc.dpr, 1),
        );

        if (frame.options?.showSoccer ?? true) {
            this.staticFieldLayer.draw(ctx, geometry, transform);
        } else {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#071c22';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            this.drawFieldOutline(ctx, geometry, transform);
        }

        const scene = soccerSceneFromFrame(frame, transform);
        const players = scene.entities.filter((entity) => entity.type === 'player');
        const balls = scene.entities.filter((entity) => entity.type === 'ball');
        const state = soccerMatchSnapshot(frame.snapshot);
        const tactical = frame.options?.soccerTactical ?? null;

        if (tactical?.enabled) {
            // Both layers dedupe by match frame internally, so the rAF loop can
            // call them at display cadence without over-sampling. They also need
            // the swap: half time mirrors every position without changing the
            // match id or rewinding the frame, so it is invisible to their other
            // reset guards.
            const swapped = sidesAreSwapped(state);
            this.trailsLayer.record(players, state.frame, state.match_id ?? null, swapped);
            this.passLinesLayer.observe(players, state.ball_owner, state.frame, state.match_id ?? null, swapped);
        } else if (this.trailsLayer.size) {
            // Leaving Tactical drops the history rather than freezing it: a trail
            // resumed after a minute in Broadcast would splice together two
            // disconnected stretches of play into one continuous-looking path.
            this.trailsLayer.clear();
            this.passLinesLayer.clear();
        }

        drawDynamicSoccerLayers(
            ctx,
            rc,
            { entities: [...players, ...balls] },
            state,
            geometry,
            transform,
            {
                players: this.playersLayer,
                ball: this.ballLayer,
                labels: this.labelsLayer,
                trails: this.trailsLayer,
                passLines: this.passLinesLayer,
            },
            tactical,
        );
    }

    private drawFieldOutline(
        ctx: CanvasRenderingContext2D,
        geometry: ResolvedSoccerFieldGeometry,
        transform: PitchTransform,
    ): void {
        const [left, top] = transform.toScreen(-geometry.length / 2, -geometry.width / 2);
        const [right, bottom] = transform.toScreen(geometry.length / 2, geometry.width / 2);
        ctx.strokeStyle = 'rgba(241, 248, 244, 0.25)';
        ctx.lineWidth = Math.max(1, 1.5 * transform.scale / Math.max(transform.scale, 1));
        ctx.strokeRect(left, top, right - left, bottom - top);
    }
}
