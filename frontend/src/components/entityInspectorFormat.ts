/**
 * Pure display helpers for the entity inspector (U4/E1).
 *
 * Kept out of EntityInspectorDrawer.tsx so the component file only exports
 * components (react-refresh) and the helpers stay unit-testable without a DOM.
 */

const ENTITY_TYPE_LABELS: Record<string, string> = {
    fish: 'Fish',
    plant: 'Plant',
    crab: 'Crab',
    castle: 'Castle',
    ball: 'Ball',
    plant_nectar: 'Nectar',
};

export const STATUS_COPY: Record<string, string> = {
    critical: 'Critically low energy — searching for food',
    hungry: 'Hungry — foraging',
    content: 'Content — building energy toward reproduction',
    full: 'Energy surplus — may reproduce or play',
};

export function entityTypeLabel(entityType: string): string {
    return ENTITY_TYPE_LABELS[entityType] ?? entityType;
}

export function formatTraitName(name: string): string {
    return name.replace(/_/g, ' ');
}

/** 3-tier energy color, matching the canvas energy-bar spec (UI_SPEC 7.5). */
export function energyBarColor(ratio: number): string {
    if (ratio < 0.3) return 'var(--color-danger)';
    if (ratio < 0.6) return 'var(--color-warning)';
    return 'var(--color-success)';
}
