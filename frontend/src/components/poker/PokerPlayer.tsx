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
        return (
            <div className={styles.humanPlayer}>
                <div className={styles.playerInfo}>
                    <div className={styles.playerName}>You</div>
                    <div className={styles.playerStats}>
                        <div className={styles.chipStackContainer}>
                            <ChipStack totalValue={Math.floor(energy)} size="medium" />
                        </div>
                        <div className={styles.energyText}>{energy.toFixed(1)} ⚡</div>
                        {currentBet > 0 && <div className={styles.currentBet}>Bet: {currentBet.toFixed(1)}</div>}
                    </div>
                </div>

                <div className={styles.yourCards}>
                    <div className={styles.cardsLabel}>Your Cards:</div>
                    <div className={styles.cardsContainer}>
                        {cards.map((card, idx) => (
                            <PlayingCard key={idx} card={card} size="small" />
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className={playerClass}>
            <div className={styles.opponentName}>{name}</div>
            <div className={styles.opponentInfo}>
                <div className={styles.opponentCards}>
                    <PlayingCard card="BACK" size="small" faceDown={true} />
                    <PlayingCard card="BACK" size="small" faceDown={true} />
                </div>
                <div className={styles.opponentStats}>
                    <div className={styles.chipStackContainer}>
                        <ChipStack totalValue={Math.floor(energy)} size="small" />
                    </div>
                    <div className={styles.energyText}>{energy.toFixed(1)} ⚡</div>
                    {currentBet > 0 && (
                        <div className={styles.bet}>Bet: {currentBet.toFixed(1)}</div>
                    )}
                    {folded && <div className={styles.foldedLabel}>FOLDED</div>}
                </div>
            </div>
        </div>
    );
}
