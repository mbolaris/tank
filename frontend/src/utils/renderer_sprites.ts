/**
 * Sprite/image drawing helpers: plain and hue-tinted image blits, HSL color
 * conversion, and sprite animation frame selection. Extracted from
 * utils/renderer.ts (god-class ratchet harvest); behavior is unchanged.
 */

// Animation constants
const IMAGE_CHANGE_RATE = 500; // milliseconds

export function getAnimationFrame(elapsedTime: number, frameCount: number): number {
    if (frameCount <= 1) return 0;
    return Math.floor(elapsedTime / IMAGE_CHANGE_RATE) % frameCount;
}

export function hslToRgb(h: number, s: number, l: number): [number, number, number] {
    let r: number, g: number, b: number;

    if (s === 0) {
        r = g = b = l;
    } else {
        const hue2rgb = (p: number, q: number, t: number) => {
            if (t < 0) t += 1;
            if (t > 1) t -= 1;
            if (t < 1 / 6) return p + (q - p) * 6 * t;
            if (t < 1 / 2) return q;
            if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
            return p;
        };

        const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
        const p = 2 * l - q;
        r = hue2rgb(p, q, h + 1 / 3);
        g = hue2rgb(p, q, h);
        b = hue2rgb(p, q, h - 1 / 3);
    }

    return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)];
}

export function hslToRgbString(h: number, s: number, l: number): string {
    const rgb = hslToRgb(h, s, l);
    return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
}

export function drawImage(
    ctx: CanvasRenderingContext2D,
    image: HTMLImageElement,
    x: number,
    y: number,
    width: number,
    height: number,
    flipHorizontal: boolean
) {
    if (flipHorizontal) {
        ctx.save();
        ctx.translate(x + width, y);
        ctx.scale(-1, 1);
        ctx.drawImage(image, 0, 0, width, height);
        ctx.restore();
    } else {
        ctx.drawImage(image, x, y, width, height);
    }
}

/**
 * Owns the reusable offscreen canvas used for hue-tinting sprites, so the
 * main renderer doesn't allocate a canvas per draw call (memory pressure).
 */
export class SpriteTinter {
    private _tintCanvas: HTMLCanvasElement | null = null;
    private _tintCtx: CanvasRenderingContext2D | null = null;

    /** Dispose the offscreen canvas so GC can reclaim its backing memory. */
    dispose() {
        if (this._tintCtx) {
            // Clear canvas contents to free ImageBitmap backing if any
            try {
                this._tintCtx.canvas.width = 0;
                this._tintCtx = null;
            } catch {
                this._tintCtx = null;
            }
        }
        if (this._tintCanvas) {
            try {
                this._tintCanvas.width = 0;
            } catch {
                /* ignore */
            }
            this._tintCanvas = null;
        }
    }

    drawImageWithColorTint(
        ctx: CanvasRenderingContext2D,
        image: HTMLImageElement,
        x: number,
        y: number,
        width: number,
        height: number,
        flipHorizontal: boolean,
        colorHue: number
    ) {
        // Reuse a single offscreen canvas/context for tinting to avoid
        // allocating a new canvas on every draw call which can lead to
        // memory growth in some browsers.
        if (!this._tintCanvas) {
            this._tintCanvas = document.createElement('canvas');
        }
        if (!this._tintCtx) {
            this._tintCtx = this._tintCanvas.getContext('2d');
        }
        if (!this._tintCtx || !this._tintCanvas) return;

        const tempCtx = this._tintCtx;
        const tempCanvas = this._tintCanvas;

        // Resize offscreen canvas only when necessary to avoid frequent reallocs
        if (tempCanvas.width !== image.width || tempCanvas.height !== image.height) {
            tempCanvas.width = image.width;
            tempCanvas.height = image.height;
        }

        // Clear previous content
        tempCtx.clearRect(0, 0, tempCanvas.width, tempCanvas.height);

        // Draw original image
        if (flipHorizontal) {
            tempCtx.save();
            tempCtx.translate(tempCanvas.width, 0);
            tempCtx.scale(-1, 1);
            tempCtx.drawImage(image, 0, 0);
            tempCtx.restore();
        } else {
            tempCtx.drawImage(image, 0, 0);
        }

        // Apply color tint using multiply blend mode
        const tintColor = hslToRgb(colorHue / 360, 0.7, 0.6);
        tempCtx.globalCompositeOperation = 'multiply';
        tempCtx.fillStyle = `rgb(${tintColor[0]}, ${tintColor[1]}, ${tintColor[2]})`;
        tempCtx.fillRect(0, 0, tempCanvas.width, tempCanvas.height);

        // Restore original alpha
        tempCtx.globalCompositeOperation = 'destination-in';
        if (flipHorizontal) {
            tempCtx.save();
            tempCtx.translate(tempCanvas.width, 0);
            tempCtx.scale(-1, 1);
            tempCtx.drawImage(image, 0, 0);
            tempCtx.restore();
        } else {
            tempCtx.drawImage(image, 0, 0);
        }

        // Draw tinted image to main canvas
        ctx.drawImage(tempCanvas, x, y, width, height);
    }
}
