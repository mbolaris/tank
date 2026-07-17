import type { EntityData } from '../types/simulation';
import styles from './FollowStoryCard.module.css';

interface FollowStoryCardProps {
    fish: EntityData;
    onStop: () => void;
}

export function FollowStoryCard({ fish, onStop }: FollowStoryCardProps) {
    const name = fish.common_name || fish.taxonomy?.common_name || 'Tank fish';
    return (
        <div className={styles.card} role="status">
            <div className={styles.eyebrow}>Following</div>
            <strong>{String(name)} <span>#{fish.id}</span></strong>
            <div className={styles.meta}>Generation {fish.generation ?? 0} · {fish.energy === undefined ? 'Exploring' : `${Math.round(fish.energy)} energy`}</div>
            <div className={styles.hint}>Double-click any fish to follow its story.</div>
            <button onClick={onStop}>Stop following</button>
        </div>
    );
}
