import React, { useEffect, useRef, useState, type CSSProperties } from 'react';
import { SoccerTopDownRenderer } from '../renderers/soccer/SoccerTopDownRenderer';
import type { SoccerMatchState } from '../types/simulation';
import type { RenderContext, RenderFrame } from '../rendering/types';
import { calculatePitchViewport, type PitchViewportSize } from './pitchViewport';

const FALLBACK_GEOMETRY = { length: 105, width: 68 };

export interface SoccerPitchProps {
    gameState: SoccerMatchState | null;
    width?: number;
    height?: number;
    style?: CSSProperties;
}

export const SoccerPitch: React.FC<SoccerPitchProps> = ({ gameState, width = 800, height = 450, style }) => {
    const hostRef = useRef<HTMLDivElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const rendererRef = useRef<SoccerTopDownRenderer | null>(null);
    const [viewport, setViewport] = useState<PitchViewportSize>(() =>
        calculatePitchViewport(width, { length: width, width: height }, width, 1),
    );

    useEffect(() => {
        const host = hostRef.current;
        if (!host) return;

        const measure = () => {
            setViewport(
                calculatePitchViewport(
                    host.clientWidth || width,
                    gameState?.geometry ?? FALLBACK_GEOMETRY,
                    width,
                    window.devicePixelRatio || 1,
                ),
            );
        };

        measure();
        const observer = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(measure) : null;
        observer?.observe(host);
        window.addEventListener('resize', measure);
        return () => {
            observer?.disconnect();
            window.removeEventListener('resize', measure);
        };
    }, [gameState?.geometry, width]);

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
            dpr: viewport.dpr,
            nowMs: performance.now(),
        };

        rendererRef.current.render(frame, rc);

    }, [gameState, viewport]);

    return (
        <div
            ref={hostRef}
            className="rounded-lg shadow-lg"
            style={{
                width: '100%',
                maxWidth: `${width}px`,
                aspectRatio: `${gameState?.geometry?.length ?? FALLBACK_GEOMETRY.length}/${gameState?.geometry?.width ?? FALLBACK_GEOMETRY.width}`,
                margin: '0 auto',
                ...style,
            }}
        >
            <canvas
                ref={canvasRef}
                width={Math.round(viewport.width * viewport.dpr)}
                height={Math.round(viewport.height * viewport.dpr)}
                className="rounded-lg shadow-lg"
                style={{
                    width: '100%',
                    height: '100%',
                    display: 'block',
                }}
            />
        </div>
    );
};
