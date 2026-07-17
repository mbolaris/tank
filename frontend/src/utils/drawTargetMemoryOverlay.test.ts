/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, expect, it, vi } from 'vitest';
import { drawTargetMemoryOverlay } from './drawTargetMemoryOverlay';
import type { TargetMemoryOverlayData } from '../rendering/types';

describe('drawTargetMemoryOverlay', () => {
    const createMockCtx = () => {
        return {
            save: vi.fn(),
            restore: vi.fn(),
            beginPath: vi.fn(),
            arc: vi.fn(),
            stroke: vi.fn(),
            fill: vi.fn(),
            moveTo: vi.fn(),
            lineTo: vi.fn(),
            translate: vi.fn(),
            rotate: vi.fn(),
            closePath: vi.fn(),
            setLineDash: vi.fn(),
            strokeStyle: '',
            fillStyle: '',
            lineWidth: 1,
        };
    };

    it('draws food target memory overlay with confidence decay and dash/fill patterns', () => {
        const ctx = createMockCtx() as any;
        const overlay: TargetMemoryOverlayData = {
            domain: 'food',
            action: 'Continue',
            lastSeenPosition: [100, 150],
            predictedPosition: [120, 160],
            searchVector: [20, 10],
            confidence: 0.8,
            recentEvent: null,
        };

        drawTargetMemoryOverlay(ctx, 50, 50, overlay);

        // Verify save and restore were called
        expect(ctx.save).toHaveBeenCalled();
        expect(ctx.restore).toHaveBeenCalled();

        // Canvas context should be updated with appropriate styles
        expect(ctx.strokeStyle).toContain('rgba');
        expect(ctx.setLineDash).toHaveBeenCalled();
        expect(ctx.arc).toHaveBeenCalled();
        expect(ctx.moveTo).toHaveBeenCalled();
        expect(ctx.lineTo).toHaveBeenCalled();
    });

    it('draws ripple/flash animations for recent SWITCH/ACQUIRE events within age limit', () => {
        const ctx = createMockCtx() as any;
        const overlay: TargetMemoryOverlayData = {
            domain: 'ball',
            action: 'Switch',
            lastSeenPosition: [200, 200],
            predictedPosition: [220, 220],
            searchVector: [20, 20],
            confidence: 1.0,
            recentEvent: {
                domain: 'ball',
                action: 'switch',
                ageFrames: 10,
            },
        };

        drawTargetMemoryOverlay(ctx, 100, 100, overlay);

        // We expect additional arc and stroke calls to render the ripples
        expect(ctx.arc).toHaveBeenCalled();
        expect(ctx.stroke).toHaveBeenCalled();
    });

    it('uses different colors for food and ball domains', () => {
        const ctxFood = createMockCtx() as any;
        const overlayFood: TargetMemoryOverlayData = {
            domain: 'food',
            action: 'Continue',
            lastSeenPosition: [100, 100],
            predictedPosition: [100, 100],
            searchVector: [0, 0],
            confidence: 1.0,
            recentEvent: null,
        };

        drawTargetMemoryOverlay(ctxFood, 50, 50, overlayFood);
        const foodStrokeColor = ctxFood.strokeStyle;

        const ctxBall = createMockCtx() as any;
        const overlayBall: TargetMemoryOverlayData = {
            domain: 'ball',
            action: 'Continue',
            lastSeenPosition: [100, 100],
            predictedPosition: [100, 100],
            searchVector: [0, 0],
            confidence: 1.0,
            recentEvent: null,
        };

        drawTargetMemoryOverlay(ctxBall, 50, 50, overlayBall);
        const ballStrokeColor = ctxBall.strokeStyle;

        // Food and Ball should not use the same base color
        expect(foodStrokeColor).not.toBe(ballStrokeColor);
    });
});
