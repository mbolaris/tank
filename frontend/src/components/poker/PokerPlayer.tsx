/**
 * Poker player card component
 */

import { useState, useEffect, useRef } from 'react';
import { PlayingCard } from './PlayingCard';
import { ChipStack } from './PokerChip';
import styles from './PokerPlayer.module.css';
import cardStyles from './PlayingCard.module.css';
import type { FishGenomeData } from '../../types/simulation';
import { getFishFrontPath, getFishFrontEyePositions, getPatternOpacity } from '../../utils/fishTemplates';
import { buildFishParams, renderPattern } from './fishAvatarParts';
import { MicrobeAvatarCanvas } from './MicrobeAvatar';

const CARD_FLIP_DELAY = 1000; // 1 second between card flips

interface PokerPlayerProps {
    name: string;
    energy: number;
    currentBet: number;
    folded: boolean;
    isActive: boolean;
    isHuman: boolean;
    isAutopilot?: boolean;
    fishId?: number;
    generation?: number;
    genomeData?: FishGenomeData;
    cards?: string[];
    worldType?: string;
}

const DEFAULT_FISH_IMAGE = '/images/george1.png';

function FishAvatar({
    fishId,
    genomeData,
    isHuman,
    isAutopilot,
    size = 'small',
    worldType,
}: {
    fishId?: number;
    genomeData?: FishGenomeData;
    isHuman?: boolean;
    isAutopilot?: boolean;
    size?: 'small' | 'medium';
    worldType?: string;
}) {
    // 1. Human/Robot Override
    if (isHuman) {
        const iconSize = size === 'medium' ? 48 : 32;
        const icon = isAutopilot ? '🤖' : '👤'; // Robot for autopilot, Person for manual
        const label = isAutopilot ? 'Auto Player' : 'You';

        return (
            <div className={`${styles.avatarCircle} ${size === 'medium' ? styles.avatarMedium : ''}`} title={label}>
                <span style={{ fontSize: `${iconSize}px`, lineHeight: 1 }}>{icon}</span>
            </div>
        );
    }

    // 2. Fish/Microbe Avatar
    const fishParams = buildFishParams(genomeData);
    const creature = worldType === 'petri' ? 'Microbe' : 'Fish';
    const label = fishId ? `${creature} #${fishId}` : `AI ${creature}`;

    // Petri dish mode: render the genome as a microbe (matches the dish visuals)
    if (worldType === 'petri') {
        return (
            <div className={styles.avatarCircle} title={label} role="img" aria-label={label}>
                <MicrobeAvatarCanvas fishId={fishId} genomeData={genomeData ?? {}} />
            </div>
        );
    }

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
    const fishPath = getFishFrontPath(fishParams, baseSize);
    const eyePositions = getFishFrontEyePositions(fishParams, baseSize);
    const eyeRadius = 3 * fishParams.eye_size;
    const hueDegrees = (fishParams.color_hue ?? 0) * 360;
    const baseColor = `hsl(${hueDegrees}deg 70% 60%)`;
    const strokeColor = `hsl(${hueDegrees}deg 80% 40%)`;
    const patternColor = `hsl(${hueDegrees}deg 75% 35%)`;
    const gradientId = `fish-pattern-${fishId ?? 'ai'}`;
    const patternOpacity = getPatternOpacity(fishParams.pattern_intensity, 0.4);

    return (
        <div className={styles.avatarCircle}>
            <svg viewBox={`${-padding} ${-padding} ${viewBoxSize} ${viewBoxSize}`} className={styles.avatarSvg} aria-hidden>
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

export function PokerPlayer({
    name,
    energy,
    currentBet,
    folded,
    isActive,
    isHuman,
    isAutopilot,
    fishId,
    genomeData,
    cards = [],
    worldType,
}: PokerPlayerProps) {
    // All hooks must be called at the top level, before any conditional returns
    // Card flipping state for opponent cards
    const [revealedCards, setRevealedCards] = useState<string[]>([]);
    const [flippingIndex, setFlippingIndex] = useState<number | null>(null);
    const prevShowActualCardsRef = useRef(false);
    const timeoutsRef = useRef<ReturnType<typeof setTimeout>[]>([]);

    // Check if we should show actual cards (showdown) or card backs
    const showActualCards = cards.length > 0 && cards[0] !== '??';

    useEffect(() => {
        // Clear any pending timeouts when component unmounts
        return () => {
            timeoutsRef.current.forEach(timeout => clearTimeout(timeout));
            timeoutsRef.current = [];
        };
    }, []);

    useEffect(() => {
        // Skip card flip logic for human player
        if (isHuman) return;

        // If showdown just started (transitioned from card backs to actual cards)
        if (showActualCards && !prevShowActualCardsRef.current) {
            // Clear any existing timeouts
            timeoutsRef.current.forEach(timeout => clearTimeout(timeout));
            timeoutsRef.current = [];
            setRevealedCards([]);
            setFlippingIndex(null);

            // Reveal cards one at a time with delay
            cards.forEach((card, index) => {
                const delay = index * CARD_FLIP_DELAY;

                const timeout = setTimeout(() => {
                    setFlippingIndex(index);

                    // After flip animation (400ms), add card to revealed list
                    const revealTimeout = setTimeout(() => {
                        setRevealedCards(prev => [...prev, card]);
                        setFlippingIndex(null);
                    }, 400);

                    timeoutsRef.current.push(revealTimeout);
                }, delay);

                timeoutsRef.current.push(timeout);
            });
        }

        // If showdown ended (back to card backs), reset state
        if (!showActualCards && prevShowActualCardsRef.current) {
            timeoutsRef.current.forEach(timeout => clearTimeout(timeout));
            timeoutsRef.current = [];
            setRevealedCards([]);
            setFlippingIndex(null);
        }

        prevShowActualCardsRef.current = showActualCards;
    }, [isHuman, showActualCards, cards]);

    const playerClass = `${styles.player} ${folded ? styles.folded : ''} ${isActive ? styles.active : ''}`;

    if (isHuman) {
        const humanClass = `${styles.humanPlayer} ${isActive ? styles.humanActive : ''}`;
        return (
            <div className={humanClass}>
                {/* Avatar on the left */}
                <FishAvatar isHuman={true} isAutopilot={isAutopilot} />

                {/* Cards next to Avatar */}
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

    return (
        <div className={playerClass} title={name}>
            <FishAvatar fishId={fishId} genomeData={genomeData} worldType={worldType} />
            <div className={styles.opponentInfo}>
                <div className={styles.opponentCards}>
                    {showActualCards ? (
                        // Show actual cards during showdown with flip animation
                        cards.map((card, idx) => {
                            const isRevealed = idx < revealedCards.length;
                            const isFlipping = idx === flippingIndex;

                            if (isRevealed) {
                                return (
                                    <PlayingCard
                                        key={idx}
                                        card={revealedCards[idx]}
                                        size="small"
                                    />
                                );
                            } else if (isFlipping) {
                                return (
                                    <PlayingCard
                                        key={idx}
                                        card={card}
                                        size="small"
                                        className={cardStyles.flipping}
                                    />
                                );
                            } else {
                                return (
                                    <PlayingCard
                                        key={idx}
                                        card="BACK"
                                        size="small"
                                        faceDown={true}
                                    />
                                );
                            }
                        })
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
