import { useEffect, useState } from 'react';
import type { SkillBreakthrough } from '../types/skill';

export function dedupeBreakthroughs(records: readonly SkillBreakthrough[]): SkillBreakthrough[] {
    const byId = new Map<string, SkillBreakthrough>();
    for (const record of records) {
        if (record.event_id && !byId.has(record.event_id)) byId.set(record.event_id, record);
    }
    return [...byId.values()].sort((left, right) => left.frame - right.frame);
}

export function useBreakthroughs(records: readonly SkillBreakthrough[], worldId?: string): SkillBreakthrough[] {
    const storageKey = `tank_soccer_breakthroughs_${worldId ?? 'default'}`;
    const [seen, setSeen] = useState<Record<string, true>>(() => {
        if (typeof window === 'undefined') return {};
        try {
            return JSON.parse(window.localStorage.getItem(storageKey) ?? '{}') as Record<string, true>;
        } catch {
            return {};
        }
    });
    const unique = dedupeBreakthroughs(records);
    const unseen = unique.filter((record) => !seen[record.event_id]);

    useEffect(() => {
        if (!unseen.length) return;
        const next = { ...seen };
        unseen.forEach((record) => { next[record.event_id] = true; });
        setSeen(next);
        try {
            window.localStorage.setItem(storageKey, JSON.stringify(next));
        } catch {
            // A storage-disabled browser still gets the current presentation.
        }
    }, [seen, storageKey, unseen]);

    return unseen;
}
