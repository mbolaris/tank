/**
 * Build Mode's canvas placement maths, lifted out of `TankView`.
 *
 * Placing, ghosting and dragging a tank object all share one rule the view kept
 * re-deriving inline: the pointer names the object's *centre*, while the
 * backend stores its top-left corner. Every one of these handlers therefore
 * subtracts half the object's size, and getting that wrong in one of the three
 * places is exactly the kind of bug that looks like "objects jump when
 * dragged". Here it is written once.
 */

import { useCallback, useState } from 'react';
import type { Command, EntityData } from '../types/simulation';
import type { BuildObjectKind } from './useUiMode';

/** Footprint of each placeable object, in world units. */
export const BUILD_OBJECT_SIZES: Record<BuildObjectKind, [number, number]> = {
    algae_reef: [150, 100],
    protein_grotto: [145, 110],
    decorative_rock: [86, 54],
    castle: [120, 120],
};

export interface BuildGhost {
    kind: BuildObjectKind;
    x: number;
    y: number;
    width: number;
    height: number;
}

interface UseBuildPlacementOptions {
    buildKind: BuildObjectKind | null;
    setBuildKind: (kind: BuildObjectKind | null) => void;
    entities: readonly EntityData[];
    sendCommand: (command: Command) => void;
}

export interface UseBuildPlacementResult {
    ghost: BuildGhost | null;
    /** Commit the held object at a pointer position. */
    place: (x: number, y: number) => void;
    /** Track the pointer while an object is held; clears the ghost when none is. */
    previewAt: (x: number, y: number) => void;
    /** Move an existing object after a drag. */
    moveObject: (objectId: number, x: number, y: number) => void;
}

export function useBuildPlacement({
    buildKind,
    setBuildKind,
    entities,
    sendCommand,
}: UseBuildPlacementOptions): UseBuildPlacementResult {
    const [ghost, setGhost] = useState<BuildGhost | null>(null);

    const place = useCallback(
        (x: number, y: number) => {
            if (!buildKind) return;
            const [width, height] = BUILD_OBJECT_SIZES[buildKind];
            sendCommand({
                command: 'place_tank_object',
                data: { object_kind: buildKind, x: x - width / 2, y: y - height / 2, width, height },
            });
            setBuildKind(null);
            setGhost(null);
        },
        [buildKind, sendCommand, setBuildKind]
    );

    const previewAt = useCallback(
        (x: number, y: number) => {
            if (!buildKind) {
                setGhost(null);
                return;
            }
            const [width, height] = BUILD_OBJECT_SIZES[buildKind];
            setGhost({ kind: buildKind, x: x - width / 2, y: y - height / 2, width, height });
        },
        [buildKind]
    );

    const moveObject = useCallback(
        (objectId: number, x: number, y: number) => {
            // The drag reports a centre; a vanished object reports nothing, and
            // guessing its size would move it somewhere the viewer did not drop it.
            const object = entities.find((entity) => entity.id === objectId);
            if (!object) return;
            sendCommand({
                command: 'move_tank_object',
                data: { object_id: objectId, x: x - object.width / 2, y: y - object.height / 2 },
            });
        },
        [entities, sendCommand]
    );

    return { ghost, place, previewAt, moveObject };
}
