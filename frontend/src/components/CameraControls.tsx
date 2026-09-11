import type { CSSProperties } from 'react';

import { DEFAULT_CAMERA, MAX_ZOOM, MIN_ZOOM, zoomByStep, type Camera } from './camera';

interface CameraControlsProps {
    camera: Camera;
    onChange: (next: (previous: Camera) => Camera) => void;
    onReset: () => void;
}

const buttonStyle: CSSProperties = {
    width: 26,
    height: 26,
    display: 'grid',
    placeItems: 'center',
    border: '1px solid rgba(148, 163, 184, 0.28)',
    borderRadius: 7,
    background: 'rgba(15, 23, 42, 0.72)',
    color: 'var(--color-text-main, #e2e8f0)',
    font: '600 14px/1 var(--font-mono, monospace)',
    cursor: 'pointer',
};

/** Zoom readout and controls, parked in the corner of the tank.
 *
 * Sits quietly until the view is actually moved: scroll-to-zoom over a canvas
 * is conventional enough to carry discovery on its own, and a permanently
 * bright control cluster over the aquarium is exactly the dashboard feel the
 * experience roadmap asks us to avoid.
 */
export function CameraControls({ camera, onChange, onReset }: CameraControlsProps) {
    const atFullView =
        camera.zoom === DEFAULT_CAMERA.zoom &&
        camera.centerX === DEFAULT_CAMERA.centerX &&
        camera.centerY === DEFAULT_CAMERA.centerY;

    return (
        <div
            style={{
                position: 'absolute',
                right: 12,
                bottom: 12,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: 5,
                borderRadius: 10,
                background: 'rgba(2, 6, 23, 0.45)',
                opacity: atFullView ? 0.45 : 1,
                transition: 'opacity 140ms ease',
            }}
            data-testid="camera-controls"
        >
            <button
                type="button"
                aria-label="Zoom out"
                style={buttonStyle}
                disabled={camera.zoom <= MIN_ZOOM}
                onClick={() => onChange((previous) => zoomByStep(previous, 1 / 1.4))}
            >
                −
            </button>
            <span
                aria-live="polite"
                style={{
                    minWidth: 42,
                    textAlign: 'center',
                    color: 'var(--color-text-dim, #94a3b8)',
                    font: '600 11px/1 var(--font-mono, monospace)',
                }}
            >
                {camera.zoom.toFixed(1)}×
            </span>
            <button
                type="button"
                aria-label="Zoom in"
                style={buttonStyle}
                disabled={camera.zoom >= MAX_ZOOM}
                onClick={() => onChange((previous) => zoomByStep(previous, 1.4))}
            >
                +
            </button>
            <button
                type="button"
                aria-label="Reset view"
                style={{ ...buttonStyle, width: 'auto', padding: '0 9px', fontSize: 11 }}
                disabled={atFullView}
                onClick={onReset}
            >
                Reset
            </button>
        </div>
    );
}
