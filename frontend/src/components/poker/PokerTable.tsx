/**
 * Enhanced poker table component with felt texture and chips
 */

import { PlayingCard } from './PlayingCard';
import { ChipStack } from './PokerChip';
import styles from './PokerTable.module.css';

interface PokerTableProps {
    pot: number;
    communityCards: string[];
    currentRound?: string;
}

// Helper to get round display name
function getRoundDisplay(round?: string): { name: string; cards: string } {
    switch (round) {
        case 'PRE_FLOP':
            return { name: 'Pre-Flop', cards: '0 cards' };
        case 'FLOP':
            return { name: 'Flop', cards: '3 cards' };
        case 'TURN':
            return { name: 'Turn', cards: '4 cards' };
        case 'RIVER':
            return { name: 'River', cards: '5 cards' };
        case 'SHOWDOWN':
            return { name: 'Showdown', cards: 'All cards revealed' };
        default:
            return { name: round || 'Starting', cards: '' };
    }
}

export function PokerTable({ pot, communityCards, currentRound }: PokerTableProps) {
    const roundInfo = getRoundDisplay(currentRound);

    return (
        <div className={styles.table}>
            {/* Round indicator */}
            <div className={styles.roundIndicator}>
                <span className={styles.roundName}>{roundInfo.name}</span>
                <span className={styles.roundCards}>{roundInfo.cards}</span>
            </div>

            {/* Pot and Community Cards side by side */}
            <div className={styles.topRow}>
                {/* Pot display */}
                <div className={styles.potArea}>
                    <div className={styles.potLabel}>POT</div>
                    <div className={styles.potChips}>
                        <ChipStack totalValue={Math.floor(pot)} size="medium" />
                    </div>
                    <div className={styles.potAmount}>{pot.toFixed(1)} ⚡</div>
                </div>

                {/* Community cards area */}
                <div className={styles.communityCardsArea}>
                    <div className={styles.communityCardsLabel}>Community Cards</div>
                    <div className={styles.communityCards}>
                        {/* Always show 5 cards - flipped or face-down */}
                        {[0, 1, 2, 3, 4].map((idx) => (
                            communityCards[idx] ? (
                                <PlayingCard key={idx} card={communityCards[idx]} size="small" />
                            ) : (
                                <PlayingCard key={idx} card="BACK" size="small" faceDown={true} />
                            )
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
