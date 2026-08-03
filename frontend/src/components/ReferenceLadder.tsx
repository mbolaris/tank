import type { SkillLadder } from '../types/skill';
import styles from './TeamProgressPanel.module.css';

export function ReferenceLadder({ ladder }: { ladder?: SkillLadder }) {
    if (!ladder) return <div className={styles.emptySection}>No frozen-ruler evaluation yet.</div>;
    const next = ladder.rungs.find((rung) => !rung.beaten);
    return (
        <div className={styles.ladder} data-testid="reference-ladder">
            {ladder.rungs.map((rung) => (
                <div className={`${styles.ladderRow} ${rung.beaten ? styles.beaten : ''}`} key={rung.rung_id}>
                    <span>{rung.rung} {rung.rung_id}</span>
                    <span>{rung.beaten ? '✓' : '·'}</span>
                </div>
            ))}
            <div className={styles.nextMilestone}>Next: {next ? `${next.rung} (${next.rung_id})` : 'all current rungs cleared'}</div>
        </div>
    );
}
