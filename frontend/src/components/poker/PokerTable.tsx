/**
 * Enhanced poker table component with felt texture and chips
 */

import { useState, useEffect, useRef } from 'react';
import { PlayingCard } from './PlayingCard';
import { ChipStack } from './PokerChip';
import styles from './PokerTable.module.css';
import cardStyles from './PlayingCard.module.css';

interface PokerTableProps {
    pot: number;
    communityCards: string[];
    resultBanner?: React.ReactNode;
}

const CARD_FLIP_DELAY = 1000; // 1 second between card flips

export function PokerTable({ pot, communityCards, resultBanner }: PokerTableProps) {
    const [revealedCards, setRevealedCards] = useState<string[]>([]);
    const [flippingIndex, setFlippingIndex] = useState<number | null>(null);
    const prevCardsRef = useRef<string[]>([]);
    const timeoutsRef = useRef<NodeJS.Timeout[]>([]);

    useEffect(() => {
        // Clear any pending timeouts when component unmounts or cards change
        return () => {
            timeoutsRef.current.forEach(timeout => clearTimeout(timeout));
            timeoutsRef.current = [];
        };
    }, []);

    useEffect(() => {
        const prevCards = prevCardsRef.current;

        // If cards decreased (new hand), reset revealed cards
        if (communityCards.length < prevCards.length) {
            timeoutsRef.current.forEach(timeout => clearTimeout(timeout));
            timeoutsRef.current = [];
            setRevealedCards([]);
            setFlippingIndex(null);
            prevCardsRef.current = communityCards;
            return;
        }

        // Find new cards that need to be revealed
        const newCards = communityCards.slice(revealedCards.length);

        if (newCards.length > 0) {
            // Clear any existing timeouts
            timeoutsRef.current.forEach(timeout => clearTimeout(timeout));
            timeoutsRef.current = [];

            // Reveal cards one at a time with delay
            newCards.forEach((card, index) => {
                const delay = index * CARD_FLIP_DELAY;
                const cardIndex = revealedCards.length + index;

                const timeout = setTimeout(() => {
                    setFlippingIndex(cardIndex);

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

        prevCardsRef.current = communityCards;
    }, [communityCards, revealedCards.length]);

    return (
        <div className={styles.table}>
            {/* Pot, Community Cards, Phase all side by side */}
            <div className={styles.topRow}>
                {/* Pot display */}
                <div className={styles.potArea}>
                    <div className={styles.potLabel}>POT</div>
                    <div className={styles.potChips}>
                        <ChipStack totalValue={Math.round(pot)} size="medium" />
                    </div>
                    <div className={styles.potAmount}>{Math.round(pot)} ⚡</div>
                </div>

                {/* Community cards area */}
                <div className={styles.communityCardsArea}>
                    <div className={styles.communityCardsLabel}>Community Cards</div>
                    <div className={styles.communityCards}>
                        {/* Always show 5 cards - flipped or face-down */}
                        {[0, 1, 2, 3, 4].map((idx) => {
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
                                        card={communityCards[idx]}
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
                        })}
                    </div>
                </div>

                {/* Right side: Result banner only (phase is now in header) */}
                {resultBanner && (
                    <div className={styles.rightArea}>
                        <div className={styles.resultArea}>
                            {resultBanner}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
