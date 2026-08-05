import type { SoccerMatchState } from '../types/simulation';
import type { FormationMetrics } from '../hooks/useFormationMetrics';
import { ROLE_LABELS } from './soccerFormation';
import { participantLabel, sideDisplayName } from './soccerParticipantLabels';
import type { SoccerBroadcastMatch } from './soccerEvents';
import styles from './AnalysisPanel.module.css';

function percent(value: number | undefined): string {
    return value === undefined ? '—' : `${Math.round(value * 100)}%`;
}

/**
 * §4.2 Analysis metrics stack.
 *
 * Every row is derived from the match state already on the wire. Where a value
 * is genuinely absent it reads `—`; nothing here computes a plausible-looking
 * substitute, because a fabricated metric in an analysis view is worse than a
 * blank one.
 */
export function AnalysisPanel({ match, metrics }: { match: SoccerMatchState | null; metrics: FormationMetrics }) {
    const broadcast = match as SoccerBroadcastMatch | null;
    const possession = broadcast?.possession;
    const participants = match?.participants ?? [];
    const meanById = new Map(metrics.summaries.map((summary) => [summary.participantId, summary]));

    const rows = participants
        .map((participant) => ({
            participant,
            summary: meanById.get(participant.participant_id),
            role: metrics.roles[participant.participant_id],
        }))
        .sort((left, right) =>
            left.participant.side.localeCompare(right.participant.side) ||
            left.participant.uniform_number - right.participant.uniform_number);

    const kinds = new Map<string, number>();
    for (const participant of participants) {
        kinds.set(participant.avatar_kind, (kinds.get(participant.avatar_kind) ?? 0) + 1);
    }

    return (
        <div className={styles.panel} data-testid="soccer-analysis-panel">
            <div className={styles.heading}>
                <h3>Match analysis</h3>
                <span className={styles.label}>Analysis</span>
            </div>

            <section className={styles.section} aria-label="Match metrics">
                <div className={styles.sectionTitle}>Match</div>
                <dl className={styles.metrics}>
                    <div className={styles.metric}>
                        <dt>{sideDisplayName(match, 'left')} possession</dt>
                        <dd>{percent(possession?.left)}</dd>
                    </div>
                    <div className={styles.metric}>
                        <dt>{sideDisplayName(match, 'right')} possession</dt>
                        <dd>{percent(possession?.right)}</dd>
                    </div>
                    <div className={styles.metric}>
                        <dt>Passing chains</dt>
                        <dd>{metrics.chains.left + metrics.chains.right}</dd>
                    </div>
                    <div className={styles.metric}>
                        <dt>Sampled frames</dt>
                        <dd>{metrics.sampledFrames}</dd>
                    </div>
                </dl>
            </section>

            <section className={styles.section} aria-label="Player contributions">
                <div className={styles.sectionTitle}>Per player · mean position</div>
                {!rows.length ? (
                    <p className={styles.empty}>No squad on the pitch.</p>
                ) : (
                    <table className={styles.table}>
                        <thead>
                            <tr>
                                <th scope="col">#</th>
                                <th scope="col">Player</th>
                                <th scope="col">Role</th>
                                <th scope="col">Mean x</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows.map(({ participant, summary, role }) => (
                                <tr key={participant.participant_id} data-testid={`analysis-row-${participant.participant_id}`}>
                                    <td className={participant.side === 'left' ? styles.numberLeft : styles.numberRight}>
                                        {participant.uniform_number}
                                    </td>
                                    <td className={styles.name}>{participantLabel(participant)}</td>
                                    <td title={role ? ROLE_LABELS[role] : undefined}>{role ?? '—'}</td>
                                    <td className={styles.numeric}>
                                        {summary ? `${summary.meanX >= 0 ? '+' : ''}${summary.meanX.toFixed(1)}` : '—'}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </section>

            <section className={styles.section} aria-label="Participant kinds">
                <div className={styles.sectionTitle}>Roster composition</div>
                <ul className={styles.kinds}>
                    {[...kinds.entries()].map(([kind, count]) => (
                        <li key={kind}>
                            <span>{kind}</span>
                            <span className={styles.numeric}>{count}</span>
                        </li>
                    ))}
                    {!kinds.size && <li className={styles.empty}>No participants on the wire.</li>}
                </ul>
            </section>
        </div>
    );
}
