/**
 * Enhanced poker table component with felt texture and chips
 */

import { PlayingCard } from './PlayingCard';
import { ChipStack } from './PokerChip';
import styles from './PokerTable.module.css';

interface PokerTableProps {
    pot: number;
    communityCards: string[];
    resultBanner?: React.ReactNode;
}

export function PokerTable({ pot, communityCards, resultBanner }: PokerTableProps) {

    return (
        <div className={styles.table}>
            {/* Pot, Community Cards, Phase all side by side */}
            <div className={styles.topRow}>
                {/* Pot display */}
                <div className={styles.potArea}>
                    <div className={styles.potLabel}>POT</div>
                    <div className={styles.potChips}>
                        <ChipStack totalValue={Math.floor(pot)} size="medium" />
                    </div>
                    <div className={styles.potAmount}>{Math.floor(pot)} ⚡</div>
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
