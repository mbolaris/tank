import type { EntityData } from '../types/simulation';

/** The object kinds Build Mode lets you pick up and move. */
const DRAGGABLE_OBJECT_TYPES = new Set([
    'castle',
    'algae_reef',
    'protein_grotto',
    'decorative_rock',
]);

/** The draggable build object under a world point, topmost first.
 *
 * Split out of Canvas.tsx, which had grown past the god-file limit. Topmost
 * first matters: objects overlap, and picking up the one drawn underneath is
 * not what the cursor appears to be pointing at.
 */
export function findDraggableObjectAt(
    entities: readonly EntityData[],
    worldX: number,
    worldY: number,
): EntityData | undefined {
    for (let i = entities.length - 1; i >= 0; i -= 1) {
        const entity = entities[i];
        if (!DRAGGABLE_OBJECT_TYPES.has(entity.type)) continue;
        if (
            worldX >= entity.x &&
            worldX <= entity.x + entity.width &&
            worldY >= entity.y &&
            worldY <= entity.y + entity.height
        ) {
            return entity;
        }
    }
    return undefined;
}
