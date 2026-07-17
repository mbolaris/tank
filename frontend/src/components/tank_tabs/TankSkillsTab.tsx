import { ForagingGymPanel } from '../ForagingGymPanel';
import { SkillLadderPanel } from '../SkillLadderPanel';

/** Research-facing, domain-neutral skill measurements and evaluators. */
export function TankSkillsTab({
    worldId,
    onSelectEntity
}: {
    worldId?: string;
    onSelectEntity?: (entityId: number, entityType: string) => void;
}) {
    return (
        <div style={styles.layout}>
            <div style={styles.intro}>
                <p style={styles.description}>
                    See how Tank World’s behaviors perform in standardized challenges. These tests use
                    the same conditions every time, making improvements easy to compare.
                </p>
            </div>

            <ForagingGymPanel worldId={worldId} onSelectEntity={onSelectEntity} />
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
