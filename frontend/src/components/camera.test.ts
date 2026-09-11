import { describe, it, expect } from 'vitest';

import { WORLD_HEIGHT, WORLD_WIDTH, screenPointToWorld } from './canvasGeometry';
import { getFollowViewport, FOLLOW_ZOOM as LEGACY_FOLLOW_ZOOM } from './followViewport';
import {
    DEFAULT_CAMERA,
    MAX_ZOOM,
    MIN_ZOOM,
    cameraForTarget,
    cameraScreenToWorld,
    clampCamera,
    getCameraViewport,
    isDefaultCamera,
    panByScreenDelta,
    viewFractionToWorld,
    zoomAtFraction,
    zoomByStep,
} from './camera';

const BUFFER_W = 1088;
const BUFFER_H = 612;
const RECT = { left: 0, top: 0, width: 1088, height: 612 };

describe('default camera', () => {
    it('shows the whole world', () => {
        const v = getCameraViewport(DEFAULT_CAMERA, BUFFER_W, BUFFER_H);
        expect(v.sourceX).toBeCloseTo(0);
        expect(v.sourceY).toBeCloseTo(0);
        expect(v.sourceWidth).toBeCloseTo(BUFFER_W);
        expect(v.sourceHeight).toBeCloseTo(BUFFER_H);
    });

    it('is recognised so the render loop can skip the blit', () => {
        expect(isDefaultCamera(DEFAULT_CAMERA)).toBe(true);
        expect(isDefaultCamera({ ...DEFAULT_CAMERA, zoom: 2 })).toBe(false);
        expect(isDefaultCamera({ ...DEFAULT_CAMERA, centerX: 10 })).toBe(false);
    });

    it('agrees with the existing un-zoomed screen-to-world mapping', () => {
        for (const [cx, cy] of [[0, 0], [544, 306], [1088, 612], [300, 100]]) {
            const legacy = screenPointToWorld(cx, cy, RECT, BUFFER_W, BUFFER_H);
            const camera = cameraScreenToWorld(DEFAULT_CAMERA, cx, cy, RECT);
            expect(camera.worldX).toBeCloseTo(legacy.worldX, 9);
            expect(camera.worldY).toBeCloseTo(legacy.worldY, 9);
        }
    });
});

describe('follow behaviour is preserved by the unified camera', () => {
    const targets = [
        { x: 0, y: 0, width: 40, height: 20 },
        { x: 500, y: 300, width: 40, height: 20 },
        { x: 1088, y: 612, width: 40, height: 20 },
        { x: 200, y: 580, width: 30, height: 30 },
    ];

    it('reproduces getFollowViewport exactly', () => {
        for (const t of targets) {
            const legacy = getFollowViewport(t, BUFFER_W, BUFFER_H);
            const next = getCameraViewport(cameraForTarget(t), BUFFER_W, BUFFER_H);
            expect(next.sourceX).toBeCloseTo(legacy.sourceX, 6);
            expect(next.sourceY).toBeCloseTo(legacy.sourceY, 6);
            expect(next.sourceWidth).toBeCloseTo(legacy.sourceWidth, 6);
            expect(next.sourceHeight).toBeCloseTo(legacy.sourceHeight, 6);
        }
    });

    it('uses the same follow zoom the old module published', () => {
        expect(cameraForTarget(targets[1]).zoom).toBe(LEGACY_FOLLOW_ZOOM);
    });
});

describe('clamping', () => {
    it('never shows anything outside the world', () => {
        for (const zoom of [1, 1.5, 2, 3, 6]) {
            for (const [cx, cy] of [[-5000, -5000], [5000, 5000], [0, 0]]) {
                const v = getCameraViewport(clampCamera({ zoom, centerX: cx, centerY: cy }), BUFFER_W, BUFFER_H);
                expect(v.sourceX).toBeGreaterThanOrEqual(-1e-6);
                expect(v.sourceY).toBeGreaterThanOrEqual(-1e-6);
                expect(v.sourceX + v.sourceWidth).toBeLessThanOrEqual(BUFFER_W + 1e-6);
                expect(v.sourceY + v.sourceHeight).toBeLessThanOrEqual(BUFFER_H + 1e-6);
            }
        }
    });

    it('holds zoom within range', () => {
        expect(clampCamera({ ...DEFAULT_CAMERA, zoom: 0.01 }).zoom).toBe(MIN_ZOOM);
        expect(clampCamera({ ...DEFAULT_CAMERA, zoom: 999 }).zoom).toBe(MAX_ZOOM);
    });

    it('re-centres at zoom 1 however far the centre was dragged', () => {
        const c = clampCamera({ zoom: 1, centerX: 0, centerY: 0 });
        expect(c.centerX).toBeCloseTo(WORLD_WIDTH / 2);
        expect(c.centerY).toBeCloseTo(WORLD_HEIGHT / 2);
    });
});

describe('zooming at the cursor', () => {
    it('keeps the world point under the cursor fixed away from the edges', () => {
        const start = { zoom: 1.2, centerX: WORLD_WIDTH / 2, centerY: WORLD_HEIGHT / 2 };
        const fx = 0.6;
        const fy = 0.45;
        const before = viewFractionToWorld(start, fx, fy);
        const after = viewFractionToWorld(zoomAtFraction(start, 2.4, fx, fy), fx, fy);
        expect(after.worldX).toBeCloseTo(before.worldX, 6);
        expect(after.worldY).toBeCloseTo(before.worldY, 6);
    });

    it('still produces a legal view when zooming at a corner', () => {
        const zoomed = zoomAtFraction(DEFAULT_CAMERA, 4, 0, 0);
        const v = getCameraViewport(zoomed, BUFFER_W, BUFFER_H);
        expect(v.sourceX).toBeCloseTo(0, 6);
        expect(v.sourceY).toBeCloseTo(0, 6);
        expect(zoomed.zoom).toBe(4);
    });

    it('zooming out to 1 returns the whole world regardless of where it was', () => {
        const wandered = clampCamera({ zoom: 5, centerX: 100, centerY: 80 });
        expect(isDefaultCamera(zoomAtFraction(wandered, 1, 0.2, 0.9))).toBe(true);
    });

    it('steps zoom about the centre', () => {
        expect(zoomByStep(DEFAULT_CAMERA, 2).zoom).toBe(2);
        expect(zoomByStep({ ...DEFAULT_CAMERA, zoom: 4 }, 0.5).zoom).toBe(2);
    });
});

describe('panning', () => {
    it('moves the world with the pointer', () => {
        const start = clampCamera({ zoom: 3, centerX: WORLD_WIDTH / 2, centerY: WORLD_HEIGHT / 2 });
        // Dragging right reveals what was to the left, so the centre moves left.
        const panned = panByScreenDelta(start, 100, 0, RECT.width, RECT.height);
        expect(panned.centerX).toBeLessThan(start.centerX);
    });

    it('scales the drag so a pixel of cursor is a pixel of world', () => {
        const start = clampCamera({ zoom: 2, centerX: WORLD_WIDTH / 2, centerY: WORLD_HEIGHT / 2 });
        const panned = panByScreenDelta(start, 50, 0, RECT.width, RECT.height);
        // At zoom 2 the view spans half the world across the full rect width.
        const expected = 50 * (WORLD_WIDTH / 2) / RECT.width;
        expect(start.centerX - panned.centerX).toBeCloseTo(expected, 6);
    });

    it('cannot be dragged out of the world', () => {
        let camera = clampCamera({ zoom: 2, centerX: WORLD_WIDTH / 2, centerY: WORLD_HEIGHT / 2 });
        for (let i = 0; i < 50; i += 1) {
            camera = panByScreenDelta(camera, 400, 400, RECT.width, RECT.height);
        }
        const v = getCameraViewport(camera, BUFFER_W, BUFFER_H);
        expect(v.sourceX).toBeGreaterThanOrEqual(-1e-6);
        expect(v.sourceY).toBeGreaterThanOrEqual(-1e-6);
    });

    it('is inert at zoom 1, where there is nothing to pan to', () => {
        const panned = panByScreenDelta(DEFAULT_CAMERA, 300, 200, RECT.width, RECT.height);
        expect(isDefaultCamera(panned)).toBe(true);
    });

    it('survives a zero-sized rect without producing NaN', () => {
        const panned = panByScreenDelta(DEFAULT_CAMERA, 10, 10, 0, 0);
        expect(Number.isFinite(panned.centerX)).toBe(true);
        expect(Number.isFinite(panned.centerY)).toBe(true);
    });
});

describe('hit testing round-trips', () => {
    it('maps a screen point to world and back to the same fraction', () => {
        const camera = clampCamera({ zoom: 2.5, centerX: 400, centerY: 250 });
        const v = getCameraViewport(camera, BUFFER_W, BUFFER_H);
        const { worldX, worldY } = cameraScreenToWorld(camera, 300, 200, RECT);
        // Re-project: world -> buffer -> source rect -> screen fraction.
        const bufferX = worldX * (BUFFER_W / WORLD_WIDTH);
        const bufferY = worldY * (BUFFER_H / WORLD_HEIGHT);
        const fx = (bufferX - v.sourceX) / v.sourceWidth;
        const fy = (bufferY - v.sourceY) / v.sourceHeight;
        expect(fx * RECT.width).toBeCloseTo(300, 6);
        expect(fy * RECT.height).toBeCloseTo(200, 6);
    });
});
