/**
 * Golden draw-trace tests for the top-down renderers.
 *
 * These snapshots were captured before the tank/petri/avatar renderers were
 * de-duplicated onto `renderers/shared/`, and they are the proof that the
 * extraction changed no pixels: every canvas call, state assignment and
 * gradient colour stop must come out in exactly the same order with exactly the
 * same arguments. If you intend to change how something is drawn, update the
 * snapshot in the same commit and say so — do not update it to make a red test
 * go green.
 *
 * The extraction itself produced exactly three deltas against the pre-refactor
 * capture, all reviewed and all no-ops for drawing:
 *
 *  1. Tank: 16 canvas-state assignments dropped, the setup for a `fillText`
 *     that had been commented out (a per-fish id debug label). Nothing read the
 *     state it left behind — every following draw sets its own.
 *  2. Tank: two `restore()` calls moved after the heading whisker. The whisker
 *     used to be emitted outside the entity's transform, which pinned every one
 *     of them to the world origin instead of its entity — a visible bug.
 *  3. Petri: four redundant `setLineDash([])` calls dropped. The dash was
 *     already empty at that point in every frame, as the trace itself shows.
 *
 * No coordinate, colour or gradient stop moved.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

import { createCanvasTrace } from './testing/canvasTrace';
import { buildFixtureSnapshot, FIXTURE_NOW_MS, FIXTURE_SELECTED_ID } from './testing/topDownFixture';
import { TankTopDownRenderer } from './tank/TankTopDownRenderer';
import { PetriTopDownRenderer } from './petri/PetriTopDownRenderer';
import { drawMicrobe } from './avatar_renderer';
import { ImageLoader } from '../utils/ImageLoader';
import { clearAllPlantCaches } from '../utils/plant';
import type { RenderFrame, RenderContext } from '../rendering/types';

/** Minimal Path2D stand-in: the L-system plant renderer caches geometry in one. */
class StubPath2D {
    moveTo() {}
    lineTo() {}
    ellipse() {}
    arc() {}
    quadraticCurveTo() {}
    bezierCurveTo() {}
    closePath() {}
    rect() {}
}

/**
 * Food avatars only draw when the sprite is already in the image cache, so the
 * un-stubbed trace would silently skip that branch entirely.
 */
const stubImage = { __traceTag: 'image', width: 16, height: 16 } as unknown as HTMLImageElement;

function makeFrame(): RenderFrame {
    return {
        worldType: 'tank',
        viewMode: 'topdown',
        snapshot: buildFixtureSnapshot() as unknown as RenderFrame['snapshot'],
        options: {
            showEffects: true,
            selectedEntityId: FIXTURE_SELECTED_ID,
        },
    };
}

describe('top-down renderer draw traces', () => {
    beforeEach(() => {
        vi.stubGlobal('Path2D', StubPath2D);
        vi.spyOn(ImageLoader, 'getCachedImage').mockReturnValue(stubImage);
        clearAllPlantCaches();
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        vi.restoreAllMocks();
    });

    it('TankTopDownRenderer draws the fixture world identically', () => {
        const trace = createCanvasTrace();
        const rc: RenderContext = {
            canvas: trace.canvas,
            ctx: trace.ctx,
            dpr: 1,
            nowMs: FIXTURE_NOW_MS,
        };

        new TankTopDownRenderer().render(makeFrame(), rc);

        expect(trace.ops.length).toBeGreaterThan(200);
        expect(trace.toString()).toMatchSnapshot();
    });

    it('PetriTopDownRenderer draws the fixture world identically', () => {
        const trace = createCanvasTrace();
        const rc: RenderContext = {
            canvas: trace.canvas,
            ctx: trace.ctx,
            dpr: 1,
            nowMs: FIXTURE_NOW_MS,
        };

        new PetriTopDownRenderer().render(makeFrame(), rc);

        expect(trace.ops.length).toBeGreaterThan(200);
        expect(trace.toString()).toMatchSnapshot();
    });

    it('avatar drawMicrobe draws identically', () => {
        const trace = createCanvasTrace();

        drawMicrobe(trace.ctx, 7, 14, 0.8, -0.3, {
            speed: 1,
            size: 1,
            color_hue: 0.33,
            template_id: 2,
            fin_size: 1.2,
            tail_size: 0.8,
            body_aspect: 1.1,
            eye_size: 1.3,
            pattern_intensity: 0.5,
            pattern_type: 1,
        });

        expect(trace.ops.length).toBeGreaterThan(50);
        expect(trace.toString()).toMatchSnapshot();
    });
});
