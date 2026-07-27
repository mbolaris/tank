/**
 * A recording `CanvasRenderingContext2D` for behaviour-preserving renderer work.
 *
 * Canvas code has no return value to assert on, which is why the renderers have
 * historically been tested by asserting on arithmetic copied out of them. This
 * records the exact sequence of drawing calls, state assignments and gradient
 * colour stops a renderer emits, so a refactor can be proven byte-identical
 * against a committed snapshot instead of re-derived by eye.
 *
 * Only used by tests; it is deliberately not exported from `renderers/index`.
 */

/** Methods recorded verbatim (name + arguments) in call order. */
const RECORDED_METHODS = [
    'save',
    'restore',
    'translate',
    'scale',
    'rotate',
    'beginPath',
    'closePath',
    'moveTo',
    'lineTo',
    'arc',
    'ellipse',
    'rect',
    'roundRect',
    'quadraticCurveTo',
    'bezierCurveTo',
    'fill',
    'stroke',
    'clip',
    'fillRect',
    'strokeRect',
    'clearRect',
    'setLineDash',
    'fillText',
    'strokeText',
    'drawImage',
    'setTransform',
    'transform',
] as const;

/** Mutable state properties recorded on assignment. */
const RECORDED_PROPERTIES = [
    'fillStyle',
    'strokeStyle',
    'lineWidth',
    'lineCap',
    'lineJoin',
    'globalAlpha',
    'globalCompositeOperation',
    'font',
    'textAlign',
    'textBaseline',
    'shadowColor',
    'shadowBlur',
    'shadowOffsetX',
    'shadowOffsetY',
] as const;

/**
 * Numbers are formatted at full precision so a one-ULP change in any drawing
 * arithmetic shows up as a snapshot diff. `-0` is normalised to `0` because the
 * two are indistinguishable on a real canvas but not in a string diff.
 */
function formatArg(value: unknown): string {
    if (typeof value === 'number') {
        return Object.is(value, -0) ? '0' : String(value);
    }
    if (typeof value === 'string') return JSON.stringify(value);
    if (value === null || value === undefined) return String(value);
    if (Array.isArray(value)) return `[${value.map(formatArg).join(',')}]`;
    if (typeof value === 'object') {
        const tag = (value as { __traceTag?: string }).__traceTag;
        if (tag) return tag;
        return '<object>';
    }
    return String(value);
}

export interface CanvasTrace {
    /** The recorded operations, one per line, in emission order. */
    readonly ops: string[];
    /** The recording context to hand to a renderer. */
    readonly ctx: CanvasRenderingContext2D;
    /** A canvas stub sized for `RenderContext`. */
    readonly canvas: HTMLCanvasElement;
    /** Snapshot-friendly rendering of the trace. */
    toString(): string;
    reset(): void;
}

interface TraceGradient {
    __traceTag: string;
    addColorStop(offset: number, color: string): void;
}

/**
 * Build a recording context. `width`/`height` size the canvas stub, which the
 * renderers read to compute their world-to-screen transform.
 */
export function createCanvasTrace(width = 800, height = 600): CanvasTrace {
    const ops: string[] = [];
    let gradientCount = 0;

    const record = (line: string) => {
        ops.push(line);
    };

    const makeGradient = (kind: string, args: number[]): TraceGradient => {
        const tag = `${kind}#${gradientCount++}`;
        record(`${kind}(${args.map(formatArg).join(',')}) -> ${tag}`);
        return {
            __traceTag: tag,
            addColorStop(offset: number, color: string) {
                record(`${tag}.addColorStop(${formatArg(offset)},${formatArg(color)})`);
            },
        };
    };

    const target: Record<string, unknown> = {
        canvas: undefined,
        createLinearGradient: (...args: number[]) => makeGradient('createLinearGradient', args),
        createRadialGradient: (...args: number[]) => makeGradient('createRadialGradient', args),
        createPattern: () => null,
        measureText: (text: string) => {
            record(`measureText(${formatArg(text)})`);
            // Deterministic stand-in: real metrics depend on the font backend.
            return { width: text.length * 6 };
        },
        getLineDash: () => [],
        getImageData: () => ({ data: new Uint8ClampedArray(4) }),
        putImageData: () => undefined,
        createImageData: () => ({ data: new Uint8ClampedArray(4) }),
    };

    for (const name of RECORDED_METHODS) {
        target[name] = (...args: unknown[]) => {
            record(`${name}(${args.map(formatArg).join(',')})`);
        };
    }

    for (const name of RECORDED_PROPERTIES) {
        target[name] = undefined;
    }

    const propertyNames = new Set<string>(RECORDED_PROPERTIES);

    const ctx = new Proxy(target, {
        set(obj, prop, value) {
            if (typeof prop === 'string' && propertyNames.has(prop)) {
                record(`${prop} = ${formatArg(value)}`);
            }
            obj[prop as string] = value;
            return true;
        },
    }) as unknown as CanvasRenderingContext2D;

    const canvas = { width, height, getContext: () => ctx } as unknown as HTMLCanvasElement;
    target.canvas = canvas;

    return {
        ops,
        ctx,
        canvas,
        toString: () => ops.join('\n'),
        reset: () => {
            ops.length = 0;
            gradientCount = 0;
        },
    };
}
