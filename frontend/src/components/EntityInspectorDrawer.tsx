/**
 * EntityInspectorDrawer — answers "what is this creature doing?" (U4/E1).
 *
 * Opens when an entity is clicked on the canvas. Shows live vitals from the
 * broadcast state plus on-demand details fetched via `get_entity_details`.
 * Transfer is an explicit secondary action here, never a click side effect.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type { Command, CommandResponse, EntityData } from '../types/simulation';
import type { EntityDetails } from '../types/entityDetails';
import type { PursuitOverlayData, TargetMemoryOverlayData } from '../rendering/types';
import { Button, StatRow } from './ui';
import {
    STATUS_COPY,
    energyBarColor,
    entityTypeLabel,
    formatOrigin,
    formatSpecies,
    formatTraitName,
} from './entityInspectorFormat';
import type { ParameterEvolutionData } from '../types/entityDetails';
import styles from './EntityInspectorDrawer.module.css';

interface EntityInspectorDrawerProps {
    entityId: number;
    entityType: string;
    /** Live broadcast snapshot of the entity; null when it left the world. */
    entity: EntityData | null;
    isConnected: boolean;
    sendCommandWithResponse: (command: Command) => Promise<CommandResponse>;
    onClose: () => void;
    onRequestTransfer: () => void;
    followEnabled: boolean;
    onToggleFollow: () => void;
    /** Fires whenever fetched pursuit-module vectors change, for the canvas overlay. */
    onPursuitOverlayChange?: (data: PursuitOverlayData | null) => void;
    /** Fires whenever fetched target memory vectors change, for the canvas overlay. */
    onTargetMemoryOverlayChange?: (data: TargetMemoryOverlayData | null) => void;
    /** Optional initial fetch state for SSR/unit tests (Point 5). */
    initialFetchState?: FetchState;
}

type FetchState =
    | { phase: 'loading' }
    | { phase: 'loaded'; details: EntityDetails }
    | { phase: 'not_found' }
    | { phase: 'error'; message: string };

interface ParameterEvolutionRowProps {
    label: string;
    currentValue: number;
    evolutionData?: ParameterEvolutionData | null;
    isInteger?: boolean;
}

function ParameterEvolutionRow({
    label,
    currentValue,
    evolutionData,
    isInteger = false,
}: ParameterEvolutionRowProps) {
    const formattedVal = isInteger ? currentValue.toFixed(0) : currentValue.toFixed(2);

    if (!evolutionData) {
        return <StatRow label={label} value={formattedVal} />;
    }

    const { parent, species_median, carriers_pct, trend } = evolutionData;

    const trendText = trend === 'increasing' ? 'rising' : trend === 'declining' ? 'falling' : 'stable';
    const parentText = parent !== null ? (isInteger ? parent.toFixed(0) : parent.toFixed(2)) : 'N/A';
    const medianText = isInteger ? species_median.toFixed(0) : species_median.toFixed(2);

    return (
        <div className={styles.paramEvolutionContainer}>
            <div className={styles.paramHeader}>
                <span className={styles.paramLabel}>{label}</span>
                <span className={styles.paramValue}>{formattedVal}</span>
            </div>
            <div className={styles.paramSubDetails}>
                <div>Parent: {parentText} | Species median: {medianText}</div>
                <div>Present in {carriers_pct.toFixed(0)}% of the population and {trendText}</div>
            </div>
        </div>
    );
}

const TRANSFERABLE_TYPES = new Set(['fish', 'plant']);

export function EntityInspectorDrawer({
    entityId,
    entityType,
    entity,
    isConnected,
    sendCommandWithResponse,
    onClose,
    onRequestTransfer,
    followEnabled,
    onToggleFollow,
    onPursuitOverlayChange,
    onTargetMemoryOverlayChange,
    initialFetchState,
}: EntityInspectorDrawerProps) {
    const [fetchState, setFetchState] = useState<FetchState>(initialFetchState || { phase: 'loading' });
    const drawerRef = useRef<HTMLDivElement>(null);
    const requestSeqRef = useRef(0);

    const fetchDetails = useCallback((quiet = false) => {
        const seq = ++requestSeqRef.current;
        if (!quiet) setFetchState({ phase: 'loading' });
        sendCommandWithResponse({
            command: 'get_entity_details',
            data: { entity_id: entityId },
        })
            .then((response) => {
                if (seq !== requestSeqRef.current) return; // stale response
                if (response.success && response.details) {
                    setFetchState({ phase: 'loaded', details: response.details });
                    const modules = response.details.modules;
                    onPursuitOverlayChange?.(
                        modules
                            ? { targetVector: modules.target_vector, aimVector: modules.aim_vector }
                            : null
                    );
                    const mem = response.details.target_memory;
                    let chosenDomainData = null;
                    let chosenDomainName = '';
                    if (mem && mem.domains) {
                        const { food, ball } = mem.domains;
                        if (food?.influencing_movement) {
                            chosenDomainData = food;
                            chosenDomainName = 'food';
                        } else if (ball?.influencing_movement) {
                            chosenDomainData = ball;
                            chosenDomainName = 'ball';
                        } else if (food && food.action_raw !== 'idle' && food.action_raw !== 'drop') {
                            chosenDomainData = food;
                            chosenDomainName = 'food';
                        } else if (ball && ball.action_raw !== 'idle' && ball.action_raw !== 'drop') {
                            chosenDomainData = ball;
                            chosenDomainName = 'ball';
                        } else {
                            chosenDomainData = food || ball || null;
                            chosenDomainName = food ? 'food' : (ball ? 'ball' : '');
                        }
                    }

                    let domainRecentEvent = null;
                    if (mem) {
                        if (mem.recent_events && chosenDomainName && mem.recent_events[chosenDomainName]) {
                            domainRecentEvent = mem.recent_events[chosenDomainName];
                        } else {
                            domainRecentEvent = mem.recent_event;
                        }
                    }

                    onTargetMemoryOverlayChange?.(
                        chosenDomainData
                            ? {
                                  domain: chosenDomainData.domain,
                                  action: chosenDomainData.action,
                                  lastSeenPosition: chosenDomainData.last_seen_position,
                                  predictedPosition: chosenDomainData.predicted_position,
                                  searchVector: chosenDomainData.search_vector,
                                  confidence: chosenDomainData.confidence_raw,
                                  recentEvent: domainRecentEvent
                                      ? {
                                            domain: domainRecentEvent.domain,
                                            action: domainRecentEvent.action,
                                            ageFrames: domainRecentEvent.age_frames,
                                        }
                                      : null,
                              }
                            : null
                    );
                } else if (response.error === 'entity_not_found') {
                    setFetchState({ phase: 'not_found' });
                    onPursuitOverlayChange?.(null);
                } else {
                    setFetchState({ phase: 'error', message: response.error ?? 'Unknown error' });
                }
            })
            .catch((err: unknown) => {
                if (seq !== requestSeqRef.current) return;
                const message = err instanceof Error ? err.message : 'Request failed';
                setFetchState({ phase: 'error', message });
            });
    }, [entityId, sendCommandWithResponse, onPursuitOverlayChange, onTargetMemoryOverlayChange]);

    useEffect(() => {
        fetchDetails();
    }, [fetchDetails]);

    // Clear the overlay when the drawer closes or switches to a different entity.
    useEffect(() => {
        return () => {
            onPursuitOverlayChange?.(null);
            onTargetMemoryOverlayChange?.(null);
        };
    }, [entityId, onPursuitOverlayChange, onTargetMemoryOverlayChange]);

    useEffect(() => {
        if (!isConnected || entityType !== 'fish') return;
        const timer = window.setInterval(() => fetchDetails(true), 500);
        return () => window.clearInterval(timer);
    }, [entityType, fetchDetails, isConnected]);

    // Focus the drawer on open; hand focus back where it was on close.
    useEffect(() => {
        const previouslyFocused = document.activeElement;
        drawerRef.current?.focus();
        return () => {
            if (previouslyFocused instanceof HTMLElement) {
                previouslyFocused.focus();
            }
        };
    }, [entityId]);

    const handleKeyDown = (event: React.KeyboardEvent) => {
        if (event.key === 'Escape') {
            event.stopPropagation();
            onClose();
        }
    };

    const isGone = entity === null || fetchState.phase === 'not_found';

    // A gone entity has nothing left to inspect — collapse to a small card
    // instead of the full-size drawer with an empty body (U4/E1 follow-up).
    if (isGone) {
        return (
            <div
                ref={drawerRef}
                className={styles.goneCard}
                role="dialog"
                aria-label={`${entityTypeLabel(entityType)} inspector`}
                tabIndex={-1}
                onKeyDown={handleKeyDown}
            >
                <header className={styles.header}>
                    <div className={styles.headerTitle}>
                        <span className={styles.entityType}>{entityTypeLabel(entityType)}</span>
                        <span className={styles.entityId}>{`#${entityId}`}</span>
                    </div>
                    <button
                        className={styles.closeButton}
                        onClick={onClose}
                        aria-label="Close inspector"
                        title="Close inspector (Esc)"
                    >
                        ×
                    </button>
                </header>
                <div className={styles.goneCardBody}>
                    <div className={styles.goneBanner} role="status">
                        No longer in the world — it may have died or been transferred.
                    </div>
                </div>
            </div>
        );
    }

    const details = fetchState.phase === 'loaded' ? fetchState.details : null;
    const canTransfer = TRANSFERABLE_TYPES.has(entityType) && isConnected;

    // Prefer live broadcast values so vitals update in real time.
    const energy = entity?.energy ?? details?.energy;
    const maxEnergy = entity?.max_energy ?? details?.max_energy;
    const energyRatio =
        energy !== undefined && maxEnergy !== undefined && maxEnergy > 0
            ? energy / maxEnergy
            : details?.energy_ratio;
    const age = entity?.age ?? details?.age;
    const generation = entity?.generation ?? details?.generation;
    const taxonomy = details?.taxonomy ?? (entity?.taxon_id ? {
        taxon_id: entity.taxon_id,
        common_name: entity.common_name ?? '',
        scientific_name: entity.scientific_name ?? '',
        status: entity.species_confidence ?? 'provisional',
        strain_id: entity.strain_id ?? null,
    } : null);

    return (
        <div
            ref={drawerRef}
            className={styles.drawer}
            role="dialog"
            aria-label={`${entityTypeLabel(entityType)} inspector`}
            tabIndex={-1}
            onKeyDown={handleKeyDown}
        >
            <header className={styles.header}>
                <div className={styles.headerTitle}>
                    <span className={styles.entityType}>{entityTypeLabel(entityType)}</span>
                    <span className={styles.entityId}>{`#${entityId}`}</span>
                    {generation !== undefined && (
                        <span className={styles.generationBadge}>{`Gen ${generation}`}</span>
                    )}
                </div>
                <button
                    className={styles.closeButton}
                    onClick={onClose}
                    aria-label="Close inspector"
                    title="Close inspector (Esc)"
                >
                    ×
                </button>
            </header>

            <div className={styles.body}>
                {details?.status && (
                    <p className={styles.statusLine}>
                        {STATUS_COPY[details.status] ?? details.status}
                        {details.reproduction?.is_gravid ? ' · carrying an egg' : ''}
                    </p>
                )}

                {energy !== undefined && maxEnergy !== undefined && (
                    <section className={styles.section} aria-label="Vital signs">
                        <h3 className={styles.sectionTitle}>Vitals</h3>
                        <div
                            className={styles.energyBar}
                            role="meter"
                            aria-label="Energy"
                            aria-valuemin={0}
                            aria-valuemax={Math.round(maxEnergy)}
                            aria-valuenow={Math.round(energy)}
                        >
                            <div
                                className={styles.energyFill}
                                style={{
                                    width: `${Math.min(100, Math.max(0, (energyRatio ?? 0) * 100))}%`,
                                    background: energyBarColor(energyRatio ?? 0),
                                }}
                            />
                        </div>
                        <StatRow
                            label="Energy"
                            value={`${Math.round(energy)} / ${Math.round(maxEnergy)}`}
                        />
                        {age !== undefined && (
                            <StatRow
                                label="Age"
                                value={
                                    details?.max_age
                                        ? `${age.toLocaleString()} / ${details.max_age.toLocaleString()} frames`
                                        : `${age.toLocaleString()} frames`
                                }
                            />
                        )}
                        {details?.life_stage && (
                            <StatRow label="Life stage" value={details.life_stage} />
                        )}
                    </section>
                )}

                {fetchState.phase === 'loading' && (
                    <p className={styles.stateMessage}>Loading details…</p>
                )}
                {fetchState.phase === 'error' && (
                    <div className={styles.stateMessage} role="alert">
                        <p>Could not load details: {fetchState.message}</p>
                        <Button variant="secondary" onClick={() => fetchDetails()} disabled={!isConnected}>
                            Retry
                        </Button>
                    </div>
                )}

                {details?.behavior && (
                    <section className={styles.section} aria-label="Behavior">
                        <h3 className={styles.sectionTitle}>Behavior</h3>
                        {details.behavior.lens && (
                            <div className={styles.behaviorLens} aria-label="Current decision">
                                <p className={styles.intent}>{details.behavior.lens.intent}</p>
                                <StatRow
                                    label="Target"
                                    value={details.behavior.lens.target ?? 'No current target'}
                                />
                                <StatRow
                                    label="Output"
                                    value={formatVector(details.behavior.lens.output)}
                                />
                                {Object.entries(details.behavior.lens.contributions)
                                    .filter(([, weight]) => weight > 0)
                                    .map(([module, weight]) => (
                                        <StatRow
                                            key={module}
                                            label={formatTraitName(module)}
                                            value={`${Math.round(weight * 100)}% contribution`}
                                        />
                                    ))}
                                {(details.behavior.lens.cancellation ?? 0) > 0 && (
                                    <StatRow
                                        label="Vector cancellation"
                                        value={`${Math.round((details.behavior.lens.cancellation ?? 0) * 100)}%`}
                                    />
                                )}
                                <details className={styles.graphDetails}>
                                    <summary>Behavior graph</summary>
                                    <p className={styles.graphFingerprint}>
                                        Graph {details.behavior.lens.fingerprint}
                                    </p>
                                    <ul>
                                        {details.behavior.lens.graph.nodes.map((node) => (
                                            <li key={node.id}>{`${node.id}: ${node.type}`}</li>
                                        ))}
                                        {Object.entries(details.behavior.lens.explanations).map(
                                            ([node, explanation]) => (
                                                <li key={`${node}-explanation`}>
                                                    {`${node}: ${Object.entries(explanation)
                                                        .map(([key, value]) => `${key}=${String(value)}`)
                                                        .join(', ')}`}
                                                </li>
                                            ),
                                        )}
                                    </ul>
                                </details>
                            </div>
                        )}
                        {details.behavior.movement_intent?.chosen && (
                            <div className={styles.movementIntent} aria-label="Chosen movement intent">
                                <p className={styles.intent}>
                                    {formatTraitName(details.behavior.movement_intent.chosen.kind)}
                                </p>
                                <StatRow
                                    label="Source"
                                    value={formatTraitName(details.behavior.movement_intent.chosen.source)}
                                />
                                <StatRow
                                    label="Urgency"
                                    value={`${Math.round(details.behavior.movement_intent.chosen.urgency * 100)}%`}
                                />
                                {/* Confidence omitted: no controller computes a defensible value yet. */}
                                {details.behavior.movement_intent.chosen.target_id !== null && (
                                    <StatRow
                                        label="Target"
                                        value={`#${details.behavior.movement_intent.chosen.target_id}`}
                                    />
                                )}
                                {details.behavior.movement_intent.suppressed_sources.length > 0 && (
                                    <p className={styles.suppressedSources}>
                                        Lower-priority sources not evaluated:{' '}
                                        {details.behavior.movement_intent.suppressed_sources
                                            .map(formatTraitName)
                                            .join(', ')}
                                    </p>
                                )}
                            </div>
                        )}
                        {details.behavior.algorithm && (
                            <StatRow label="Algorithm" value={details.behavior.algorithm} />
                        )}
                        {details.behavior.parameters &&
                            Object.entries(details.behavior.parameters).slice(0, 6).map(([key, value]) => (
                                <StatRow
                                    key={key}
                                    label={formatTraitName(key)}
                                    value={typeof value === 'number' ? value.toFixed(2) : String(value)}
                                />
                            ))}
                    </section>
                )}

                {details?.target_memory?.domains && (
                    <section className={styles.section} aria-label="Target Memory">
                        <h3 className={styles.sectionTitle}>Target Memory</h3>
                        {Object.entries(details.target_memory.domains).map(([domainKey, domainData]) => {
                            if (!domainData) return null;
                            const isInfluencing = domainData.influencing_movement;
                            const isActive = domainData.action_raw !== 'idle' && domainData.action_raw !== 'drop';

                            let statusLabel = 'Inactive';
                            let statusClass = styles.statusInactive;
                            if (isInfluencing) {
                                statusLabel = 'Influencing Movement';
                                statusClass = styles.statusInfluencing;
                            } else if (isActive) {
                                statusLabel = 'Tracking in Background';
                                statusClass = styles.statusBackground;
                            }

                            return (
                                <div key={domainKey} className={`${styles.domainBlock} ${isInfluencing ? styles.domainInfluencing : ''}`}>
                                    <div className={styles.domainHeader}>
                                        <span className={styles.domainName}>{domainData.domain} Memory</span>
                                        <span className={`${styles.statusBadge} ${statusClass}`}>{statusLabel}</span>
                                    </div>
                                    <div className={styles.domainDetails}>
                                        <StatRow label="Remembering" value={domainData.remembering} />
                                        <StatRow label="Action" value={domainData.action} />
                                        {isActive && (
                                            <>
                                                <StatRow label="Last seen" value={domainData.last_seen} />
                                                <StatRow label="Confidence" value={domainData.confidence} />
                                                <StatRow label="Predicted location" value={domainData.predicted_location} />
                                                <StatRow label="Switch threshold" value={domainData.switch_threshold} />
                                                {domainData.candidate_value !== undefined && domainData.candidate_value !== null && (
                                                    <StatRow
                                                        label="Value comparison"
                                                        value={`Cand: ${domainData.candidate_value.toFixed(1)} vs Thresh: ${(domainData.remembered_effective_value ?? 0).toFixed(1)}`}
                                                    />
                                                )}
                                            </>
                                        )}
                                        <StatRow label="Memory duration" value={`${domainData.memory_duration} frames`} />
                                    </div>
                                </div>
                            );
                        })}
                    </section>
                )}

                {details?.modules && (
                    <section className={styles.section} aria-label="Modules">
                        <h3 className={styles.sectionTitle}>Modules</h3>
                        <p className={styles.intent}>{details.modules.name}</p>
                        <StatRow label="Used for" value={details.modules.used_for.join(', ')} />
                        <ParameterEvolutionRow
                            label="Speed calibration"
                            currentValue={details.modules.parameters.speed_multiplier}
                            evolutionData={details.modules.parameters_evolution?.speed_multiplier}
                        />
                        <ParameterEvolutionRow
                            label="Prediction strength"
                            currentValue={details.modules.parameters.prediction_strength}
                            evolutionData={details.modules.parameters_evolution?.prediction_strength}
                        />
                        <ParameterEvolutionRow
                            label="Max prediction horizon"
                            currentValue={details.modules.parameters.max_prediction_horizon}
                            evolutionData={details.modules.parameters_evolution?.max_prediction_horizon}
                            isInteger={true}
                        />
                        <ParameterEvolutionRow
                            label="Pursuit commitment"
                            currentValue={details.modules.parameters.pursuit_commitment}
                            evolutionData={details.modules.parameters_evolution?.pursuit_commitment}
                        />
                        <StatRow
                            label="Current target"
                            value={details.modules.current_target ?? 'None'}
                        />
                        {details.modules.aim_vector && (
                            <StatRow
                                label="Predicted intercept vector"
                                value={formatVector(details.modules.aim_vector)}
                            />
                        )}
                        <StatRow
                            label="Inherited from"
                            value={formatOrigin(details.modules.inherited_from, details.generation)}
                        />
                    </section>
                )}

                {details?.lineage && (
                    <section className={styles.section} aria-label="Lineage">
                        <h3 className={styles.sectionTitle}>Lineage</h3>
                        <StatRow
                            label="Origin"
                            value={formatOrigin(details.lineage.parent_id, details.generation)}
                        />
                        {details.species && (
                            <StatRow label="Species" value={formatSpecies(details.species)} />
                        )}
                    </section>
                )}

                {taxonomy && (
                    <section className={styles.section} aria-label="Taxonomy">
                        <h3 className={styles.sectionTitle}>Taxonomy</h3>
                        {taxonomy.common_name && <p className={styles.commonName}>{taxonomy.common_name}</p>}
                        {taxonomy.scientific_name && (
                            <p className={styles.scientificName}>{taxonomy.scientific_name}</p>
                        )}
                        <StatRow label="Status" value={taxonomy.status} />
                        <StatRow label="Taxon" value={taxonomy.taxon_id} />
                        {taxonomy.strain_id && <StatRow label="Strain" value={taxonomy.strain_id} />}
                    </section>
                )}

                {details?.traits && Object.keys(details.traits).length > 0 && (
                    <section className={styles.section} aria-label="Traits">
                        <h3 className={styles.sectionTitle}>Traits</h3>
                        {Object.entries(details.traits).map(([key, value]) => (
                            <StatRow key={key} label={formatTraitName(key)} value={value.toFixed(2)} />
                        ))}
                    </section>
                )}

                {details?.games && (
                    <section className={styles.section} aria-label="Games">
                        <h3 className={styles.sectionTitle}>Games</h3>
                        <StatRow
                            label="Poker"
                            value={
                                details.games.poker.eligible
                                    ? 'Ready to play'
                                    : details.games.poker.cooldown_frames > 0
                                        ? `Cooling down (${details.games.poker.cooldown_frames})`
                                        : 'Not eligible'
                            }
                        />
                        <StatRow
                            label="Ball play"
                            value={
                                !details.games.soccer.ball_present
                                    ? 'No ball in tank'
                                    : details.games.soccer.eligible
                                        ? 'Has surplus energy to play'
                                        : 'Saving energy'
                            }
                        />
                    </section>
                )}
            </div>

            {TRANSFERABLE_TYPES.has(entityType) && (
                <footer className={styles.footer}>
                    <Button
                        variant={followEnabled ? 'primary' : 'secondary'}
                        onClick={onToggleFollow}
                        aria-pressed={followEnabled}
                        title={followEnabled ? 'Stop following this organism' : 'Keep this organism in view'}
                    >
                        {followEnabled ? 'Following' : 'Follow'}
                    </Button>
                    <Button
                        variant="secondary"
                        onClick={onRequestTransfer}
                        disabled={!canTransfer}
                        title={
                            canTransfer
                                ? 'Move this entity to another world'
                                : 'Transfer unavailable'
                        }
                    >
                        Transfer to another world…
                    </Button>
                </footer>
            )}
        </div>
    );
}

function formatVector(value: unknown): string {
    if (Array.isArray(value) && value.length === 2 && value.every((item) => typeof item === 'number')) {
        return `${value[0].toFixed(2)}, ${value[1].toFixed(2)}`;
    }
    return String(value ?? '—');
}
