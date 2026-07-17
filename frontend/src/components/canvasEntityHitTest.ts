import type { EntityData } from '../types/simulation';

export function findEntityAtPoint(
    entities: EntityData[],
    worldX: number,
    worldY: number,
    matches: (entity: EntityData) => boolean,
): EntityData | undefined {
    for (let i = entities.length - 1; i >= 0; i -= 1) {
        const entity = entities[i];
        if (!matches(entity)) continue;
        const left = entity.x - entity.width / 2;
        const top = entity.y - entity.height / 2;
        if (worldX >= left && worldX <= left + entity.width && worldY >= top && worldY <= top + entity.height) return entity;
    }
    return undefined;
}
