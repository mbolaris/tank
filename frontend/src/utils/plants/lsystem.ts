import type { FractalSegment, FractalLeaf, TurtleState } from './types';
import { seededRandom } from './helpers';

/**
 * Group segments by thickness to batch render strokes on canvas.
 */
export function groupSegmentsByThickness(
    segments: FractalSegment[]
): Array<{ thickness: number; segments: FractalSegment[]; path?: Path2D }> {
    const groups = new Map<number, FractalSegment[]>();
    for (const segment of segments) {
        const group = groups.get(segment.thickness);
        if (group) {
            group.push(segment);
        } else {
            groups.set(segment.thickness, [segment]);
        }
    }
    return Array.from(groups, ([thickness, groupedSegments]) => {
        const path = createSegmentPath(groupedSegments);
        return { thickness, segments: groupedSegments, ...(path ? { path } : {}) };
    });
}

/**
 * Append segments to context path.
 */
export function appendSegments(ctx: CanvasRenderingContext2D, segments: FractalSegment[]): void {
    for (const segment of segments) {
        ctx.moveTo(segment.x1, segment.y1);
        ctx.lineTo(segment.x2, segment.y2);
    }
}

/**
 * Create Path2D for a list of segments.
 */
export function createSegmentPath(segments: FractalSegment[]): Path2D | undefined {
    if (typeof Path2D === 'undefined') return undefined;
    const path = new Path2D();
    for (const segment of segments) {
        path.moveTo(segment.x1, segment.y1);
        path.lineTo(segment.x2, segment.y2);
    }
    return path;
}

/**
 * Generate Path2D paths for leaves and veins.
 */
export function createLeafPaths(leaves: FractalLeaf[]): { leafPath?: Path2D; veinPath?: Path2D } {
    if (typeof Path2D === 'undefined') return {};
    const leafPath = new Path2D();
    const veinPath = new Path2D();
    for (const leaf of leaves) {
        const rotation = (leaf.angle * Math.PI) / 180 + Math.PI / 2;
        const centerX = leaf.x + Math.sin(rotation) * leaf.size / 2;
        const centerY = leaf.y - Math.cos(rotation) * leaf.size / 2;
        const radiusX = leaf.size * 0.4;
        const radiusY = leaf.size;
        leafPath.moveTo(
            centerX + Math.cos(rotation) * radiusX,
            centerY + Math.sin(rotation) * radiusX
        );
        leafPath.ellipse(
            centerX,
            centerY,
            radiusX,
            radiusY,
            rotation,
            0,
            Math.PI * 2
        );
        veinPath.moveTo(leaf.x, leaf.y);
        veinPath.lineTo(
            leaf.x + Math.sin(rotation) * leaf.size,
            leaf.y - Math.cos(rotation) * leaf.size
        );
    }
    return { leafPath, veinPath };
}

/**
 * Apply L-system production rules to generate the fractal string.
 */
export function generateLSystemString(
    axiom: string,
    rules: Array<{ input: string; output: string; prob: number }>,
    iterations: number,
    seed: number = 12345
): string {
    let current = axiom;

    // Safety check: if no rules provided or empty array, return a basic F pattern
    // to ensure the plant is visible
    if (!rules || rules.length === 0) {
        // If axiom has X but no rules, convert X to F so we at least draw something
        current = axiom.replace(/X/g, 'F[-F][+F]F');
        // Apply basic branching
        for (let i = 0; i < iterations && current.length < 500; i++) {
            current = current.replace(/F/g, 'F[-F][+F]');
        }
        return current;
    }

    // Build rules map
    const ruleMap = new Map<string, Array<{ output: string; prob: number }>>();
    for (const rule of rules) {
        if (!ruleMap.has(rule.input)) {
            ruleMap.set(rule.input, []);
        }
        ruleMap.get(rule.input)!.push({ output: rule.output, prob: rule.prob });
    }

    // Apply rules for each iteration
    let seedCounter = seed;
    for (let i = 0; i < iterations; i++) {
        let next = '';
        for (const char of current) {
            const options = ruleMap.get(char);
            if (options && options.length > 0) {
                // Choose based on probability
                const totalProb = options.reduce((sum, o) => sum + o.prob, 0);
                seedCounter++;
                let roll = seededRandom(seedCounter) * totalProb;
                let chosen = char;
                for (const opt of options) {
                    roll -= opt.prob;
                    if (roll <= 0) {
                        chosen = opt.output;
                        break;
                    }
                }
                next += chosen;
            } else {
                next += char;
            }
        }
        current = next;
    }

    return current;
}

/**
 * Interpret an L-system string into drawable segments and leaves.
 */
export function interpretLSystem(
    lsystemString: string,
    baseAngle: number,
    lengthRatio: number,
    curveFactor: number,
    stemThickness: number,
    leafDensity: number,
    baseLength: number = 15,
    startX: number = 0,
    startY: number = 0,
    seed: number = 12345
): { segments: FractalSegment[]; leaves: FractalLeaf[] } {
    const segments: FractalSegment[] = [];
    const leaves: FractalLeaf[] = [];
    const stateStack: TurtleState[] = [];

    // Initial turtle state (pointing up)
    let state: TurtleState = {
        x: startX,
        y: startY,
        angle: -90, // Point upward (0 = right, -90 = up)
        length: baseLength,
        thickness: stemThickness * 3,
    };

    let depth = 0;
    let seedCounter = seed;

    for (const char of lsystemString) {
        switch (char) {
            case 'F':
            case 'R': {
                const dx = Math.cos((state.angle * Math.PI) / 180) * state.length;
                const dy = Math.sin((state.angle * Math.PI) / 180) * state.length;
                const newX = state.x + dx;
                const newY = state.y + dy;

                const isRoot = char === 'R';
                segments.push({
                    x1: state.x,
                    y1: state.y,
                    x2: newX,
                    y2: newY,
                    thickness: isRoot ? state.thickness * 1.1 : state.thickness,
                    depth: depth,
                    kind: isRoot ? 'root' : 'branch',
                });

                state.x = newX;
                state.y = newY;

                // Roots avoid leaves; branches may sprout them
                if (!isRoot) {
                    seedCounter++;
                    if (seededRandom(seedCounter) < leafDensity * 0.3) {
                        seedCounter++;
                        leaves.push({
                            x: state.x,
                            y: state.y,
                            angle: state.angle,
                            size: 3 + seededRandom(seedCounter) * 4,
                        });
                    }
                }
                break;
            }

            case 'f': {
                const fdx = Math.cos((state.angle * Math.PI) / 180) * state.length;
                const fdy = Math.sin((state.angle * Math.PI) / 180) * state.length;
                state.x += fdx;
                state.y += fdy;
                break;
            }

            case '+':
                seedCounter++;
                state.angle += baseAngle + curveFactor * (seededRandom(seedCounter) - 0.5) * 20;
                break;

            case '-':
                seedCounter++;
                state.angle -= baseAngle + curveFactor * (seededRandom(seedCounter) - 0.5) * 20;
                break;

            case '&': {
                seedCounter++;
                // Downward bend for aerial roots
                state.angle += baseAngle * 0.45 + curveFactor * (seededRandom(seedCounter) - 0.5) * 18;
                break;
            }

            case '[':
                stateStack.push({ ...state });
                depth++;
                state.length *= lengthRatio;
                state.thickness *= 0.7;
                break;

            case ']':
                if (stateStack.length > 0) {
                    seedCounter++;
                    if (seededRandom(seedCounter) < leafDensity) {
                        seedCounter++;
                        leaves.push({
                            x: state.x,
                            y: state.y,
                            angle: state.angle,
                            size: 4 + seededRandom(seedCounter) * 5,
                        });
                    }
                    state = stateStack.pop()!;
                    depth--;
                }
                break;

            case '|':
                state.angle += 180;
                break;
        }
    }

    return { segments, leaves };
}
