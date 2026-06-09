/**
 * Microbe avatar for poker displays in petri dish mode.
 *
 * Reuses the canvas microbe renderer (drawMicrobe) so poker avatars match
 * the organisms swimming in the dish exactly.
 */

import { useEffect, useRef } from 'react';
import type { FishGenomeData } from '../../types/simulation';
import { drawMicrobe } from '../../renderers/avatar_renderer';

interface MicrobeAvatarCanvasProps {
    fishId?: number;
    // drawMicrobe defaults every trait, so a partial genome still renders
    genomeData: Partial<FishGenomeData>;
    className?: string;
}

export function MicrobeAvatarCanvas({ fishId, genomeData, className }: MicrobeAvatarCanvasProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const size = Math.max(canvas.getBoundingClientRect().width, 1);
        const dpr = window.devicePixelRatio || 1;
        canvas.width = size * dpr;
        canvas.height = size * dpr;

        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.clearRect(0, 0, size, size);
        ctx.save();
        // Offset slightly right of center so the trailing flagellum stays visible;
        // velocity (1, 0) keeps every avatar facing the same direction.
        ctx.translate(size * 0.56, size * 0.5);
        drawMicrobe(ctx, fishId ?? 0, size * 0.3, 1, 0, genomeData as FishGenomeData);
        ctx.restore();
    }, [fishId, genomeData]);

    return (
        <canvas
            ref={canvasRef}
            className={className}
            style={{ width: '100%', height: '100%', display: 'block' }}
            aria-hidden
        />
    );
}
