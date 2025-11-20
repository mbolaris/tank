/**
 * Playing card component for poker games
 */

import styles from './PlayingCard.module.css';

interface PlayingCardProps {
  card: string;
  size?: 'small' | 'medium' | 'large';
}

export function PlayingCard({ card, size = 'medium' }: PlayingCardProps) {
  const sizeClass = styles[size] || styles.medium;

  return (
    <div className={`${styles.card} ${sizeClass}`}>
      {card}
    </div>
  );
}
