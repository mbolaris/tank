import { Fragment } from 'react';
import type { SoccerParticipant } from '../types/simulation';
import { lineageLabel, participantLabel } from './soccerParticipantLabels';
import { ROLE_LABELS, type PositionalRole } from './soccerFormation';
import styles from './LineupPanel.module.css';

const AVATAR_KIND_LABELS: Record<SoccerParticipant['avatar_kind'], string> = {
    fish: 'Tank fish',
    reference: 'Frozen reference',
    external: 'External agent',
    bot: 'Bot',
};

/**
 * §6.8 selected-player detail.
 *
 * Every field is optional on the wire, so a row is omitted rather than shown
 * empty - a card claiming "Generation —" reads as missing data about a fish
 * that has one.
 */
export function PlayerCard({
    participant,
    role,
    meanX,
}: {
    participant: SoccerParticipant;
    role?: PositionalRole;
    meanX?: number;
}) {
    const lineage = lineageLabel(participant);
    const rows: [string, string][] = [];
    rows.push(['Kind', AVATAR_KIND_LABELS[participant.avatar_kind] ?? participant.avatar_kind]);
    if (lineage) rows.push(['Lineage', lineage]);
    // Deliberately no originating-tank row. The arena is world-agnostic - the
    // same card presents an external RCSS participant - and the squad heading
    // already names the team. See `test_no_tank_id_in_world_agnostic_code`.
    if (participant.fish_id !== undefined) rows.push(['Fish id', String(participant.fish_id)]);
    if (role) rows.push(['Role', `${role} · ${ROLE_LABELS[role]}`]);
    if (meanX !== undefined) rows.push(['Mean x', `${meanX.toFixed(1)} m`]);

    return (
        <div className={styles.card} data-testid="soccer-player-card">
            <div className={styles.cardEyebrow}>Selected · #{participant.uniform_number}</div>
            <div className={styles.cardName}>{participantLabel(participant)}</div>
            <div className={styles.cardGrid}>
                {rows.map(([key, value]) => (
                    <Fragment key={key}>
                        <span className={styles.cardKey}>{key}</span>
                        <span className={styles.cardValue}>{value}</span>
                    </Fragment>
                ))}
            </div>
        </div>
    );
}
