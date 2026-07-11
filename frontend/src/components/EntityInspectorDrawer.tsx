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
}: EntityInspectorDrawerProps) {
    const [fetchState, setFetchState] = useState<FetchState>({ phase: 'loading' });
    const drawerRef = useRef<HTMLDivElement>(null);
    const requestSeqRef = useRef(0);

    const fetchDetails = useCallback(() => {
        const seq = ++requestSeqRef.current;
        setFetchState({ phase: 'loading' });
        sendCommandWithResponse({
            command: 'get_entity_details',
            data: { entity_id: entityId },
        })
            .then((response) => {
                if (seq !== requestSeqRef.current) return; // stale response
                if (response.success && response.details) {
                    setFetchState({ phase: 'loaded', details: response.details });
                } else if (response.error === 'entity_not_found') {
                    setFetchState({ phase: 'not_found' });
                } else {
                    setFetchState({ phase: 'error', message: response.error ?? 'Unknown error' });
                }
            })
            .catch((err: unknown) => {
                if (seq !== requestSeqRef.current) return;
                const message = err instanceof Error ? err.message : 'Request failed';
                setFetchState({ phase: 'error', message });
            });
    }, [entityId, sendCommandWithResponse]);

    useEffect(() => {
        fetchDetails();
    }, [fetchDetails]);

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
                        <Button variant="secondary" onClick={fetchDetails} disabled={!isConnected}>
                            Retry
                        </Button>
                    </div>
                )}

                {details?.behavior && (
                    <section className={styles.section} aria-label="Behavior">
                        <h3 className={styles.sectionTitle}>Behavior</h3>
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
