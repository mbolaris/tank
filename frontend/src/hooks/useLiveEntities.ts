import { useMemo } from 'react';
import type { EntityData, SimulationUpdate } from '../types/simulation';

export function useLiveEntities(state: SimulationUpdate | null | undefined): EntityData[] {
    return useMemo(
        () => state?.snapshot?.entities ?? state?.entities ?? [],
        [state?.snapshot?.entities, state?.entities],
    );
}
