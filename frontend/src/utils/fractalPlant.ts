/**
 * L-System fractal plant rendering utilities.
 *
 * This module generates fractal plant shapes using L-system grammar rules
 * inherited from the plant's genome.
 */

export interface PlantGenomeData {
  axiom: string;
  angle: number;
  length_ratio: number;
  branch_probability: number;
  curve_factor: number;
  color_hue: number;
  color_saturation: number;
  stem_thickness: number;
  leaf_density: number;
  production_rules: Array<{
    input: string;
    output: string;
    prob: number;
  }>;
}

interface TurtleState {
  x: number;
  y: number;
  angle: number;
  length: number;
  thickness: number;
}

interface FractalSegment {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  thickness: number;
  depth: number;
}

interface FractalLeaf {
  x: number;
  y: number;
  angle: number;
  size: number;
}

/**
 * Apply L-system production rules to generate the fractal string.
 */
export function generateLSystemString(
  axiom: string,
  rules: Array<{ input: string; output: string; prob: number }>,
  iterations: number
): string {
  let current = axiom;

  // Build rules map
  const ruleMap = new Map<string, Array<{ output: string; prob: number }>>();
  for (const rule of rules) {
    if (!ruleMap.has(rule.input)) {
      ruleMap.set(rule.input, []);
    }
    ruleMap.get(rule.input)!.push({ output: rule.output, prob: rule.prob });
  }

  // Apply rules for each iteration
  for (let i = 0; i < iterations; i++) {
    let next = '';
    for (const char of current) {
      const options = ruleMap.get(char);
      if (options && options.length > 0) {
        // Choose based on probability
        const totalProb = options.reduce((sum, o) => sum + o.prob, 0);
        let roll = Math.random() * totalProb;
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
  startY: number = 0
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

  for (const char of lsystemString) {
    switch (char) {
      case 'F': // Move forward and draw
        const dx = Math.cos((state.angle * Math.PI) / 180) * state.length;
        const dy = Math.sin((state.angle * Math.PI) / 180) * state.length;
        const newX = state.x + dx;
        const newY = state.y + dy;

        segments.push({
          x1: state.x,
          y1: state.y,
          x2: newX,
          y2: newY,
          thickness: state.thickness,
          depth: depth,
        });

        state.x = newX;
        state.y = newY;

        // Possibly add a leaf at branch tips
        if (Math.random() < leafDensity * 0.3) {
          leaves.push({
            x: state.x,
            y: state.y,
            angle: state.angle,
            size: 3 + Math.random() * 4,
          });
        }
        break;

      case 'f': // Move forward without drawing
        const fdx = Math.cos((state.angle * Math.PI) / 180) * state.length;
        const fdy = Math.sin((state.angle * Math.PI) / 180) * state.length;
        state.x += fdx;
        state.y += fdy;
        break;

      case '+': // Turn right
        state.angle += baseAngle + curveFactor * (Math.random() - 0.5) * 20;
        break;

      case '-': // Turn left
        state.angle -= baseAngle + curveFactor * (Math.random() - 0.5) * 20;
        break;

      case '[': // Push state (start branch)
        stateStack.push({ ...state });
        depth++;
        state.length *= lengthRatio;
        state.thickness *= 0.7;
        break;

      case ']': // Pop state (end branch)
        if (stateStack.length > 0) {
          // Add leaf at branch tip
          if (Math.random() < leafDensity) {
            leaves.push({
              x: state.x,
              y: state.y,
              angle: state.angle,
              size: 4 + Math.random() * 5,
            });
          }
          state = stateStack.pop()!;
          depth--;
        }
        break;

      case '|': // Turn around
        state.angle += 180;
        break;
    }
  }

  return { segments, leaves };
}

/**
 * Convert HSL to RGB color string.
 */
function hslToRgb(h: number, s: number, l: number): string {
  let r: number, g: number, b: number;

  if (s === 0) {
    r = g = b = l;
  } else {
    const hue2rgb = (p: number, q: number, t: number): number => {
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

  return `rgb(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)})`;
}

/**
 * Render a fractal plant to a canvas context.
 */
export function renderFractalPlant(
  ctx: CanvasRenderingContext2D,
  genome: PlantGenomeData,
  x: number,
  y: number,
  sizeMultiplier: number,
  iterations: number,
  elapsedTime: number,
  nectarReady: boolean = false
): void {
  // Generate L-system string
  const lsystemString = generateLSystemString(
    genome.axiom,
    genome.production_rules,
    iterations
  );

  // Calculate base length based on size
  const baseLength = 10 + sizeMultiplier * 12;

  // Apply gentle swaying animation
  const swayAngle = Math.sin(elapsedTime * 0.001 + x * 0.01) * 3;

  // Interpret L-system into drawable elements
  const { segments, leaves } = interpretLSystem(
    lsystemString,
    genome.angle + swayAngle,
    genome.length_ratio,
    genome.curve_factor,
    genome.stem_thickness,
    genome.leaf_density,
    baseLength,
    x,
    y
  );

  // Get colors from genome
  const stemColor = hslToRgb(genome.color_hue, genome.color_saturation * 0.8, 0.25);
  const leafColor = hslToRgb(genome.color_hue, genome.color_saturation, 0.4);
  const highlightColor = hslToRgb(genome.color_hue, genome.color_saturation * 0.6, 0.55);

  ctx.save();

  // Draw shadow
  ctx.save();
  ctx.globalAlpha = 0.15;
  ctx.translate(3, 3);

  for (const seg of segments) {
    ctx.beginPath();
    ctx.moveTo(seg.x1, seg.y1);
    ctx.lineTo(seg.x2, seg.y2);
    ctx.strokeStyle = '#000';
    ctx.lineWidth = seg.thickness + 1;
    ctx.lineCap = 'round';
    ctx.stroke();
  }
  ctx.restore();

  // Draw stem segments (back to front by depth)
  const sortedSegments = [...segments].sort((a, b) => a.depth - b.depth);

  for (const seg of sortedSegments) {
    // Main stem stroke
    ctx.beginPath();
    ctx.moveTo(seg.x1, seg.y1);
    ctx.lineTo(seg.x2, seg.y2);
    ctx.strokeStyle = stemColor;
    ctx.lineWidth = seg.thickness;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Highlight stroke
    ctx.beginPath();
    ctx.moveTo(seg.x1, seg.y1);
    ctx.lineTo(seg.x2, seg.y2);
    ctx.strokeStyle = highlightColor;
    ctx.lineWidth = seg.thickness * 0.4;
    ctx.lineCap = 'round';
    ctx.stroke();
  }

  // Draw leaves
  for (const leaf of leaves) {
    ctx.save();
    ctx.translate(leaf.x, leaf.y);
    ctx.rotate((leaf.angle * Math.PI) / 180 + Math.PI / 2);

    // Leaf shape (ellipse)
    ctx.beginPath();
    ctx.ellipse(0, -leaf.size / 2, leaf.size * 0.4, leaf.size, 0, 0, Math.PI * 2);
    ctx.fillStyle = leafColor;
    ctx.fill();

    // Leaf vein
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(0, -leaf.size);
    ctx.strokeStyle = highlightColor;
    ctx.lineWidth = 0.5;
    ctx.stroke();

    ctx.restore();
  }

  // Draw nectar glow if ready
  if (nectarReady) {
    // Find topmost point
    let topY = y;
    for (const seg of segments) {
      topY = Math.min(topY, seg.y1, seg.y2);
    }

    // Pulsing glow
    const pulse = 0.5 + Math.sin(elapsedTime * 0.005) * 0.3;

    ctx.beginPath();
    const gradient = ctx.createRadialGradient(x, topY - 10, 0, x, topY - 10, 20);
    gradient.addColorStop(0, `rgba(255, 220, 100, ${pulse})`);
    gradient.addColorStop(0.5, `rgba(255, 200, 50, ${pulse * 0.5})`);
    gradient.addColorStop(1, 'rgba(255, 180, 0, 0)');
    ctx.arc(x, topY - 10, 20, 0, Math.PI * 2);
    ctx.fillStyle = gradient;
    ctx.fill();

    // Nectar droplet
    ctx.beginPath();
    ctx.arc(x, topY - 10, 6, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(255, 220, 100, ${0.8 + pulse * 0.2})`;
    ctx.fill();
    ctx.strokeStyle = 'rgba(255, 255, 200, 0.8)';
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  ctx.restore();
}

/**
 * Render plant nectar (the collectible item).
 */
export function renderPlantNectar(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  elapsedTime: number
): void {
  ctx.save();

  // Pulsing animation
  const pulse = 1 + Math.sin(elapsedTime * 0.008) * 0.15;
  const size = Math.min(width, height) * pulse;

  // Glow effect
  const gradient = ctx.createRadialGradient(x, y, 0, x, y, size * 1.5);
  gradient.addColorStop(0, 'rgba(255, 230, 120, 0.9)');
  gradient.addColorStop(0.4, 'rgba(255, 200, 80, 0.6)');
  gradient.addColorStop(1, 'rgba(255, 180, 50, 0)');

  ctx.beginPath();
  ctx.arc(x, y, size * 1.5, 0, Math.PI * 2);
  ctx.fillStyle = gradient;
  ctx.fill();

  // Main nectar droplet
  ctx.beginPath();
  ctx.arc(x, y, size * 0.5, 0, Math.PI * 2);
  ctx.fillStyle = 'rgba(255, 220, 100, 0.95)';
  ctx.fill();

  // Highlight
  ctx.beginPath();
  ctx.arc(x - size * 0.15, y - size * 0.15, size * 0.2, 0, Math.PI * 2);
  ctx.fillStyle = 'rgba(255, 255, 220, 0.8)';
  ctx.fill();

  ctx.restore();
}

/**
 * Get default genome for testing.
 */
export function getDefaultPlantGenome(): PlantGenomeData {
  return {
    axiom: 'F',
    angle: 25,
    length_ratio: 0.7,
    branch_probability: 0.85,
    curve_factor: 0.1,
    color_hue: 0.33,
    color_saturation: 0.7,
    stem_thickness: 1.0,
    leaf_density: 0.6,
    production_rules: [
      { input: 'F', output: 'FF-[-F+F+F]+[+F-F-F]', prob: 0.7 },
      { input: 'F', output: 'F[-F][+F]', prob: 0.3 },
    ],
  };
}
