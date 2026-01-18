import React, { useEffect, useRef, type CSSProperties } from 'react';
import { SoccerTopDownRenderer } from '../renderers/soccer/SoccerTopDownRenderer';
import type { SoccerMatchState } from '../types/simulation';
import type { RenderContext, RenderFrame } from '../rendering/types';

export interface SoccerPitchProps {
    gameState: SoccerMatchState | null;
    width?: number;
    height?: number;
    style?: CSSProperties;
}

export const SoccerPitch: React.FC<SoccerPitchProps> = ({ gameState, width = 800, height = 450, style }) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const rendererRef = useRef<SoccerTopDownRenderer | null>(null);

    useEffect(() => {
        rendererRef.current = new SoccerTopDownRenderer();
        return () => rendererRef.current?.dispose();
    }, []);

    useEffect(() => {
        if (!rendererRef.current || !canvasRef.current || !gameState) return;

        const ctx = canvasRef.current.getContext('2d');
        if (!ctx) return;

        const viewMode =
            gameState.view_mode === 'side' || gameState.view_mode === 'topdown'
                ? gameState.view_mode
                : 'topdown';

        const frame: RenderFrame = {
            worldType: 'soccer',
            viewMode: 'topdown',
            snapshot: gameState,
            options: {
                viewMode,
            }
        };

        const rc: RenderContext = {
            ctx,
            canvas: canvasRef.current,
            dpr: window.devicePixelRatio || 1,
            nowMs: performance.now(),
        };

        rendererRef.current.render(frame, rc);

    }, [gameState]);

    return (
        <canvas
            ref={canvasRef}
            width={width}
            height={height}
            className="rounded-lg shadow-lg"
            style={{
                background: '#2e9a30',
                width: '100%',
                maxWidth: `${width}px`,
                height: 'auto',
                display: 'block',
                margin: '0 auto',
                ...style,
            }}
        />
    );
};
