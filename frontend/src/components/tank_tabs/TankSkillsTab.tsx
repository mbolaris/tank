import { ForagingGymPanel } from '../ForagingGymPanel';
import { SkillLadderPanel } from '../SkillLadderPanel';

/** Research-facing, domain-neutral skill measurements and evaluators. */
export function TankSkillsTab() {
    return (
        <div style={styles.layout}>
            <div style={styles.intro}>
                <p style={styles.description}>
                    Measure what agents can do outside the ecosystem composite. These frozen-ruler
                    tests make scores comparable across simulation changes and champion re-baselines.
                </p>
            </div>

            <ForagingGymPanel />
            <SkillLadderPanel />
        </div>
    );
}

const styles = {
    layout: {
        display: 'flex',
        flexDirection: 'column' as const,
        gap: '16px',
    },
    intro: {
        padding: '2px 4px 0',
    },
    title: {
        color: '#f8fafc',
        fontSize: '18px',
        fontWeight: 700,
    },
    description: {
        color: '#94a3b8',
        fontSize: '13px',
        lineHeight: 1.5,
        margin: '4px 0 0',
        maxWidth: '760px',
    },
} as const;
