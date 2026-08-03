import type { RenderContext } from '../../rendering/types';
import type { SoccerMatchState } from '../../types/simulation';
import type { ResolvedSoccerFieldGeometry } from './fieldGeometry';
import type { BallLayer } from './BallLayer';
import type { LabelsLayer } from './LabelsLayer';
import type { PlayersLayer } from './PlayersLayer';
import type { SoccerScene } from './scene';
import type { PitchTransform } from './usePitchTransform';

export interface DynamicLayerSet {
    players: Pick<PlayersLayer, 'draw'>;
    ball: Pick<BallLayer, 'draw'>;
    labels: Pick<LabelsLayer, 'draw'>;
}

/** Stable dynamic z-order: players, then ball, then labels/effects. */
export function drawDynamicSoccerLayers(
    ctx: CanvasRenderingContext2D,
    rc: RenderContext,
    scene: SoccerScene,
    state: SoccerMatchState,
    geometry: ResolvedSoccerFieldGeometry,
    transform: PitchTransform,
    layers: DynamicLayerSet,
): void {
    layers.players.draw(ctx, scene.entities.filter((entity) => entity.type === 'player'), false);
    for (const ball of scene.entities.filter((entity) => entity.type === 'ball')) {
        layers.ball.draw(ctx, ball, rc, transform.scale);
    }
    layers.labels.draw(ctx, state, geometry, transform);
}
