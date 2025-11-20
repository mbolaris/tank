/**
 * Poker table component showing pot and community cards
 */

import { PlayingCard } from './PlayingCard';
import styles from './PokerTable.module.css';

interface PokerTableProps {
  pot: number;
  communityCards: string[];
}

export function PokerTable({ pot, communityCards }: PokerTableProps) {
  return (
    <div className={styles.table}>
      <div className={styles.pot}>
        <div className={styles.potLabel}>Pot</div>
        <div className={styles.potAmount}>{pot.toFixed(1)} ⚡</div>
      </div>

      <div className={styles.communityCards}>
        {communityCards.length > 0 ? (
          communityCards.map((card, idx) => (
            <PlayingCard key={idx} card={card} size="medium" />
          ))
        ) : (
          <div className={styles.noCards}>No community cards yet</div>
        )}
      </div>
    </div>
  );
}
