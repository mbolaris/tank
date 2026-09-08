/**
 * LegendsRoster - the organisms and lineages this tank remembers (U8b/E6).
 *
 * Each row states who, what they did, and the measured evidence behind it,
 * because a legend whose reason is not visible is just a nickname.
 *
 * **These are not benchmark champions.** The panel says so where a viewer can
 * see it: the `champions/` registry holds reproducible best-known solutions,
 * while a legend is a thing that happened in this one world's history and
 * means nothing outside it. Presenting them alike would let a lucky fish read
 * as a validated result.
 */

import type { Legend } from '../types/legend';
import { legendMeta, subjectLabel } from '../utils/legendDisplay';
import { formatSimulationTime } from '../utils/storyEventDisplay';
import styles from './LegendsRoster.module.css';

interface LegendsRosterProps {
    legends: Legend[];
    liveEntityIds?: ReadonlySet<number>;
    onInspectEntity?: (entityId: number) => void;
}

export function LegendsRoster({ legends, liveEntityIds, onInspectEntity }: LegendsRosterProps) {
    if (legends.length === 0) return null;

    return (
        <section className={styles.roster} aria-label="Legends of this tank" data-testid="legends-roster">
            <div className={styles.heading}>
                <h3 className={styles.title}>Legends of this tank</h3>
                <span className={styles.count}>
                    {legends.length} legend{legends.length === 1 ? '' : 's'}
                </span>
            </div>
            <p className={styles.disclaimer}>
                Promoted by in-world criteria. Not benchmark champions.
            </p>

            <ul className={styles.list}>
                {legends.map((legend) => {
                    const meta = legendMeta(legend.kind);
                    const fishId =
                        legend.subject_type === 'fish' ? Number(legend.subject_id) : NaN;
                    // Offer the inspector only for a fish still in the world;
                    // a legend outlives its subject, and most will be gone.
                    const canInspect =
                        Boolean(onInspectEntity) &&
                        Number.isFinite(fishId) &&
                        Boolean(liveEntityIds?.has(fishId));

                    return (
                        <li key={legend.id} className={styles.row} data-legend-kind={legend.kind}>
                            <div className={styles.rowHead}>
                                <span className={styles.icon} aria-hidden="true">{meta.icon}</span>
                                <span className={styles.name}>{legend.name}</span>
                                <span className={styles.kind}>{meta.label}</span>
                                <span className={styles.subject}>{subjectLabel(legend)}</span>
                                <span className={styles.clock}>
                                    {formatSimulationTime(legend.simulation_time)}
                                </span>
                            </div>
                            <p className={styles.reason}>{legend.reason}</p>
                            {canInspect && (
                                <button
                                    type="button"
                                    className={styles.inspect}
                                    onClick={() => onInspectEntity?.(fishId)}
                                >
                                    Inspect {subjectLabel(legend)}
                                </button>
                            )}
                        </li>
                    );
                })}
            </ul>
        </section>
    );
}
