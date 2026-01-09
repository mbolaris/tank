/**
 * TypeScript types for world modes
 */

export type WorldType = 'tank' | 'petri' | 'soccer';

export const WORLD_TYPES: readonly WorldType[] = ['tank', 'petri'] as const;

export const WORLD_TYPE_LABELS: Record<WorldType, string> = {
    tank: 'Tank',
    petri: 'Petri Dish',
    soccer: 'Soccer Pitch', // Keeping label mapping in case backend sends it, but it won't be in selector options
};

/**
 * Check if a world type forces top-down view only
 */
export function isTopDownOnly(worldType: WorldType): boolean {
    return worldType === 'petri' || worldType === 'soccer';
}
