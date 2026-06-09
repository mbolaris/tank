/**
 * Fish avatar component for poker displays
 */

import React from 'react';
import type { FishGenomeData } from '../../types/simulation';
import { getEyePosition, getFishPath, getFishFrontPath, getFishFrontEyePositions, getPatternOpacity } from '../../utils/fishTemplates';
import { buildFishParams, renderPattern } from './fishAvatarParts';
import { MicrobeAvatarCanvas } from './MicrobeAvatar';

const DEFAULT_FISH_IMAGE = '/images/george1.png';

interface FishAvatarProps {
    fishId?: number;
    genomeData?: FishGenomeData;
    size?: 'small' | 'medium' | 'large';
    view?: 'front' | 'side' | 'rear';
    className?: string;
    isHuman?: boolean;
    /** Active world type; 'petri' renders the genome as a microbe instead of a fish */
    worldType?: string;
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
    view = 'front',
    className,
    isHuman = false,
    worldType,
}: FishAvatarProps) {
    const fishParams = buildFishParams(genomeData);
    const isMicrobe = worldType === 'petri';
    const creature = isMicrobe ? 'Microbe' : 'Fish';
    const label = isHuman ? 'You' : fishId ? `${creature} #${fishId}` : `AI ${creature}`;
    const dims = sizeMap[size];

    const containerStyle: React.CSSProperties = {
        width: dims.container,
        height: dims.container,
        borderRadius: size === 'small' ? 6 : 10,
        background: isHuman
            ? 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)'
            : 'radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.08), rgba(15, 23, 42, 0.6)), #0f172a',
        border: isHuman ? '2px solid #60a5fa' : '1px solid rgba(148, 163, 184, 0.3)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        overflow: 'hidden',
        flexShrink: 0,
    };

    // Render human player avatar
    if (isHuman) {
        const iconSize = dims.container * 0.6;
        return (
            <div style={containerStyle} className={className}>
                <svg
                    width={iconSize}
                    height={iconSize}
                    viewBox="0 0 24 24"
                    fill="none"
                    aria-label={label}
                >
                    {/* Person silhouette */}
                    <circle cx="12" cy="8" r="4" fill="white" />
                    <path
                        d="M4 20c0-4 4-6 8-6s8 2 8 6"
                        fill="white"
                    />
                </svg>
            </div>
        );
    }

    // Petri dish mode: render the genome as a microbe (matches the dish visuals)
    if (isMicrobe) {
        return (
            <div style={containerStyle} className={className} role="img" aria-label={label}>
                <MicrobeAvatarCanvas fishId={fishId} genomeData={genomeData ?? {}} />
            </div>
        );
    }

    // Fallback for fish without genome data
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
    const hueDegrees = (fishParams.color_hue ?? 0) * 360;
    const baseColor = `hsl(${hueDegrees}deg 70% 60%)`;
    const strokeColor = `hsl(${hueDegrees}deg 80% 40%)`;
    const patternColor = `hsl(${hueDegrees}deg 75% 35%)`;
    const gradientId = `fish-pattern-${fishId ?? 'ai'}-${size}`;
    const patternOpacity = getPatternOpacity(fishParams.pattern_intensity, 0.8);
    const eyeRadius = 3 * fishParams.eye_size * (baseSize / 90);

    // Front view rendering with two eyes
    if (view === 'front') {
        const fishPath = getFishFrontPath(fishParams, baseSize);
        const eyePositions = getFishFrontEyePositions(fishParams, baseSize);

        return (
            <div style={containerStyle} className={className}>
                <svg
                    viewBox={`${-padding} ${-padding} ${viewBoxSize} ${viewBoxSize}`}
                    style={{ width: '100%', height: '100%' }}
                    aria-hidden
                >
                    <path d={fishPath} fill={baseColor} stroke={strokeColor} strokeWidth={2} />
                    {patternOpacity > 0 &&
                        renderPattern(fishParams, patternColor, baseSize, gradientId, patternOpacity)}
                    {/* Left eye */}
                    <circle cx={eyePositions.left.x} cy={eyePositions.left.y} r={eyeRadius} fill="#ffffff" />
                    <circle cx={eyePositions.left.x} cy={eyePositions.left.y} r={eyeRadius * 0.5} fill="#0f172a" />
                    {/* Right eye */}
                    <circle cx={eyePositions.right.x} cy={eyePositions.right.y} r={eyeRadius} fill="#ffffff" />
                    <circle cx={eyePositions.right.x} cy={eyePositions.right.y} r={eyeRadius * 0.5} fill="#0f172a" />
                    {/* Mouth - small curved line centered below eyes */}
                    <path
                        d={`M ${baseSize * 0.4} ${baseSize * 0.6} Q ${baseSize * 0.5} ${baseSize * 0.65}, ${baseSize * 0.6} ${baseSize * 0.6}`}
                        stroke={strokeColor}
                        strokeWidth={1.5}
                        fill="none"
                    />
                </svg>
            </div>
        );
    }

    // Side view rendering (original)
    const fishPath = getFishPath(fishParams, baseSize);
    const eyePos = getEyePosition(fishParams, baseSize);

    return (
        <div style={containerStyle} className={className}>
            <svg
                viewBox={`${-padding} ${-padding} ${viewBoxSize} ${viewBoxSize}`}
                style={{ width: '100%', height: '100%' }}
                aria-hidden
            >
                <path d={fishPath} fill={baseColor} stroke={strokeColor} strokeWidth={2} />
                {patternOpacity > 0 &&
                    renderPattern(fishParams, patternColor, baseSize, gradientId, patternOpacity)}
                <circle cx={eyePos.x} cy={eyePos.y} r={eyeRadius} fill="#ffffff" />
                <circle cx={eyePos.x} cy={eyePos.y} r={eyeRadius * 0.5} fill="#0f172a" />
            </svg>
        </div>
    );
}

