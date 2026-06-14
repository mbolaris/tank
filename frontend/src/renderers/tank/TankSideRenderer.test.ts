import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { TankSideRenderer } from './TankSideRenderer';

const rendererMocks = vi.hoisted(() => ({
    clear: vi.fn(),
    dispose: vi.fn(),
    pruneEntityFacingCache: vi.fn(),
    prunePlantCaches: vi.fn(),
    renderEntity: vi.fn(),
}));

vi.mock('../../utils/renderer', () => ({
    Renderer: class {
        clear = rendererMocks.clear;
        dispose = rendererMocks.dispose;
        pruneEntityFacingCache = rendererMocks.pruneEntityFacingCache;
        prunePlantCaches = rendererMocks.prunePlantCaches;
        renderEntity = rendererMocks.renderEntity;
    },
}));

describe('TankSideRenderer', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it('prunes caches once per entity snapshot instead of once per animation frame', () => {
        const renderer = new TankSideRenderer();
        const entities = [
            { id: 1, type: 'fish', x: 10, y: 10, width: 20, height: 10 },
            { id: 2, type: 'plant', x: 30, y: 30, width: 10, height: 20 },
        ];
        const frame = {
            worldType: 'tank',
            viewMode: 'side',
            snapshot: {
                snapshot: {
                    entities,
                    stats: {},
                    elapsed_time: 0,
                },
            },
        };
        const ctx = {
            restore: vi.fn(),
            save: vi.fn(),
            scale: vi.fn(),
        };
        const renderContext = {
            canvas: { width: 1088, height: 612 },
            ctx,
            dpr: 1,
            nowMs: 0,
        };

        renderer.render(frame as never, renderContext as never);
        renderer.render(frame as never, renderContext as never);

        expect(rendererMocks.pruneEntityFacingCache).toHaveBeenCalledTimes(1);
        expect(rendererMocks.prunePlantCaches).toHaveBeenCalledTimes(1);

        frame.snapshot.snapshot.entities = [...entities];
        renderer.render(frame as never, renderContext as never);

        expect(rendererMocks.pruneEntityFacingCache).toHaveBeenCalledTimes(2);
        expect(rendererMocks.prunePlantCaches).toHaveBeenCalledTimes(2);
    });

    it('renders moving entities every frame while refreshing the plant layer at 15 Hz', () => {
        const layerCtx = {
            clearRect: vi.fn(),
        };
        vi.stubGlobal('document', {
            createElement: vi.fn(() => ({
                width: 0,
                height: 0,
                getContext: vi.fn(() => layerCtx),
            })),
        });

        const renderer = new TankSideRenderer();
        const entities = [
            { id: 1, type: 'fish', x: 10, y: 10, width: 20, height: 10 },
            { id: 2, type: 'plant', x: 30, y: 30, width: 10, height: 20 },
        ];
        const frame = {
            worldType: 'tank',
            viewMode: 'side',
            snapshot: {
                snapshot: {
                    entities,
                    stats: {},
                    elapsed_time: 0,
                },
            },
        };
        const ctx = {
            drawImage: vi.fn(),
            restore: vi.fn(),
            save: vi.fn(),
            scale: vi.fn(),
        };
        const renderContext = {
            canvas: { width: 1088, height: 612 },
            ctx,
            dpr: 1,
            nowMs: 0,
        };

        renderer.render(frame as never, renderContext as never);
        renderContext.nowMs = 16;
        renderer.render(frame as never, renderContext as never);
        renderContext.nowMs = 70;
        renderer.render(frame as never, renderContext as never);

        const renderedTypes = rendererMocks.renderEntity.mock.calls.map(([entity]) => entity.type);
        expect(renderedTypes.filter(type => type === 'fish')).toHaveLength(3);
        expect(renderedTypes.filter(type => type === 'plant')).toHaveLength(2);
        expect(ctx.drawImage).toHaveBeenCalledTimes(3);
    });
});
