/**
 * Poker player card component
 */

import React from 'react';
import { PlayingCard } from './PlayingCard';
import { ChipStack } from './PokerChip';
import styles from './PokerPlayer.module.css';
import type { FishGenomeData } from '../../types/simulation';
import { getEyePosition, getFishPath, type FishParams } from '../../utils/fishTemplates';

interface PokerPlayerProps {
    name: string;
    energy: number;
    currentBet: number;
    folded: boolean;
    isActive: boolean;
    isHuman: boolean;
    fishId?: number;
    generation?: number;
    genomeData?: FishGenomeData;
    cards?: string[];
}

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

function FishAvatar({
    fishId,
    genomeData,
}: {
    fishId?: number;
    genomeData?: FishGenomeData;
}) {
    const fishParams = buildFishParams(genomeData);
    const label = fishId ? `Fish #${fishId}` : 'AI Fish';

    if (!fishParams) {
        return (
            <div className={styles.avatarCircle}>
                <img src={DEFAULT_FISH_IMAGE} alt={label} className={styles.avatarImage} />
            </div>
        );
    }

    const baseSize = 90;
    const padding = 15;
    const viewBoxSize = baseSize + padding * 2;
    const fishPath = getFishPath(fishParams, baseSize);
    const eyePos = getEyePosition(fishParams, baseSize);
    const eyeRadius = 3 * fishParams.eye_size;
    const hueDegrees = (fishParams.color_hue ?? 0) * 360;
    const baseColor = `hsl(${hueDegrees}deg 70% 60%)`;
    const strokeColor = `hsl(${hueDegrees}deg 80% 40%)`;
    const patternColor = `hsl(${hueDegrees}deg 75% 35%)`;
    const gradientId = `fish-pattern-${fishId ?? 'ai'}`;

    return (
        <div className={styles.avatarCircle}>
            <svg viewBox={`${-padding} ${-padding} ${viewBoxSize} ${viewBoxSize}`} className={styles.avatarSvg} aria-hidden>
                <path d={fishPath} fill={baseColor} stroke={strokeColor} strokeWidth={2} />
                {fishParams.pattern_intensity > 0.05 &&
                    renderPattern(fishParams, patternColor, baseSize, gradientId)}
                <circle cx={eyePos.x} cy={eyePos.y} r={eyeRadius} fill="#ffffff" />
                <circle cx={eyePos.x} cy={eyePos.y} r={eyeRadius * 0.5} fill="#0f172a" />
            </svg>
        </div>
    );
}

export function PokerPlayer({
    name,
    energy,
    currentBet,
    folded,
    isActive,
    isHuman,
    fishId,
    genomeData,
    cards = [],
}: PokerPlayerProps) {
    const playerClass = `${styles.player} ${folded ? styles.folded : ''} ${isActive ? styles.active : ''}`;

    if (isHuman) {
        const humanClass = `${styles.humanPlayer} ${isActive ? styles.humanActive : ''}`;
        return (
            <div className={humanClass}>
                {/* Cards on the left */}
                <div className={styles.yourCards}>
                    <div className={styles.cardsContainer}>
                        {cards.map((card, idx) => (
                            <PlayingCard key={idx} card={card} size="small" />
                        ))}
                    </div>
                </div>

                {/* Chips and stats to the right of cards */}
                <div className={styles.playerStats}>
                    <div className={styles.chipStackContainer}>
                        <ChipStack totalValue={Math.round(energy)} size="medium" />
                        <div className={styles.energyText}>{Math.round(energy)} ⚡</div>
                    </div>
                    <div className={currentBet > 0 ? styles.currentBet : styles.betHidden}>
                        {currentBet > 0 ? `🪙 ${Math.round(currentBet)}` : ''}
                    </div>
                </div>
            </div>
        );
    }

    // Check if we should show actual cards (showdown) or card backs
    const showActualCards = cards.length > 0 && cards[0] !== '??';

    return (
        <div className={playerClass} title={name}>
            <FishAvatar fishId={fishId} genomeData={genomeData} />
            <div className={styles.opponentInfo}>
                <div className={styles.opponentCards}>
                    {showActualCards ? (
                        // Show actual cards during showdown
                        cards.map((card, idx) => (
                            <PlayingCard key={idx} card={card} size="small" />
                        ))
                    ) : (
                        // Show card backs during normal play
                        <>
                            <PlayingCard card="BACK" size="small" faceDown={true} />
                            <PlayingCard card="BACK" size="small" faceDown={true} />
                        </>
                    )}
                </div>
                <div className={styles.opponentStats}>
                    <div className={styles.chipWithTotal}>
                        <ChipStack totalValue={Math.round(energy)} size="small" />
                        <div className={styles.energyText}>{Math.round(energy)} ⚡</div>
                    </div>
                    <div className={currentBet > 0 ? styles.bet : styles.betHidden}>
                        {currentBet > 0 ? `🪙 ${Math.round(currentBet)}` : ''}
                    </div>
                    {folded && <div className={styles.foldedLabel}>FOLDED</div>}
                </div>
            </div>
        </div>
    );
}
