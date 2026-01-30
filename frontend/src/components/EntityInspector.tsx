/**
 * Entity Inspector - slide-in side panel showing detailed data
 * for a selected entity (fish, plant, or crab).
 */

import { useState, useEffect, useCallback } from 'react';
import type { EntityData } from '../types/simulation';
import { Button } from './ui';
import styles from './EntityInspector.module.css';

interface EntityInspectorProps {
    entity: EntityData | null;
    onClose: () => void;
    onTransfer?: (entityId: number, entityType: string) => void;
}

export function EntityInspector({ entity, onClose, onTransfer }: EntityInspectorProps) {
    const handleKeyDown = useCallback((e: KeyboardEvent) => {
        if (e.key === 'Escape') onClose();
    }, [onClose]);

    useEffect(() => {
        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [handleKeyDown]);

    if (!entity) return null;

    const canTransfer = entity.type === 'fish' || entity.type === 'plant' || entity.type === 'crab';

    return (
        <>
            {/* Backdrop */}
            <div className={styles.backdrop} onClick={onClose} />

            {/* Panel */}
            <div className={styles.panel} role="dialog" aria-label="Entity Inspector">
                <InspectorHeader
                    entity={entity}
                    onClose={onClose}
                    onTransfer={canTransfer && onTransfer ? () => onTransfer(entity.id, entity.type) : undefined}
                />
                <div className={styles.body}>
                    <EnergyBar entity={entity} />
                    {entity.type === 'fish' && <FishSections entity={entity} />}
                    {entity.type === 'plant' && <PlantSections entity={entity} />}
                    {entity.type === 'crab' && <CrabSections entity={entity} />}
                </div>
            </div>
        </>
    );
}

/* ---------- Header ---------- */

function InspectorHeader({ entity, onClose, onTransfer }: {
    entity: EntityData;
    onClose: () => void;
    onTransfer?: () => void;
}) {
    const hue = getEntityHue(entity);
    const typeLabel = entity.type.charAt(0).toUpperCase() + entity.type.slice(1);
    const typeClass = styles[entity.type as keyof typeof styles] ?? '';

    return (
        <div className={styles.header}>
            <div className={styles.headerRow}>
                <div className={styles.headerIdentity}>
                    <div
                        className={styles.colorSwatch}
                        style={{ background: `hsl(${hue}, 70%, 50%)` }}
                    />
                    <div className={styles.headerText}>
                        <span className={`${styles.entityType} ${typeClass}`}>
                            {typeLabel}
                        </span>
                        <div className={styles.entityId}>#{entity.id}</div>
                    </div>
                </div>
                <button className={styles.closeButton} onClick={onClose} aria-label="Close">
                    &times;
                </button>
            </div>
            {onTransfer && (
                <div className={styles.actions}>
                    <Button variant="primary" onClick={onTransfer}>
                        Transfer
                    </Button>
                </div>
            )}
        </div>
    );
}

/* ---------- Energy Bar ---------- */

function EnergyBar({ entity }: { entity: EntityData }) {
    const energy = entity.energy ?? 0;
    const maxEnergy = entity.max_energy ?? 100;
    const pct = maxEnergy > 0 ? Math.min(100, (energy / maxEnergy) * 100) : 0;

    let tierClass = styles.healthy;
    if (pct < 30) tierClass = styles.critical;
    else if (pct < 60) tierClass = styles.low;

    return (
        <div className={styles.energyBarContainer}>
            <div className={styles.energyBarLabel}>
                <span className={styles.energyBarLabelText}>Energy</span>
                <span className={styles.energyBarValue}>
                    {energy.toFixed(0)} / {maxEnergy.toFixed(0)}
                </span>
            </div>
            <div className={styles.energyBarTrack}>
                <div
                    className={`${styles.energyBarFill} ${tierClass}`}
                    style={{ width: `${pct}%` }}
                />
            </div>
        </div>
    );
}

/* ---------- Collapsible Section ---------- */

function Section({ title, defaultOpen = true, children }: {
    title: string;
    defaultOpen?: boolean;
    children: React.ReactNode;
}) {
    const [open, setOpen] = useState(defaultOpen);

    return (
        <div className={styles.section}>
            <button
                className={`${styles.sectionHeader} ${open ? styles.sectionHeaderOpen : ''}`}
                onClick={() => setOpen(!open)}
            >
                <span>{title}</span>
                <span className={`${styles.sectionChevron} ${open ? styles.sectionChevronOpen : ''}`}>
                    &#9660;
                </span>
            </button>
            {open && <div className={styles.sectionContent}>{children}</div>}
        </div>
    );
}

function Stat({ label, value, valueColor }: { label: string; value: string | number; valueColor?: string }) {
    return (
        <div className={styles.statRow}>
            <span className={styles.statLabel}>{label}</span>
            <span className={styles.statValue} style={valueColor ? { color: valueColor } : undefined}>
                {value}
            </span>
        </div>
    );
}

/* ---------- Fish Sections ---------- */

function FishSections({ entity }: { entity: EntityData }) {
    const genome = entity.genome_data;

    return (
        <>
            <Section title="Identity">
                <Stat label="Species" value={entity.species ?? 'unknown'} />
                <Stat label="Generation" value={entity.generation ?? 0} />
                <Stat label="Age" value={`${entity.age ?? 0} frames`} />
                {entity.team && <Stat label="Team" value={entity.team} />}
            </Section>

            <Section title="Vitals">
                <Stat label="Position" value={`${entity.x.toFixed(0)}, ${entity.y.toFixed(0)}`} />
                <Stat
                    label="Velocity"
                    value={`${(entity.vel_x ?? 0).toFixed(1)}, ${(entity.vel_y ?? 0).toFixed(1)}`}
                />
                <Stat label="Size" value={`${entity.width.toFixed(0)} × ${entity.height.toFixed(0)}`} />
            </Section>

            {genome && (
                <Section title="Genome">
                    <Stat label="Speed" value={genome.speed.toFixed(3)} />
                    <Stat label="Size Gene" value={genome.size.toFixed(3)} />
                    <Stat label="Color Hue" value={genome.color_hue.toFixed(3)} />
                    <Stat label="Eye Size" value={genome.eye_size.toFixed(3)} />
                    <Stat label="Pattern Intensity" value={genome.pattern_intensity.toFixed(2)} />
                    <Stat label="Pattern Type" value={genome.pattern_type} />
                </Section>
            )}

            {genome && (
                <Section title="Visual Traits" defaultOpen={false}>
                    <Stat label="Template" value={genome.template_id} />
                    <Stat label="Fin Size" value={genome.fin_size.toFixed(2)} />
                    <Stat label="Tail Size" value={genome.tail_size.toFixed(2)} />
                    <Stat label="Body Aspect" value={genome.body_aspect.toFixed(2)} />
                </Section>
            )}

            {entity.poker_effect_state && (
                <Section title="Poker" defaultOpen={false}>
                    <Stat label="Status" value={entity.poker_effect_state.status} />
                    <Stat
                        label="Amount"
                        value={entity.poker_effect_state.amount}
                        valueColor={entity.poker_effect_state.status === 'won' ? '#4ade80' : entity.poker_effect_state.status === 'lost' ? '#f87171' : undefined}
                    />
                    {entity.poker_effect_state.target_id !== undefined && (
                        <Stat label="Opponent" value={`#${entity.poker_effect_state.target_id}`} />
                    )}
                </Section>
            )}
        </>
    );
}

/* ---------- Plant Sections ---------- */

function PlantSections({ entity }: { entity: EntityData }) {
    const genome = entity.genome;

    return (
        <>
            <Section title="Identity">
                <Stat label="Age" value={`${entity.age ?? 0} frames`} />
                {genome?.type && <Stat label="L-System Type" value={genome.type} />}
                <Stat label="Size Multiplier" value={(entity.size_multiplier ?? 1).toFixed(2)} />
                <Stat label="Iterations" value={entity.iterations ?? 0} />
            </Section>

            <Section title="Vitals">
                <Stat label="Position" value={`${entity.x.toFixed(0)}, ${entity.y.toFixed(0)}`} />
                <Stat label="Size" value={`${entity.width.toFixed(0)} × ${entity.height.toFixed(0)}`} />
            </Section>

            {genome && (
                <Section title="L-System Genome">
                    <Stat label="Angle" value={`${genome.angle.toFixed(1)}°`} />
                    <Stat label="Length Ratio" value={genome.length_ratio.toFixed(3)} />
                    <Stat label="Branch Prob." value={genome.branch_probability.toFixed(3)} />
                    <Stat label="Curve Factor" value={genome.curve_factor.toFixed(3)} />
                    <Stat label="Stem Thickness" value={genome.stem_thickness.toFixed(2)} />
                    <Stat label="Leaf Density" value={genome.leaf_density.toFixed(2)} />
                    <Stat label="Color Hue" value={genome.color_hue.toFixed(3)} />
                    <Stat label="Saturation" value={genome.color_saturation.toFixed(2)} />
                </Section>
            )}

            <Section title="Nectar">
                <Stat
                    label="Nectar Ready"
                    value={entity.nectar_ready ? 'Yes' : 'No'}
                    valueColor={entity.nectar_ready ? '#4ade80' : '#f87171'}
                />
                {genome && (
                    <>
                        <Stat label="Base Energy Rate" value={genome.base_energy_rate.toFixed(3)} />
                        <Stat label="Growth Efficiency" value={genome.growth_efficiency.toFixed(3)} />
                        <Stat label="Nectar Threshold" value={genome.nectar_threshold_ratio.toFixed(2)} />
                    </>
                )}
            </Section>

            {genome && (
                <Section title="Poker Strategy" defaultOpen={false}>
                    {genome.strategy_type && <Stat label="Strategy" value={genome.strategy_type} />}
                    <Stat label="Aggression" value={genome.aggression.toFixed(2)} />
                    <Stat label="Bluff Frequency" value={genome.bluff_frequency.toFixed(2)} />
                    <Stat label="Risk Tolerance" value={genome.risk_tolerance.toFixed(2)} />
                    <Stat label="Fitness Score" value={genome.fitness_score.toFixed(1)} />
                </Section>
            )}
        </>
    );
}

/* ---------- Crab Sections ---------- */

function CrabSections({ entity }: { entity: EntityData }) {
    return (
        <>
            <Section title="Identity">
                <Stat label="Position" value={`${entity.x.toFixed(0)}, ${entity.y.toFixed(0)}`} />
                <Stat label="Size" value={`${entity.width.toFixed(0)} × ${entity.height.toFixed(0)}`} />
            </Section>

            <Section title="Hunting">
                <Stat
                    label="Can Hunt"
                    value={entity.can_hunt ? 'Yes' : 'Cooldown'}
                    valueColor={entity.can_hunt ? '#4ade80' : '#fbbf24'}
                />
                <Stat
                    label="Velocity"
                    value={`${(entity.vel_x ?? 0).toFixed(1)}, ${(entity.vel_y ?? 0).toFixed(1)}`}
                />
            </Section>
        </>
    );
}

/* ---------- Helpers ---------- */

function getEntityHue(entity: EntityData): number {
    if (entity.type === 'fish' && entity.genome_data?.color_hue !== undefined) {
        return entity.genome_data.color_hue * 360;
    }
    if (entity.type === 'plant' && entity.genome?.color_hue !== undefined) {
        return entity.genome.color_hue * 360;
    }
    if (entity.type === 'crab') return 340;
    // Deterministic fallback
    return ((entity.id * 2654435761) >>> 0) % 360;
}
