import { useEffect, useState } from 'react';
import { colors } from '../styles/theme';
import type { ForagingGymSummary, ObservatoryData } from '../types/skill';
import { describePredictionProvenance } from '../utils/observatoryProvenance';
import { styles } from './ForagingGymPanel.styles';

// Background evaluation can take a few seconds after a world starts; poll at
// this cadence while the observatory reports "no_data" so the panel picks up
// the result without the user having to close and reopen it.
const OBSERVATORY_POLL_INTERVAL_MS = 4000;

function percent(value: number): string {
    return `${(value * 100).toFixed(1)}%`;
}

function getSkillDescriptor(score: number): { label: string; description: string } {
    const val = score * 100;
    if (val >= 90) {
        return { label: 'EXPERT', description: 'Perfect or near-optimal route selection' };
    } else if (val >= 75) {
        return { label: 'ADVANCED', description: 'Highly efficient foraging and pathing' };
    } else if (val >= 60) {
        return { label: 'SKILLED', description: 'Efficiently finds most available food' };
    } else if (val >= 45) {
        return { label: 'BASIC', description: 'Basic target selection and food capture' };
    } else {
        return { label: 'POOR', description: 'Inefficient or struggling to locate food' };
    }
}

function formatSubject(subject: string): string {
    if (subject === 'engine_baseline') {
        return 'Engine baseline';
    }
    return subject
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

export function ForagingGymPanel({
    worldId,
    onSelectEntity
}: {
    worldId?: string;
    onSelectEntity?: (entityId: number, entityType: string) => void;
}) {
    const [summary, setSummary] = useState<ForagingGymSummary | null>(null);
    const [summaryError, setSummaryError] = useState<string | null>(null);
    const [summaryLoading, setSummaryLoading] = useState(true);
    const [observatory, setObservatory] = useState<ObservatoryData | null>(null);
    const [observatoryError, setObservatoryError] = useState<string | null>(null);
    const [observatoryLoading, setObservatoryLoading] = useState(true);

    // Independent of the observatory fetch below: a failure here must not
    // hide an observatory result that loaded fine, and vice versa.
    useEffect(() => {
        let active = true;
        async function fetchSummary() {
            setSummaryLoading(true);
            setSummaryError(null);
            try {
                const queryStr = worldId ? `?world_id=${encodeURIComponent(worldId)}` : '';
                const res = await fetch(`/api/skill/foraging-gym/summary${queryStr}`);
                if (!res.ok) throw new Error(`Failed to load summary (${res.status})`);
                const data: ForagingGymSummary = await res.json();
                if (active) {
                    setSummary(data);
                }
            } catch (cause) {
                if (active) {
                    setSummaryError(cause instanceof Error ? cause.message : 'Foraging summary unavailable');
                }
            } finally {
                if (active) {
                    setSummaryLoading(false);
                }
            }
        }
        fetchSummary();
        return () => {
            active = false;
        };
    }, [worldId]);

    // Background evaluation is asynchronous, so a freshly started world can
    // report "no_data" for a while - poll until a result actually arrives
    // instead of leaving the panel stuck on the pending message.
    useEffect(() => {
        let active = true;
        let timeoutId: ReturnType<typeof setTimeout> | undefined;

        async function pollObservatory() {
            try {
                const queryStr = worldId ? `?world_id=${encodeURIComponent(worldId)}` : '';
                const res = await fetch(`/api/skill/foraging-gym/observatory${queryStr}`);
                if (!res.ok) throw new Error(`Failed to load observatory (${res.status})`);
                const data: ObservatoryData = await res.json();
                if (!active) return;
                setObservatory(data);
                setObservatoryError(null);
                if (data.status === 'no_data') {
                    timeoutId = setTimeout(pollObservatory, OBSERVATORY_POLL_INTERVAL_MS);
                }
            } catch (cause) {
                if (active) {
                    setObservatoryError(cause instanceof Error ? cause.message : 'Observatory unavailable');
                }
            } finally {
                if (active) {
                    setObservatoryLoading(false);
                }
            }
        }
        setObservatoryLoading(true);
        pollObservatory();
        return () => {
            active = false;
            if (timeoutId !== undefined) {
                clearTimeout(timeoutId);
            }
        };
    }, [worldId]);

    if (summaryLoading || observatoryLoading) {
        return (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <section style={styles.panel} aria-label="Foraging gym evaluator">
                    <div style={styles.titleContainer}>
                        <div style={styles.title}>FORAGING SKILL</div>
                    </div>
                    <div style={styles.skeletonContainer} data-testid="skeleton">
                        <div style={styles.skeletonRow}>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                <div style={styles.skeletonScore} />
                                <div style={styles.skeletonDescription} />
                            </div>
                            <div style={styles.skeletonBadge} />
                        </div>
                        <div style={styles.skeletonTrack} />
                        <div style={styles.skeletonText} />
                    </div>
                </section>
                <section style={styles.panel} aria-label="Tank skill observatory">
                    <div style={styles.titleContainer}>
                        <div style={styles.title}>YOUR TANK'S FORAGING</div>
                    </div>
                    <div style={styles.skeletonContainer} data-testid="skeleton">
                        <div style={styles.skeletonRow}>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                <div style={styles.skeletonScore} />
                                <div style={styles.skeletonDescription} />
                            </div>
                            <div style={styles.skeletonBadge} />
                        </div>
                        <div style={styles.skeletonTrack} />
                        <div style={styles.skeletonText} />
                    </div>
                </section>
            </div>
        );
    }

    // Each half renders independently once its own fetch has settled - a
    // failure loading one must not hide a successfully loaded other.
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {observatory ? (
                <ForagingGymObservatoryDisplay observatory={observatory} onSelectEntity={onSelectEntity} />
            ) : (
                <section style={styles.panel} aria-label="Tank skill observatory">
                    <div style={styles.titleContainer}>
                        <div style={styles.title}>YOUR TANK'S FORAGING</div>
                    </div>
                    <div style={styles.error}>{observatoryError || 'Failed to load observatory'}</div>
                </section>
            )}
            {summary ? (
                <ForagingGymSummaryDisplay summary={summary} />
            ) : (
                <section style={styles.panel} aria-label="Foraging gym evaluator">
                    <div style={styles.titleContainer}>
                        <div style={styles.title}>FORAGING SKILL</div>
                    </div>
                    <div style={styles.error}>{summaryError || 'Failed to load summary'}</div>
                </section>
            )}
        </div>
    );
}

export function ForagingGymSummaryDisplay({ summary }: { summary: ForagingGymSummary }) {
    const [measuredOpen, setMeasuredOpen] = useState(false);
    const [techOpen, setTechOpen] = useState(false);

    const { mean, wandering_mean, perfect_mean, confidence_interval, range, average_food, average_energy } = summary;
    const descriptor = getSkillDescriptor(mean);

    const wPct = wandering_mean * 100;
    const cPct = mean * 100;
    const pPct = perfect_mean * 100;

    return (
        <section style={styles.panel} aria-label="Foraging gym evaluator">
            <div style={styles.titleContainer}>
                <div style={styles.title}>FORAGING SKILL</div>
            </div>

            <div style={styles.scoreRow}>
                <div style={styles.scoreLeft}>
                    <div style={styles.score}>
                        {Math.round(cPct)} <span style={styles.scoreDenom}>/ 100</span>
                    </div>
                    <div style={styles.descriptorText}>{descriptor.description}</div>
                </div>
                <div style={styles.badge}>{descriptor.label}</div>
            </div>

            {/* Comparison Scale */}
            <div style={styles.scaleContainer} aria-label="Comparison scale with three markers">
                {/* Labels Row */}
                <div style={styles.scaleLabels}>
                    <div style={{ ...styles.markerLabel, left: `${wPct}%`, transform: `translateX(${-wPct}%)` }}>
                        <span style={styles.markerName}>Wandering</span>
                    </div>
                    <div style={{ ...styles.markerLabel, left: `${cPct}%`, transform: `translateX(${-cPct}%)` }}>
                        <span style={{ ...styles.markerName, color: colors.success, fontWeight: 700 }}>
                            {formatSubject(summary.subject)}
                        </span>
                    </div>
                    <div style={{ ...styles.markerLabel, left: `${pPct}%`, transform: `translateX(${-pPct}%)` }}>
                        <span style={styles.markerName}>Perfect route</span>
                    </div>
                </div>

                {/* Track Line */}
                <div style={styles.trackLineContainer}>
                    <div style={styles.trackBackground} />
                    <div style={{ ...styles.trackDot, left: `${wPct}%` }} />
                    <div style={{ ...styles.trackDotActive, left: `${cPct}%` }} />
                    <div style={{ ...styles.trackDot, left: `${pPct}%` }} />
                </div>

                {/* Values Row */}
                <div style={styles.scaleValues}>
                    <div style={{ ...styles.markerValueLabel, left: `${wPct}%`, transform: `translateX(${-wPct}%)` }}>
                        <span style={styles.markerValue}>{Math.round(wPct)}</span>
                    </div>
                    <div style={{ ...styles.markerValueLabel, left: `${cPct}%`, transform: `translateX(${-cPct}%)` }}>
                        <span style={{ ...styles.markerValue, color: colors.success, fontWeight: 800 }}>
                            ● {Math.round(cPct)}
                        </span>
                    </div>
                    <div style={{ ...styles.markerValueLabel, left: `${pPct}%`, transform: `translateX(${-pPct}%)` }}>
                        <span style={styles.markerValue}>{Math.round(pPct)}</span>
                    </div>
                </div>
            </div>

            {/* Averages Summary */}
            <div style={styles.averagesInfo}>
                <div style={styles.averagesTitle}>Average across {summary.metadata.seeds.length} standardized trials</div>
                <div style={styles.averagesDetail}>
                    {average_food.toFixed(1)} of {summary.average_food_available} food collected · Trial range {Math.round(range[0] * 100)}–{Math.round(range[1] * 100)}
                </div>
            </div>

            {/* How this is measured details */}
            <details
                style={styles.details}
                open={measuredOpen}
                onToggle={(e) => setMeasuredOpen((e.target as HTMLDetailsElement).open)}
                data-testid="details-measurement"
            >
                <summary style={styles.summary}>
                    <span style={styles.arrowIcon}>{measuredOpen ? '▼' : '▶'}</span>
                    How this is measured
                </summary>
                <div style={styles.detailsContent}>
                    The foraging gym isolates food pursuit from ecosystem confounders (no predators,
                    reproduction, or population dynamics). A single neutral-policy fish chases scripted
                    food spawns that alternate between two lanes. Score is gross food energy captured
                    relative to an omniscient greedy oracle that always takes the optimal route.
                </div>
            </details>

            {/* Technical details */}
            <details
                style={styles.details}
                open={techOpen}
                onToggle={(e) => setTechOpen((e.target as HTMLDetailsElement).open)}
                data-testid="details-technical"
            >
                <summary style={styles.summary}>
                    <span style={styles.arrowIcon}>{techOpen ? '▼' : '▶'}</span>
                    Test details
                </summary>
                <div style={styles.detailsContent}>
                    <div style={styles.techRow}>
                        <span style={styles.techLabel}>Subject:</span>
                        <span style={styles.techVal}>{summary.subject}</span>
                    </div>
                    <div style={styles.techRow}>
                        <span style={styles.techLabel}>Benchmark ID:</span>
                        <span style={styles.techVal}>{summary.benchmark_id}</span>
                    </div>
                    <div style={styles.techRow}>
                        <span style={styles.techLabel}>Config Hash:</span>
                        <span style={styles.techVal}>{summary.config_hash}</span>
                    </div>
                    <div style={styles.techRow}>
                        <span style={styles.techLabel}>Confidence Interval (95%):</span>
                        <span style={styles.techVal}>
                            {percent(confidence_interval[0])} to {percent(confidence_interval[1])}
                        </span>
                    </div>
                    <div style={styles.techRow}>
                        <span style={styles.techLabel}>Average Energy Captured:</span>
                        <span style={styles.techVal}>{Math.round(average_energy).toLocaleString()}</span>
                    </div>

                    <div style={{ ...styles.averagesTitle, marginTop: '12px', marginBottom: '6px' }}>Per-Seed Trials</div>
                    <table style={styles.table}>
                        <thead>
                            <tr>
                                <th style={styles.th}>Seed</th>
                                <th style={styles.th}>Score</th>
                                <th style={styles.th}>Food</th>
                                <th style={styles.th}>Energy</th>
                            </tr>
                        </thead>
                        <tbody>
                            {summary.metadata.seeds.map(seed => {
                                const seedStr = String(seed);
                                const seedData = summary.metadata.per_seed[seedStr];
                                if (!seedData) return null;
                                return (
                                    <tr key={seed} style={styles.tr}>
                                        <td style={styles.td}>{seed}</td>
                                        <td style={styles.td}>{percent(seedData.score)}</td>
                                        <td style={styles.td}>
                                            {seedData.metadata.composable.food_collected} / {seedData.metadata.oracle.food_collected}
                                        </td>
                                        <td style={styles.td}>
                                            {Math.round(seedData.metadata.composable.energy_collected)} / {Math.round(seedData.metadata.oracle_energy)}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </details>
        </section>
    );
}

export function ForagingGymObservatoryDisplay({
    observatory,
    onSelectEntity,
}: {
    observatory: ObservatoryData;
    onSelectEntity?: (entityId: number, entityType: string) => void;
}) {
    if (observatory.status === 'no_data') {
        return (
            <section style={styles.panel} aria-label="Tank skill observatory">
                <div style={styles.titleContainer}>
                    <div style={styles.title}>YOUR TANK'S FORAGING</div>
                </div>
                <div style={styles.detailsContent}>
                    {observatory.message || 'No evolved fish available to evaluate yet.'}
                </div>
            </section>
        );
    }

    const bPct = (observatory.best_species?.score ?? 0) * 100;
    const aPct = (observatory.tank_average ?? 0) * 100;
    const cPct = (observatory.engine_baseline ?? 0) * 100;
    const wPct = (observatory.wandering_mean ?? 0) * 100;
    const pPct = (observatory.perfect_mean ?? 0) * 100;

    return (
        <section style={styles.panel} aria-label="Tank skill observatory">
            <div style={styles.titleContainer}>
                <div style={styles.title}>YOUR TANK'S FORAGING</div>
                {observatory.subject && (
                    <div style={{ fontSize: '10px', color: '#94a3b8', marginTop: '2px', fontWeight: 500 }}>
                        EVALUATED SUBJECT: {observatory.subject.toUpperCase()}
                    </div>
                )}
                {observatory.evaluated_at_generation !== undefined && (
                    <div style={{ fontSize: '10px', color: '#94a3b8', marginTop: '2px' }}>
                        Evaluated at generation {observatory.evaluated_at_generation} · frame {observatory.evaluated_at_frame ?? 0}
                    </div>
                )}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', margin: '8px 0' }}>
                {/* Best species */}
                {observatory.best_species && (
                    <div style={styles.barRow}>
                        <div style={styles.barLabel}>Best species ({observatory.best_species.name})</div>
                        <div style={styles.barTrack}>
                            <div style={{ ...styles.barFill, width: `${bPct}%`, backgroundColor: colors.buttonSecondary }} />
                        </div>
                        <div style={styles.barValue}>{Math.round(bPct)}</div>
                    </div>
                )}

                {/* Tank average */}
                <div style={styles.barRow}>
                    <div style={styles.barLabel}>Tank average</div>
                    <div style={styles.barTrack}>
                        <div style={{ ...styles.barFill, width: `${aPct}%`, backgroundColor: colors.primary }} />
                    </div>
                    <div style={styles.barValue}>{Math.round(aPct)}</div>
                </div>

                {/* Default controller */}
                <div style={styles.barRow}>
                    <div style={styles.barLabel}>Default controller</div>
                    <div style={styles.barTrack}>
                        <div style={{ ...styles.barFill, width: `${cPct}%`, backgroundColor: colors.success }} />
                    </div>
                    <div style={styles.barValue}>{Math.round(cPct)}</div>
                </div>

                {/* Wandering */}
                <div style={styles.barRow}>
                    <div style={styles.barLabel}>Wandering</div>
                    <div style={styles.barTrack}>
                        <div style={{ ...styles.barFill, width: `${wPct}%`, backgroundColor: colors.textSecondary }} />
                    </div>
                    <div style={styles.barValue}>{Math.round(wPct)}</div>
                </div>

                {/* Perfect route */}
                <div style={styles.barRow}>
                    <div style={styles.barLabel}>Perfect route</div>
                    <div style={styles.barTrack}>
                        <div style={{ ...styles.barFill, width: `${pPct}%`, backgroundColor: colors.buttonSuccess }} />
                    </div>
                    <div style={styles.barValue}>{Math.round(pPct)}</div>
                </div>
            </div>

            {observatory.best_individual && (
                <div style={styles.observatoryBest}>
                    <div style={styles.observatoryBestTitle}>BEST FORAGER:</div>
                    <div
                        style={onSelectEntity ? styles.clickableLink : styles.nonClickableText}
                        onClick={() => onSelectEntity?.(observatory.best_individual!.id, 'fish')}
                    >
                        {observatory.best_individual.name}
                    </div>
                    <div style={styles.observatoryBestDetail}>
                        Captured {observatory.best_individual.food_collected.toFixed(1)} of {observatory.best_individual.food_available} food items (uncertainty: ±{observatory.best_individual.score_uncertainty.toFixed(3)}, n={observatory.best_individual.sample_size})
                    </div>
                    <div style={styles.observatoryBestDetail}>
                        {describePredictionProvenance(observatory.best_individual)}
                    </div>
                    <div style={styles.observatoryBestDetail}>
                        Species median prediction skill: {observatory.best_individual.species_median.toFixed(2)}
                    </div>
                    <div style={styles.observatoryBestDetail}>
                        This module variant (fingerprint: {observatory.best_individual.module_fingerprint}) is present in {Math.round(observatory.best_individual.similar_fraction * 100)}% of its species
                    </div>
                </div>
            )}
        </section>
    );
}
