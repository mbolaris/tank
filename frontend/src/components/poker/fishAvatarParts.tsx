/**
 * Shared helpers for rendering genome-based fish avatars in poker displays.
 */

import React from 'react';
import type { FishGenomeData } from '../../types/simulation';
import { getFishPath, type FishParams } from '../../utils/fishTemplates';

export function buildFishParams(genomeData?: FishGenomeData): FishParams | null {
    if (!genomeData) return null;

    return {
        template_id: genomeData.template_id ?? 0,
        fin_size: genomeData.fin_size ?? 1,
        tail_size: genomeData.tail_size ?? 1,
        body_aspect: genomeData.body_aspect ?? 1,
        eye_size: genomeData.eye_size ?? 1,
        pattern_intensity: genomeData.pattern_intensity ?? 0,
        pattern_type: genomeData.pattern_type ?? 0,
        color_hue: genomeData.color_hue ?? 0,
        size: genomeData.size ?? 1,
    };
}

export function renderPattern(
    params: FishParams,
    patternColor: string,
    baseSize: number,
    gradientId: string,
    patternOpacity: number
): React.ReactNode {
    if (patternOpacity <= 0) {
        return null;
    }
    const commonProps = {
        opacity: patternOpacity,
        stroke: patternColor,
        fill: 'none',
        strokeWidth: 2,
    } as const;

    switch (params.pattern_type) {
        case 0: // Stripes
            return (
                <g {...commonProps}>
                    <line x1={baseSize * 0.3} y1={baseSize * 0.2} x2={baseSize * 0.3} y2={baseSize * 0.8} />
                    <line x1={baseSize * 0.5} y1={baseSize * 0.2} x2={baseSize * 0.5} y2={baseSize * 0.8} />
                    <line x1={baseSize * 0.7} y1={baseSize * 0.2} x2={baseSize * 0.7} y2={baseSize * 0.8} />
                </g>
            );
        case 1: // Spots
            return (
                <g fill={patternColor} opacity={patternOpacity}>
                    <circle cx={baseSize * 0.4} cy={baseSize * 0.35} r={3} />
                    <circle cx={baseSize * 0.6} cy={baseSize * 0.4} r={3} />
                    <circle cx={baseSize * 0.5} cy={baseSize * 0.6} r={3} />
                    <circle cx={baseSize * 0.7} cy={baseSize * 0.65} r={3} />
                </g>
            );
        case 2: // Solid overlay
            return (
                <path
                    d={getFishPath(params, baseSize)}
                    fill={patternColor}
                    opacity={patternOpacity * 0.6}
                />
            );
        case 3: // Gradient
            return (
                <>
                    <defs>
                        <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stopColor={patternColor} stopOpacity={patternOpacity} />
                            <stop offset="100%" stopColor="transparent" stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <path d={getFishPath(params, baseSize)} fill={`url(#${gradientId})`} />
                </>
            );
        case 4: // Chevron
            return (
                <g stroke={patternColor} strokeWidth={2} fill="none" opacity={patternOpacity}>
                    {/* Column 1 */}
                    <path d={`M ${baseSize * 0.3} ${baseSize * 0.25 - 4} L ${baseSize * 0.3 - 4} ${baseSize * 0.25} L ${baseSize * 0.3} ${baseSize * 0.25 + 4}`} />
                    <path d={`M ${baseSize * 0.3} ${baseSize * 0.5 - 4} L ${baseSize * 0.3 - 4} ${baseSize * 0.5} L ${baseSize * 0.3} ${baseSize * 0.5 + 4}`} />
                    <path d={`M ${baseSize * 0.3} ${baseSize * 0.75 - 4} L ${baseSize * 0.3 - 4} ${baseSize * 0.75} L ${baseSize * 0.3} ${baseSize * 0.75 + 4}`} />

                    {/* Column 2 */}
                    <path d={`M ${baseSize * 0.5} ${baseSize * 0.25 - 4} L ${baseSize * 0.5 - 4} ${baseSize * 0.25} L ${baseSize * 0.5} ${baseSize * 0.25 + 4}`} />
                    <path d={`M ${baseSize * 0.5} ${baseSize * 0.5 - 4} L ${baseSize * 0.5 - 4} ${baseSize * 0.5} L ${baseSize * 0.5} ${baseSize * 0.5 + 4}`} />
                    <path d={`M ${baseSize * 0.5} ${baseSize * 0.75 - 4} L ${baseSize * 0.5 - 4} ${baseSize * 0.75} L ${baseSize * 0.5} ${baseSize * 0.75 + 4}`} />

                    {/* Column 3 */}
                    <path d={`M ${baseSize * 0.7} ${baseSize * 0.25 - 4} L ${baseSize * 0.7 - 4} ${baseSize * 0.25} L ${baseSize * 0.7} ${baseSize * 0.25 + 4}`} />
                    <path d={`M ${baseSize * 0.7} ${baseSize * 0.5 - 4} L ${baseSize * 0.7 - 4} ${baseSize * 0.5} L ${baseSize * 0.7} ${baseSize * 0.5 + 4}`} />
                    <path d={`M ${baseSize * 0.7} ${baseSize * 0.75 - 4} L ${baseSize * 0.7 - 4} ${baseSize * 0.75} L ${baseSize * 0.7} ${baseSize * 0.75 + 4}`} />
                </g>
            );
        case 5: // Scales (overlapping arcs)
            return (
                <g stroke={patternColor} strokeWidth={1.5} fill="none" opacity={patternOpacity}>
                    {/* Row 1 */}
                    <path d={`M ${baseSize * 0.35} ${baseSize * 0.25} A 5 5 0 0 1 ${baseSize * 0.25} ${baseSize * 0.25}`} />
                    <path d={`M ${baseSize * 0.55} ${baseSize * 0.25} A 5 5 0 0 1 ${baseSize * 0.45} ${baseSize * 0.25}`} />
                    <path d={`M ${baseSize * 0.75} ${baseSize * 0.25} A 5 5 0 0 1 ${baseSize * 0.65} ${baseSize * 0.25}`} />
                    {/* Row 2 (offset) */}
                    <path d={`M ${baseSize * 0.4} ${baseSize * 0.5} A 5 5 0 0 1 ${baseSize * 0.3} ${baseSize * 0.5}`} />
                    <path d={`M ${baseSize * 0.6} ${baseSize * 0.5} A 5 5 0 0 1 ${baseSize * 0.5} ${baseSize * 0.5}`} />
                    <path d={`M ${baseSize * 0.8} ${baseSize * 0.5} A 5 5 0 0 1 ${baseSize * 0.7} ${baseSize * 0.5}`} />
                    {/* Row 3 */}
                    <path d={`M ${baseSize * 0.35} ${baseSize * 0.75} A 5 5 0 0 1 ${baseSize * 0.25} ${baseSize * 0.75}`} />
                    <path d={`M ${baseSize * 0.55} ${baseSize * 0.75} A 5 5 0 0 1 ${baseSize * 0.45} ${baseSize * 0.75}`} />
                    <path d={`M ${baseSize * 0.75} ${baseSize * 0.75} A 5 5 0 0 1 ${baseSize * 0.65} ${baseSize * 0.75}`} />
                </g>
            );
        default:
            return null;
    }
}
