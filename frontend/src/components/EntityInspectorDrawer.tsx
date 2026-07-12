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
import type { PursuitOverlayData } from '../rendering/types';
import { Button, StatRow } from './ui';
import {
    STATUS_COPY,
    energyBarColor,
    entityTypeLabel,
    formatOrigin,
    formatSpecies,
    formatTraitName,
} from './entityInspectorFormat';
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
}

type FetchState =
    | { phase: 'loading' }
    | { phase: 'loaded'; details: EntityDetails }
    | { phase: 'not_found' }
    | { phase: 'error'; message: string };

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
}: EntityInspectorDrawerProps) {
    const [fetchState, setFetchState] = useState<FetchState>({ phase: 'loading' });
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
    }, [entityId, sendCommandWithResponse, onPursuitOverlayChange]);

    useEffect(() => {
        fetchDetails();
    }, [fetchDetails]);

    // Clear the overlay when the drawer closes or switches to a different entity.
    useEffect(() => {
        return () => onPursuitOverlayChange?.(null);
    }, [entityId, onPursuitOverlayChange]);

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

    const details = fetchState.phase === 'loaded' ? fetchState.details : null;
    const isGone = entity === null || fetchState.phase === 'not_found';
    const canTransfer =
        TRANSFERABLE_TYPES.has(entityType) && !isGone && isConnected;

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
                {isGone && (
                    <div className={styles.goneBanner} role="status">
                        No longer in the world — it may have died or been transferred.
                    </div>
                )}

                {details?.status && !isGone && (
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

                {details?.modules && (
                    <section className={styles.section} aria-label="Modules">
                        <h3 className={styles.sectionTitle}>Modules</h3>
                        <p className={styles.intent}>{details.modules.name}</p>
                        <StatRow label="Used for" value={details.modules.used_for.join(', ')} />
                        <StatRow
                            label="Speed calibration"
                            value={details.modules.parameters.speed_multiplier.toFixed(2)}
                        />
                        <StatRow
                            label="Prediction strength"
                            value={details.modules.parameters.prediction_strength.toFixed(2)}
                        />
                        <StatRow
                            label="Max prediction horizon"
                            value={details.modules.parameters.max_prediction_horizon.toFixed(0)}
                        />
                        <StatRow
                            label="Pursuit commitment"
                            value={details.modules.parameters.pursuit_commitment.toFixed(2)}
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
                        disabled={isGone}
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
