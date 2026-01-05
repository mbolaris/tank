/**
 * TypeScript types for world modes
 */

export type WorldType = 'tank' | 'petri' | 'soccer_training' | 'soccer';

export const WORLD_TYPES: readonly WorldType[] = ['tank', 'petri', 'soccer_training', 'soccer'] as const;

export const WORLD_TYPE_LABELS: Record<WorldType, string> = {
    tank: 'Tank',
    petri: 'Petri Dish',
    soccer_training: 'Soccer Training',
    soccer: 'Soccer (RCSS)',
};

/**
 * Check if a world type forces top-down view only
 */
export function isTopDownOnly(worldType: WorldType): boolean {
    return worldType === 'petri' || worldType === 'soccer_training' || worldType === 'soccer';
}
