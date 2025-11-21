/**
 * Poker player card component
 */

import { PlayingCard } from './PlayingCard';
import { ChipStack } from './PokerChip';
import styles from './PokerPlayer.module.css';

interface PokerPlayerProps {
    name: string;
    energy: number;
    currentBet: number;
    folded: boolean;
    isActive: boolean;
    isHuman: boolean;
    cards?: string[];
}

export function PokerPlayer({
    name,
    energy,
    currentBet,
    folded,
    isActive,
    isHuman,
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
                        <ChipStack totalValue={Math.floor(energy)} size="medium" />
                        <div className={styles.energyText}>{Math.floor(energy)} ⚡</div>
                    </div>
                    <div className={currentBet > 0 ? styles.currentBet : styles.betHidden}>
                        {currentBet > 0 ? `🪙 ${Math.floor(currentBet)}` : ''}
                    </div>
                </div>
            </div>
        );
    }

    // Check if we should show actual cards (showdown) or card backs
    const showActualCards = cards.length > 0 && cards[0] !== '??';

    return (
        <div className={playerClass}>
            <div className={styles.opponentName}>{name}</div>
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
                        <ChipStack totalValue={Math.floor(energy)} size="small" />
                        <div className={styles.energyText}>{Math.floor(energy)} ⚡</div>
                    </div>
                    <div className={currentBet > 0 ? styles.bet : styles.betHidden}>
                        {currentBet > 0 ? `🪙 ${Math.floor(currentBet)}` : ''}
                    </div>
                    {folded && <div className={styles.foldedLabel}>FOLDED</div>}
                </div>
            </div>
        </div>
    );
}
