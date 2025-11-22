/**
 * Fish avatar component for poker displays
 */

import React from 'react';
import type { FishGenomeData } from '../../types/simulation';
import { getEyePosition, getFishPath, type FishParams } from '../../utils/fishTemplates';

const DEFAULT_FISH_IMAGE = '/images/george1.png';

function buildFishParams(genomeData?: FishGenomeData): FishParams | null {
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

function renderPattern(
    params: FishParams,
    patternColor: string,
    baseSize: number,
    gradientId: string
): React.ReactNode {
    const commonProps = {
        opacity: params.pattern_intensity * 0.4,
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
                <g fill={patternColor} opacity={params.pattern_intensity * 0.4}>
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
                    opacity={params.pattern_intensity * 0.2}
                />
            );
        case 3: // Gradient
            return (
                <>
                    <defs>
                        <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stopColor={patternColor} stopOpacity={params.pattern_intensity * 0.4} />
                            <stop offset="100%" stopColor="transparent" stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <path d={getFishPath(params, baseSize)} fill={`url(#${gradientId})`} />
                </>
            );
        default:
            return null;
    }
}

interface FishAvatarProps {
    fishId?: number;
    genomeData?: FishGenomeData;
    size?: 'small' | 'medium' | 'large';
    className?: string;
}

const sizeMap = {
    small: { container: 28, baseSize: 50, padding: 8 },
    medium: { container: 62, baseSize: 90, padding: 15 },
    large: { container: 80, baseSize: 120, padding: 20 },
};

export function FishAvatar({
    fishId,
    genomeData,
    size = 'medium',
    className,
}: FishAvatarProps) {
    const fishParams = buildFishParams(genomeData);
    const label = fishId ? `Fish #${fishId}` : 'AI Fish';
    const dims = sizeMap[size];

    const containerStyle: React.CSSProperties = {
        width: dims.container,
        height: dims.container,
        borderRadius: size === 'small' ? 6 : 10,
        background: 'radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.08), rgba(15, 23, 42, 0.6)), #0f172a',
        border: '1px solid rgba(148, 163, 184, 0.3)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        overflow: 'hidden',
        flexShrink: 0,
    };

    if (!fishParams) {
        return (
            <div style={containerStyle} className={className}>
                <img
                    src={DEFAULT_FISH_IMAGE}
                    alt={label}
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
            </div>
        );
    }

    const { baseSize, padding } = dims;
    const viewBoxSize = baseSize + padding * 2;
    const fishPath = getFishPath(fishParams, baseSize);
    const eyePos = getEyePosition(fishParams, baseSize);
    const eyeRadius = 3 * fishParams.eye_size * (baseSize / 90);
    const hueDegrees = (fishParams.color_hue ?? 0) * 360;
    const baseColor = `hsl(${hueDegrees}deg 70% 60%)`;
    const strokeColor = `hsl(${hueDegrees}deg 80% 40%)`;
    const patternColor = `hsl(${hueDegrees}deg 75% 35%)`;
    const gradientId = `fish-pattern-${fishId ?? 'ai'}-${size}`;

    return (
        <div style={containerStyle} className={className}>
            <svg
                viewBox={`${-padding} ${-padding} ${viewBoxSize} ${viewBoxSize}`}
                style={{ width: '100%', height: '100%' }}
                aria-hidden
            >
                <path d={fishPath} fill={baseColor} stroke={strokeColor} strokeWidth={2} />
                {fishParams.pattern_intensity > 0.05 &&
                    renderPattern(fishParams, patternColor, baseSize, gradientId)}
                <circle cx={eyePos.x} cy={eyePos.y} r={eyeRadius} fill="#ffffff" />
                <circle cx={eyePos.x} cy={eyePos.y} r={eyeRadius * 0.5} fill="#0f172a" />
            </svg>
        </div>
    );
}
