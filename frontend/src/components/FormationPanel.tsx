import type { SoccerMatchState } from '../types/simulation';
import type { FormationMetrics } from '../hooks/useFormationMetrics';
import type { TeamShape } from './soccerFormation';
import { sideDisplayName } from './soccerParticipantLabels';
import styles from './FormationPanel.module.css';

function ShapeBlock({ label, side, shape, chains, longest }: { label: string; side: 'left' | 'right'; shape: TeamShape; chains: number; longest: number }) {
    return (
        <section className={styles.team} aria-label={`${label} formation`}>
            <div className={styles.teamHeading}>
                <span className={`${styles.sideDot} ${side === 'left' ? styles.sideLeft : styles.sideRight}`} aria-hidden="true" />
                <h4>{label}</h4>
            </div>
            <dl className={styles.metrics}>
                <div className={styles.metric}>
                    <dt>Shape area</dt>
                    <dd>{shape.areaM2.toFixed(0)} m²</dd>
                </div>
                <div className={styles.metric}>
                    <dt>Mean x</dt>
                    <dd>{shape.meanX >= 0 ? '+' : ''}{shape.meanX.toFixed(1)} m</dd>
                </div>
                <div className={styles.metric}>
                    <dt>Depth</dt>
                    <dd>{shape.widthM.toFixed(1)} m</dd>
                </div>
                <div className={styles.metric}>
                    <dt>Chains</dt>
                    <dd>{chains}{longest > 0 ? ` · max ${longest}` : ''}</dd>
                </div>
            </dl>
        </section>
    );
}

/**
 * §4.1 Formation & Spacing rail.
 *
 * Every number here is derived on the client from positions already on the
 * wire; nothing is fetched and nothing is asked of the backend. Metrics read
 * `—` until the window has samples rather than showing a confident 0.
 */
export function FormationPanel({ match, metrics }: { match: SoccerMatchState | null; metrics: FormationMetrics }) {
    const hasSamples = metrics.sampledFrames > 0;

    return (
        <div className={styles.panel} data-testid="soccer-formation-panel">
            <div className={styles.heading}>
                <h3>Formation &amp; Spacing</h3>
                <span className={styles.label}>Tactical</span>
            </div>
            {!hasSamples ? (
                <p className={styles.empty}>Sampling play — metrics appear once the match is running.</p>
            ) : (
                <>
                    <ShapeBlock
                        label={sideDisplayName(match, 'left')}
                        side="left"
                        shape={metrics.left}
                        chains={metrics.chains.left}
                        longest={metrics.chains.longestLeft}
                    />
                    <ShapeBlock
                        label={sideDisplayName(match, 'right')}
                        side="right"
                        shape={metrics.right}
                        chains={metrics.chains.right}
                        longest={metrics.chains.longestRight}
                    />
                    <p className={styles.footnote}>
                        Rolling window of {metrics.sampledFrames} frames. Roles are derived from mean position, not assigned
                        by the simulation.
                    </p>
                </>
            )}
        </div>
    );
}
