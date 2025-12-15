/**
 * Parametric SVG fish templates
 *
 * Each template is a function that generates an SVG path string based on
 * genetic parameters. Templates are selected by template_id (0-5).
 */

export interface FishParams {
    template_id: number;    // 0-5
    fin_size: number;       // 0.6-1.4
    tail_size: number;      // 0.6-1.4
    body_aspect: number;    // 0.7-1.3
    eye_size: number;       // 0.7-1.3
    pattern_intensity: number;  // 0.0-1.0
    pattern_type: number;   // 0-3
    color_hue: number;      // 0.0-1.0
    size: number;           // size_modifier from genome
}

/**
 * Template 0: Classic rounded fish (like a goldfish)
 */
function template0(params: FishParams, baseSize: number): string {
    const width = baseSize * params.body_aspect;
    const height = baseSize;

    const bodyPath = `
    M ${width * 0.2} ${height * 0.5}
    Q ${width * 0.1} ${height * 0.2}, ${width * 0.4} ${height * 0.15}
    Q ${width * 0.7} ${height * 0.1}, ${width * 0.85} ${height * 0.3}
    Q ${width * 0.95} ${height * 0.5}, ${width * 0.85} ${height * 0.7}
    Q ${width * 0.7} ${height * 0.9}, ${width * 0.4} ${height * 0.85}
    Q ${width * 0.1} ${height * 0.8}, ${width * 0.2} ${height * 0.5}
  `;

    // Dorsal fin (top)
    const finScale = params.fin_size;
    const dorsalFin = `
    M ${width * 0.45} ${height * 0.15}
    Q ${width * 0.5} ${height * (0.15 - 0.2 * finScale)}, ${width * 0.55} ${height * 0.15}
  `;

    // Pectoral fin (side)
    const pectoralFin = `
    M ${width * 0.35} ${height * 0.5}
    Q ${width * (0.35 - 0.15 * finScale)} ${height * 0.55}, ${width * 0.35} ${height * 0.65}
  `;

    // Tail fin
    const tailScale = params.tail_size;
    const tailFin = `
    M ${width * 0.2} ${height * 0.4}
    Q ${width * (0.2 - 0.2 * tailScale)} ${height * 0.3}, ${width * (0.2 - 0.25 * tailScale)} ${height * 0.5}
    Q ${width * (0.2 - 0.2 * tailScale)} ${height * 0.7}, ${width * 0.2} ${height * 0.6}
  `;

    return `${bodyPath} ${dorsalFin} ${pectoralFin} ${tailFin}`;
}

/**
 * Template 1: Sleek torpedo fish (like a tuna)
 */
function template1(params: FishParams, baseSize: number): string {
    const width = baseSize * params.body_aspect;
    const height = baseSize;

    const bodyPath = `
    M ${width * 0.15} ${height * 0.5}
    Q ${width * 0.1} ${height * 0.35}, ${width * 0.5} ${height * 0.3}
    Q ${width * 0.9} ${height * 0.35}, ${width * 0.95} ${height * 0.5}
    Q ${width * 0.9} ${height * 0.65}, ${width * 0.5} ${height * 0.7}
    Q ${width * 0.1} ${height * 0.65}, ${width * 0.15} ${height * 0.5}
  `;

    const finScale = params.fin_size;
    const dorsalFin = `
    M ${width * 0.6} ${height * 0.3}
    L ${width * 0.65} ${height * (0.3 - 0.15 * finScale)}
    L ${width * 0.7} ${height * 0.3}
  `;

    const pectoralFin = `
    M ${width * 0.4} ${height * 0.5}
    Q ${width * (0.4 - 0.1 * finScale)} ${height * 0.6}, ${width * 0.35} ${height * 0.65}
  `;

    const tailScale = params.tail_size;
    const tailFin = `
    M ${width * 0.15} ${height * 0.35}
    Q ${width * (0.15 - 0.15 * tailScale)} ${height * 0.2}, ${width * (0.15 - 0.2 * tailScale)} ${height * 0.5}
    Q ${width * (0.15 - 0.15 * tailScale)} ${height * 0.8}, ${width * 0.15} ${height * 0.65}
  `;

    return `${bodyPath} ${dorsalFin} ${pectoralFin} ${tailFin}`;
}

/**
 * Template 2: Flat fish (like a flounder or betta)
 */
function template2(params: FishParams, baseSize: number): string {
    const width = baseSize * params.body_aspect;
    const height = baseSize;

    const bodyPath = `
    M ${width * 0.25} ${height * 0.5}
    Q ${width * 0.2} ${height * 0.25}, ${width * 0.6} ${height * 0.2}
    Q ${width * 0.9} ${height * 0.25}, ${width * 0.95} ${height * 0.5}
    Q ${width * 0.9} ${height * 0.75}, ${width * 0.6} ${height * 0.8}
    Q ${width * 0.2} ${height * 0.75}, ${width * 0.25} ${height * 0.5}
  `;

    const finScale = params.fin_size;
    const dorsalFin = `
    M ${width * 0.4} ${height * 0.2}
    Q ${width * 0.5} ${height * (0.2 - 0.25 * finScale)}, ${width * 0.7} ${height * 0.2}
  `;

    const ventralFin = `
    M ${width * 0.4} ${height * 0.8}
    Q ${width * 0.5} ${height * (0.8 + 0.25 * finScale)}, ${width * 0.7} ${height * 0.8}
  `;

    const tailScale = params.tail_size;
    const tailFin = `
    M ${width * 0.25} ${height * 0.35}
    Q ${width * (0.25 - 0.3 * tailScale)} ${height * 0.25}, ${width * (0.25 - 0.3 * tailScale)} ${height * 0.5}
    Q ${width * (0.25 - 0.3 * tailScale)} ${height * 0.75}, ${width * 0.25} ${height * 0.65}
  `;

    return `${bodyPath} ${dorsalFin} ${ventralFin} ${tailFin}`;
}

/**
 * Template 3: Angular fish (like an angelfish)
 */
function template3(params: FishParams, baseSize: number): string {
    const width = baseSize * params.body_aspect;
    const height = baseSize;

    const bodyPath = `
    M ${width * 0.3} ${height * 0.5}
    L ${width * 0.4} ${height * 0.25}
    L ${width * 0.7} ${height * 0.2}
    L ${width * 0.9} ${height * 0.4}
    L ${width * 0.9} ${height * 0.6}
    L ${width * 0.7} ${height * 0.8}
    L ${width * 0.4} ${height * 0.75}
    Z
  `;

    const finScale = params.fin_size;
    const dorsalFin = `
    M ${width * 0.5} ${height * 0.22}
    L ${width * 0.55} ${height * (0.22 - 0.3 * finScale)}
    L ${width * 0.6} ${height * 0.22}
  `;

    const ventralFin = `
    M ${width * 0.5} ${height * 0.78}
    L ${width * 0.55} ${height * (0.78 + 0.3 * finScale)}
    L ${width * 0.6} ${height * 0.78}
  `;

    const tailScale = params.tail_size;
    const tailFin = `
    M ${width * 0.3} ${height * 0.4}
    L ${width * (0.3 - 0.25 * tailScale)} ${height * 0.2}
    L ${width * (0.3 - 0.2 * tailScale)} ${height * 0.5}
    L ${width * (0.3 - 0.25 * tailScale)} ${height * 0.8}
    L ${width * 0.3} ${height * 0.6}
  `;

    return `${bodyPath} ${dorsalFin} ${ventralFin} ${tailFin}`;
}

/**
 * Template 4: Chubby fish (like a pufferfish)
 */
function template4(params: FishParams, baseSize: number): string {
    const width = baseSize * params.body_aspect;
    const height = baseSize;

    // More circular/round body
    const bodyPath = `
    M ${width * 0.25} ${height * 0.5}
    Q ${width * 0.2} ${height * 0.15}, ${width * 0.55} ${height * 0.15}
    Q ${width * 0.9} ${height * 0.2}, ${width * 0.92} ${height * 0.5}
    Q ${width * 0.9} ${height * 0.8}, ${width * 0.55} ${height * 0.85}
    Q ${width * 0.2} ${height * 0.85}, ${width * 0.25} ${height * 0.5}
  `;

    const finScale = params.fin_size;
    const dorsalFin = `
    M ${width * 0.5} ${height * 0.15}
    Q ${width * 0.55} ${height * (0.15 - 0.15 * finScale)}, ${width * 0.6} ${height * 0.15}
  `;

    const pectoralFin = `
    M ${width * 0.4} ${height * 0.5}
    Q ${width * (0.4 - 0.2 * finScale)} ${height * 0.5}, ${width * (0.4 - 0.15 * finScale)} ${height * 0.6}
  `;

    const tailScale = params.tail_size;
    const tailFin = `
    M ${width * 0.25} ${height * 0.45}
    Q ${width * (0.25 - 0.15 * tailScale)} ${height * 0.35}, ${width * (0.25 - 0.18 * tailScale)} ${height * 0.5}
    Q ${width * (0.25 - 0.15 * tailScale)} ${height * 0.65}, ${width * 0.25} ${height * 0.55}
  `;

    return `${bodyPath} ${dorsalFin} ${pectoralFin} ${tailFin}`;
}

/**
 * Template 5: Elongated fish (like an eel or barracuda)
 */
function template5(params: FishParams, baseSize: number): string {
    const width = baseSize * params.body_aspect * 1.3; // Longer
    const height = baseSize * 0.7; // Narrower

    const bodyPath = `
    M ${width * 0.1} ${height * 0.5}
    Q ${width * 0.05} ${height * 0.4}, ${width * 0.5} ${height * 0.35}
    Q ${width * 0.95} ${height * 0.4}, ${width * 0.98} ${height * 0.5}
    Q ${width * 0.95} ${height * 0.6}, ${width * 0.5} ${height * 0.65}
    Q ${width * 0.05} ${height * 0.6}, ${width * 0.1} ${height * 0.5}
  `;

    const finScale = params.fin_size;
    const dorsalFin = `
    M ${width * 0.7} ${height * 0.35}
    L ${width * 0.75} ${height * (0.35 - 0.12 * finScale)}
    L ${width * 0.8} ${height * 0.35}
  `;

    const pectoralFin = `
    M ${width * 0.3} ${height * 0.5}
    Q ${width * (0.3 - 0.08 * finScale)} ${height * 0.55}, ${width * 0.28} ${height * 0.6}
  `;

    const tailScale = params.tail_size;
    const tailFin = `
    M ${width * 0.1} ${height * 0.4}
    Q ${width * (0.1 - 0.12 * tailScale)} ${height * 0.25}, ${width * (0.1 - 0.15 * tailScale)} ${height * 0.5}
    Q ${width * (0.1 - 0.12 * tailScale)} ${height * 0.75}, ${width * 0.1} ${height * 0.6}
  `;

    return `${bodyPath} ${dorsalFin} ${pectoralFin} ${tailFin}`;
}

/**
 * Get the SVG path for a fish based on its genetic parameters
 */
export function getFishPath(params: FishParams, baseSize: number = 50): string {
    const templateFunctions = [
        template0,
        template1,
        template2,
        template3,
        template4,
        template5,
    ];

    const templateId = Math.max(0, Math.min(5, params.template_id));
    return templateFunctions[templateId](params, baseSize);
}

/**
 * Generate pattern overlay based on pattern_type and pattern_intensity
 */
export function getFishPattern(
    params: FishParams,
    baseSize: number,
    baseColor: string
): string | null {
    if (params.pattern_intensity < 0.05) {
        return null; // No pattern
    }

    const width = baseSize * params.body_aspect;
    const height = baseSize;
    const opacity = params.pattern_intensity * 0.8; // Increased from 0.4

    switch (params.pattern_type) {
        case 0: // Stripes
            return `
        <g opacity="${opacity}">
          <line x1="${width * 0.3}" y1="${height * 0.2}" x2="${width * 0.3}" y2="${height * 0.8}" stroke="${baseColor}" stroke-width="2" />
          <line x1="${width * 0.5}" y1="${height * 0.2}" x2="${width * 0.5}" y2="${height * 0.8}" stroke="${baseColor}" stroke-width="2" />
          <line x1="${width * 0.7}" y1="${height * 0.2}" x2="${width * 0.7}" y2="${height * 0.8}" stroke="${baseColor}" stroke-width="2" />
        </g>
      `;

        case 1: // Spots
            return `
        <g opacity="${opacity}">
          <circle cx="${width * 0.4}" cy="${height * 0.35}" r="3" fill="${baseColor}" />
          <circle cx="${width * 0.6}" cy="${height * 0.4}" r="3" fill="${baseColor}" />
          <circle cx="${width * 0.5}" cy="${height * 0.6}" r="3" fill="${baseColor}" />
          <circle cx="${width * 0.7}" cy="${height * 0.65}" r="3" fill="${baseColor}" />
        </g>
      `;

        case 2: // Solid (darker overlay)
            return `
        <path d="${getFishPath(params, baseSize)}" fill="${baseColor}" opacity="${opacity * 0.6}" />
      `;

        case 3: // Gradient
            return `
        <defs>
          <linearGradient id="pattern-gradient-${params.template_id}" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:${baseColor};stop-opacity:${opacity}" />
            <stop offset="100%" style="stop-color:${baseColor};stop-opacity:0" />
          </linearGradient>
        </defs>
        <path d="${getFishPath(params, baseSize)}" fill="url(#pattern-gradient-${params.template_id})" />
      `;

        case 4: // Chevron
            return `
        <g opacity="${opacity}" stroke="${baseColor}" stroke-width="2" fill="none">
          <path d="M ${width * 0.3} ${height * 0.25 - 4} L ${width * 0.3 - 4} ${height * 0.25} L ${width * 0.3} ${height * 0.25 + 4}" />
          <path d="M ${width * 0.3} ${height * 0.5 - 4} L ${width * 0.3 - 4} ${height * 0.5} L ${width * 0.3} ${height * 0.5 + 4}" />
          <path d="M ${width * 0.3} ${height * 0.75 - 4} L ${width * 0.3 - 4} ${height * 0.75} L ${width * 0.3} ${height * 0.75 + 4}" />

          <path d="M ${width * 0.5} ${height * 0.25 - 4} L ${width * 0.5 - 4} ${height * 0.25} L ${width * 0.5} ${height * 0.25 + 4}" />
          <path d="M ${width * 0.5} ${height * 0.5 - 4} L ${width * 0.5 - 4} ${height * 0.5} L ${width * 0.5} ${height * 0.5 + 4}" />
          <path d="M ${width * 0.5} ${height * 0.75 - 4} L ${width * 0.5 - 4} ${height * 0.75} L ${width * 0.5} ${height * 0.75 + 4}" />

          <path d="M ${width * 0.7} ${height * 0.25 - 4} L ${width * 0.7 - 4} ${height * 0.25} L ${width * 0.7} ${height * 0.25 + 4}" />
          <path d="M ${width * 0.7} ${height * 0.5 - 4} L ${width * 0.7 - 4} ${height * 0.5} L ${width * 0.7} ${height * 0.5 + 4}" />
          <path d="M ${width * 0.7} ${height * 0.75 - 4} L ${width * 0.7 - 4} ${height * 0.75} L ${width * 0.7} ${height * 0.75 + 4}" />
        </g>
      `;

        case 5: // Scales (overlapping arcs)
            return `
        <g opacity="${opacity}" stroke="${baseColor}" stroke-width="1.5" fill="none">
          <path d="M ${width * 0.35} ${height * 0.25} A 5 5 0 0 1 ${width * 0.25} ${height * 0.25}" />
          <path d="M ${width * 0.55} ${height * 0.25} A 5 5 0 0 1 ${width * 0.45} ${height * 0.25}" />
          <path d="M ${width * 0.75} ${height * 0.25} A 5 5 0 0 1 ${width * 0.65} ${height * 0.25}" />
          <path d="M ${width * 0.4} ${height * 0.5} A 5 5 0 0 1 ${width * 0.3} ${height * 0.5}" />
          <path d="M ${width * 0.6} ${height * 0.5} A 5 5 0 0 1 ${width * 0.5} ${height * 0.5}" />
          <path d="M ${width * 0.8} ${height * 0.5} A 5 5 0 0 1 ${width * 0.7} ${height * 0.5}" />
          <path d="M ${width * 0.35} ${height * 0.75} A 5 5 0 0 1 ${width * 0.25} ${height * 0.75}" />
          <path d="M ${width * 0.55} ${height * 0.75} A 5 5 0 0 1 ${width * 0.45} ${height * 0.75}" />
          <path d="M ${width * 0.75} ${height * 0.75} A 5 5 0 0 1 ${width * 0.65} ${height * 0.75}" />
        </g>
      `;

        default:
            return null;
    }
}

/**
 * Get eye position based on template
 */
export function getEyePosition(params: FishParams, baseSize: number): { x: number; y: number } {
    const width = baseSize * params.body_aspect;
    const height = baseSize;

    // Eye position varies slightly by template
    const positions = [
        { x: width * 0.7, y: height * 0.35 },  // Template 0
        { x: width * 0.75, y: height * 0.4 },  // Template 1
        { x: width * 0.75, y: height * 0.4 },  // Template 2
        { x: width * 0.7, y: height * 0.35 },  // Template 3
        { x: width * 0.65, y: height * 0.35 }, // Template 4
        { x: width * 0.85, y: height * 0.45 }, // Template 5
    ];

    const templateId = Math.max(0, Math.min(5, params.template_id));
    return positions[templateId];
}
