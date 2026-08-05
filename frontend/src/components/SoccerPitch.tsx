import React, { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import { SoccerTopDownRenderer } from '../renderers/soccer/SoccerTopDownRenderer';
import type { SoccerMatchState } from '../types/simulation';
import type { RenderContext, RenderFrame, SoccerTacticalOptions } from '../rendering/types';
import { calculatePitchViewport, resolvePitchMaxWidth, type PitchViewportSize } from './pitchViewport';
import { useMatchAnimator } from './useMatchAnimator';

const FALLBACK_GEOMETRY = { length: 105, width: 68 };

/** Fallback CSS width used only before the host has been measured. */
const UNMEASURED_WIDTH = 800;

export interface SoccerPitchProps {
    gameState: SoccerMatchState | null;
    /**
     * Explicit fixed viewport width. Legacy panels pass this and keep their
     * existing size; it also acts as the visual cap unless `maxWidth` overrides
     * it, so no embedded pitch silently becomes unbounded.
     */
    width?: number;
    /** Explicit fixed viewport height. Only used to seed the pre-geometry aspect. */
    height?: number;
    /** Optional visual cap, independent of a fixed viewport. */
    maxWidth?: number;
    /**
     * Tactical annotations (§4.1). Absent or `enabled: false` renders the
     * Broadcast pitch, unchanged.
     *
     * Note that this never affects the pitch *box*: the canvas is sized from
     * the host width and the field aspect in both modes, so switching modes
     * cannot re-fit or jump the pitch (§7).
     */
    tactical?: SoccerTacticalOptions | null;
    style?: CSSProperties;
}

export const SoccerPitch: React.FC<SoccerPitchProps> = ({ gameState, width, height, maxWidth, tactical, style }) => {
    const hostRef = useRef<HTMLDivElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const rendererRef = useRef<SoccerTopDownRenderer | null>(null);
    const animatedState = useMatchAnimator(gameState);
    const cap = resolvePitchMaxWidth(width, maxWidth);
    // Real field geometry always wins. Legacy width/height only seed the aspect
    // for the frames before a match state arrives. Memoised on the *values*:
    // every websocket payload brings a fresh geometry object, and re-running the
    // measuring effect on each one would resubscribe ResizeObserver 10x/second.
    const fieldLength = gameState?.geometry?.length;
    const fieldWidth = gameState?.geometry?.width;
    const geometry = useMemo(() => {
        if (fieldLength !== undefined && fieldWidth !== undefined) {
            return { length: fieldLength, width: fieldWidth };
        }
        if (width !== undefined && height !== undefined) return { length: width, width: height };
        return FALLBACK_GEOMETRY;
    }, [fieldLength, fieldWidth, width, height]);
    const [viewport, setViewport] = useState<PitchViewportSize>(() =>
        calculatePitchViewport(width ?? UNMEASURED_WIDTH, geometry, cap ?? width ?? UNMEASURED_WIDTH, 1),
    );

    useEffect(() => {
        const host = hostRef.current;
        if (!host) return;

        const measure = () => {
            // clientWidth is 0 while the host is detached or display:none.
            const hostWidth = host.clientWidth || width || UNMEASURED_WIDTH;
            const next = calculatePitchViewport(
                hostWidth,
                geometry,
                cap ?? hostWidth,
                window.devicePixelRatio || 1,
            );
            // Bailing out on an unchanged viewport keeps ResizeObserver from
            // looping: setState -> re-render -> observed resize -> setState.
            setViewport((current) =>
                current.width === next.width && current.height === next.height && current.dpr === next.dpr
                    ? current
                    : next,
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
    }, [geometry, width, cap]);

    useEffect(() => {
        rendererRef.current = new SoccerTopDownRenderer();
        return () => rendererRef.current?.dispose();
    }, []);

    useEffect(() => {
        if (!rendererRef.current || !canvasRef.current || !animatedState) return;

        const ctx = canvasRef.current.getContext('2d');
        if (!ctx) return;

        const viewMode =
            animatedState.view_mode === 'side' || animatedState.view_mode === 'topdown'
                ? animatedState.view_mode
                : 'topdown';

        const frame: RenderFrame = {
            worldType: 'soccer',
            viewMode: 'topdown',
            snapshot: animatedState,
            options: {
                viewMode,
                soccerTactical: tactical ?? null,
            }
        };

        const rc: RenderContext = {
            ctx,
            canvas: canvasRef.current,
            dpr: viewport.dpr,
            nowMs: performance.now(),
        };

        rendererRef.current.render(frame, rc);

    }, [animatedState, viewport, tactical]);

    return (
        <div
            ref={hostRef}
            className="rounded-lg shadow-lg"
            data-testid="soccer-pitch-host"
            style={{
                width: '100%',
                // Uncapped only when the caller passed neither a fixed width nor
                // an explicit cap, i.e. deliberately asked to be responsive.
                maxWidth: cap !== undefined ? `${cap}px` : undefined,
                // The pitch stays landscape at every breakpoint: the aspect comes
                // from the real field, so a compact screen gets a shorter,
                // full-width pitch rather than a rotated one.
                aspectRatio: `${geometry.length}/${geometry.width}`,
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
