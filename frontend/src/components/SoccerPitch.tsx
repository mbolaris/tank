import React, { useEffect, useRef } from 'react';
import { SoccerTopDownRenderer } from '../renderers/soccer/SoccerTopDownRenderer';

export interface SoccerPitchProps {
    gameState: any;
    width?: number;
    height?: number;
}

export const SoccerPitch: React.FC<SoccerPitchProps> = ({ gameState, width = 800, height = 450 }) => {
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

        // Mock frame for renderer
        const frame = {
            frame_count: gameState.frame || 0,
            snapshot: {
                entities: gameState.entities || []
            },
            options: {
                view_mode: gameState.view_mode || 'side'  // "side" = fish, "top" = microbe
            }
        };

        const rc = {
            ctx,
            canvas: canvasRef.current,
            width: canvasRef.current.width,
            height: canvasRef.current.height,
            deltaTime: 16,
        };

        rendererRef.current.render(frame as any, rc as any);

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
                margin: '0 auto'
            }}
        />
    );
};
