import { useCallback, useEffect, useRef, useState, type RefObject } from 'react';

import { DEFAULT_CAMERA, panByScreenDelta, zoomAtFraction, type Camera } from './camera';

/** Pointer travel before a press counts as a pan rather than a click. */
const PAN_THRESHOLD_PX = 4;
/** Wheel delta -> zoom factor, via exp() so trackpads and mice both feel linear. */
const WHEEL_ZOOM_SENSITIVITY = 0.0015;

interface CameraInteractions {
    camera: Camera;
    cameraRef: RefObject<Camera>;
    applyCamera: (next: (previous: Camera) => Camera) => void;
    resetCamera: () => void;
    /** Begin a potential pan. Call from mousedown; ignores anything but the left button. */
    beginPan: (event: { button: number; clientX: number; clientY: number }) => void;
    /** True when the last press actually moved the view, so its click is not a selection. */
    consumePanFlag: () => boolean;
}

/** Wheel-to-zoom and drag-to-pan over a canvas.
 *
 * `disabled` is for when something else owns the camera — following a fish —
 * where free look should stand down rather than fight it.
 */
export function useCameraInteractions(
    canvasRef: RefObject<HTMLCanvasElement | null>,
    disabled: boolean,
): CameraInteractions {
    const [camera, setCamera] = useState<Camera>(DEFAULT_CAMERA);
    const cameraRef = useRef(camera);
    const panOriginRef = useRef<{ x: number; y: number } | null>(null);
    // A drag that moved is a pan, not a click; without this, releasing after
    // dragging the view would also select whatever ended up under the cursor.
    const didPanRef = useRef(false);

    useEffect(() => {
        cameraRef.current = camera;
    }, [camera]);

    const applyCamera = useCallback((next: (previous: Camera) => Camera) => {
        setCamera((previous) => next(previous));
    }, []);

    const resetCamera = useCallback(() => setCamera(DEFAULT_CAMERA), []);

    const beginPan = useCallback(
        (event: { button: number; clientX: number; clientY: number }) => {
            if (disabled || event.button !== 0) return;
            panOriginRef.current = { x: event.clientX, y: event.clientY };
            didPanRef.current = false;
        },
        [disabled],
    );

    const consumePanFlag = useCallback(() => {
        if (!didPanRef.current) return false;
        didPanRef.current = false;
        return true;
    }, []);

    // Panning tracks the window rather than the canvas: a drag that leaves the
    // tank should keep panning until the button comes up, not stick halfway.
    useEffect(() => {
        const onMove = (event: MouseEvent) => {
            const origin = panOriginRef.current;
            const canvas = canvasRef.current;
            if (!origin || !canvas) return;
            const dx = event.clientX - origin.x;
            const dy = event.clientY - origin.y;
            if (!didPanRef.current && Math.hypot(dx, dy) < PAN_THRESHOLD_PX) return;
            didPanRef.current = true;
            panOriginRef.current = { x: event.clientX, y: event.clientY };
            const rect = canvas.getBoundingClientRect();
            applyCamera((previous) => panByScreenDelta(previous, dx, dy, rect.width, rect.height));
        };
        const onUp = () => {
            panOriginRef.current = null;
        };
        window.addEventListener('mousemove', onMove);
        window.addEventListener('mouseup', onUp);
        return () => {
            window.removeEventListener('mousemove', onMove);
            window.removeEventListener('mouseup', onUp);
        };
    }, [applyCamera, canvasRef]);

    // Wheel zoom needs a non-passive listener to stop the page scrolling, which
    // React's onWheel cannot guarantee.
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const onWheel = (event: WheelEvent) => {
            if (disabled) return;
            event.preventDefault();
            const rect = canvas.getBoundingClientRect();
            if (rect.width <= 0 || rect.height <= 0) return;
            const factor = Math.exp(-event.deltaY * WHEEL_ZOOM_SENSITIVITY);
            applyCamera((previous) =>
                zoomAtFraction(
                    previous,
                    previous.zoom * factor,
                    (event.clientX - rect.left) / rect.width,
                    (event.clientY - rect.top) / rect.height,
                ),
            );
        };
        canvas.addEventListener('wheel', onWheel, { passive: false });
        return () => canvas.removeEventListener('wheel', onWheel);
    }, [applyCamera, canvasRef, disabled]);

    return { camera, cameraRef, applyCamera, resetCamera, beginPan, consumePanFlag };
}
