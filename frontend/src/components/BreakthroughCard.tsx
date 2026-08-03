import type { SkillBreakthrough } from '../types/skill';
import styles from './TeamProgressPanel.module.css';

function labelFor(kind: string): string {
    return kind.replaceAll('_', ' ').toUpperCase();
}

export function BreakthroughCard({ record }: { record: SkillBreakthrough }) {
    return (
        <article className={styles.breakthroughCard} data-testid="soccer-breakthrough-card">
            <div className={styles.breakthroughEyebrow}>BREAKTHROUGH</div>
            <strong>{labelFor(record.kind)}</strong>
            <span>{record.detail?.rung ? `Cleared ${record.detail.rung}` : `Frame ${record.frame}`}</span>
        </article>
    );
}
