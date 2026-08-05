import type { RenderContext, SoccerTacticalOptions } from '../../rendering/types';
import type { SoccerMatchState } from '../../types/simulation';
import type { ResolvedSoccerFieldGeometry } from './fieldGeometry';
import type { BallLayer } from './BallLayer';
import type { LabelsLayer } from './LabelsLayer';
import type { PassLinesLayer } from './PassLinesLayer';
import type { PlayersLayer } from './PlayersLayer';
import type { SoccerScene } from './scene';
import type { TrailsLayer } from './TrailsLayer';
import type { PitchTransform } from './usePitchTransform';

export interface DynamicLayerSet {
    players: Pick<PlayersLayer, 'draw'>;
    ball: Pick<BallLayer, 'draw'>;
    labels: Pick<LabelsLayer, 'draw'>;
    trails?: Pick<TrailsLayer, 'draw'>;
    passLines?: Pick<PassLinesLayer, 'draw'>;
}

/**
 * Stable dynamic z-order (§6.3): trails and pass lines, then players, then the
 * ball, then labels/effects. Tactical annotations sit *under* the players so
 * they never obscure the thing they annotate, and the ball is never behind a
 * player.
 */
export function drawDynamicSoccerLayers(
    ctx: CanvasRenderingContext2D,
    rc: RenderContext,
    scene: SoccerScene,
    state: SoccerMatchState,
    geometry: ResolvedSoccerFieldGeometry,
    transform: PitchTransform,
    layers: DynamicLayerSet,
    tactical?: SoccerTacticalOptions | null,
): void {
    const players = scene.entities.filter((entity) => entity.type === 'player');
    if (tactical?.enabled) {
        layers.trails?.draw(ctx, players, transform, tactical.selectedParticipantId ?? undefined);
        layers.passLines?.draw(ctx, state.frame, transform);
    }
    layers.players.draw(ctx, players, false, tactical);
    for (const ball of scene.entities.filter((entity) => entity.type === 'ball')) {
        layers.ball.draw(ctx, ball, rc, transform.scale);
    }
    layers.labels.draw(ctx, state, geometry, transform);
}
