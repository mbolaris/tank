import type { SoccerMatchState, SoccerParticipant } from '../types/simulation';
import type { PositionalRole } from './soccerFormation';
import { ROLE_LABELS } from './soccerFormation';
import { lineageLabel, participantLabel, sideDisplayName } from './soccerParticipantLabels';
import styles from './LineupPanel.module.css';

export interface LineupPanelProps {
    match: SoccerMatchState | null;
    roles: Record<string, PositionalRole>;
    selectedParticipantId: string | null;
    onSelect: (participantId: string | null) => void;
}

function PlayerRow({
    participant,
    role,
    selected,
    onSelect,
}: {
    participant: SoccerParticipant;
    role: PositionalRole | undefined;
    selected: boolean;
    onSelect: (participantId: string | null) => void;
}) {
    const lineage = lineageLabel(participant);
    const frozen = participant.avatar_kind === 'reference';
    return (
        <li>
            <button
                type="button"
                className={`${styles.row} ${selected ? styles.rowSelected : ''}`}
                // Toggling means a second click on the selected row deselects,
                // which is the only way to clear selection from the keyboard.
                onClick={() => onSelect(selected ? null : participant.participant_id)}
                aria-pressed={selected}
                data-testid={`lineup-row-${participant.participant_id}`}
            >
                <span className={styles.number}>{participant.uniform_number}</span>
                <span className={styles.identity}>
                    <span className={styles.name}>{participantLabel(participant)}</span>
                    {lineage && <span className={styles.lineage}>{lineage}</span>}
                </span>
                {frozen ? (
                    <span className={styles.frozenTag} title="Frozen reference policy">FROZEN</span>
                ) : (
                    role && (
                        <span className={styles.role} title={ROLE_LABELS[role]}>
                            {role}
                        </span>
                    )
                )}
            </button>
        </li>
    );
}

function TeamLineup({
    match,
    side,
    participants,
    roles,
    selectedParticipantId,
    onSelect,
}: {
    match: SoccerMatchState | null;
    side: 'left' | 'right';
    participants: SoccerParticipant[];
    roles: Record<string, PositionalRole>;
    selectedParticipantId: string | null;
    onSelect: (participantId: string | null) => void;
}) {
    const generations = participants
        .map((participant) => participant.generation)
        .filter((generation): generation is number => generation !== undefined);
    const averageGeneration = generations.length
        ? generations.reduce((total, value) => total + value, 0) / generations.length
        : null;

    return (
        <section className={styles.team} aria-label={`${sideDisplayName(match, side)} lineup`}>
            <div className={styles.teamHeading}>
                <span className={`${styles.sideDot} ${side === 'left' ? styles.sideLeft : styles.sideRight}`} aria-hidden="true" />
                <h4>{sideDisplayName(match, side)}</h4>
            </div>
            <ul className={styles.rows}>
                {participants.map((participant) => (
                    <PlayerRow
                        key={participant.participant_id}
                        participant={participant}
                        role={roles[participant.participant_id]}
                        selected={participant.participant_id === selectedParticipantId}
                        onSelect={onSelect}
                    />
                ))}
            </ul>
            {averageGeneration !== null && (
                <div className={styles.teamFooter}>Avg generation {averageGeneration.toFixed(1)}</div>
            )}
        </section>
    );
}

/**
 * §6.8 lineups.
 *
 * Player count is data-driven (§10.4 rule 4) - nothing here assumes 3, 6 or 11,
 * so an 11-a-side roster scrolls rather than overflowing.
 */
export function LineupPanel({ match, roles, selectedParticipantId, onSelect }: LineupPanelProps) {
    const participants = match?.participants ?? [];

    if (!participants.length) {
        return (
            <div className={styles.panel} data-testid="soccer-lineup-panel">
                <div className={styles.heading}>
                    <h3>Lineups</h3>
                </div>
                <p className={styles.empty}>No squad is on the pitch yet.</p>
            </div>
        );
    }

    const bySide = (side: 'left' | 'right') =>
        participants
            .filter((participant) => participant.side === side)
            .sort((left, right) => left.uniform_number - right.uniform_number);

    return (
        <div className={styles.panel} data-testid="soccer-lineup-panel">
            <div className={styles.heading}>
                <h3>Lineups</h3>
                <span className={styles.count}>{participants.length} players</span>
            </div>
            <TeamLineup match={match} side="left" participants={bySide('left')} roles={roles} selectedParticipantId={selectedParticipantId} onSelect={onSelect} />
            <TeamLineup match={match} side="right" participants={bySide('right')} roles={roles} selectedParticipantId={selectedParticipantId} onSelect={onSelect} />
        </div>
    );
}
