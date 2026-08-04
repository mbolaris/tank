import { useCallback, useEffect, useState } from 'react';
import type { SkillBreakthrough } from '../types/skill';

/**
 * How long a breakthrough card holds the major slot, in ms.
 *
 * Long enough to actually read the record it announces. It used to be marked
 * seen the moment it was *fetched*, so the card could vanish on the very next
 * render - the event was acknowledged without ever having been presented.
 */
export const BREAKTHROUGH_PRESENT_MS = 4000;

export type BreakthroughPhase = 'queued' | 'presenting' | 'acknowledged';

export function dedupeBreakthroughs(records: readonly SkillBreakthrough[]): SkillBreakthrough[] {
    const byId = new Map<string, SkillBreakthrough>();
    for (const record of records) {
        if (record.event_id && !byId.has(record.event_id)) byId.set(record.event_id, record);
    }
    return [...byId.values()].sort((left, right) => left.frame - right.frame);
}

/**
 * Pure queue transition: what should be on screen, and what is still waiting.
 *
 * Deterministic - the queue is frame-ordered and deduped by `event_id`, so the
 * same records always present in the same order. Deliberately one at a time.
 */
export function selectBreakthroughPresentation(
    records: readonly SkillBreakthrough[],
    acknowledgedIds: ReadonlySet<string>,
    options: { blocked?: boolean; holding?: string | null } = {},
): { presenting: SkillBreakthrough | null; queued: SkillBreakthrough[]; acknowledged: SkillBreakthrough[] } {
    const unique = dedupeBreakthroughs(records);
    const acknowledged = unique.filter((record) => acknowledgedIds.has(record.event_id));
    const pending = unique.filter((record) => !acknowledgedIds.has(record.event_id));

    // Whatever is already on screen stays there until its hold completes, even
    // if an earlier-framed record arrives late.
    const held = options.holding ? pending.find((record) => record.event_id === options.holding) : undefined;
    if (held) return { presenting: held, queued: pending.filter((r) => r !== held), acknowledged };

    // A goal or full-time card owns the major slot; the breakthrough waits its
    // turn rather than overlapping it.
    if (options.blocked) return { presenting: null, queued: pending, acknowledged };

    const [next, ...rest] = pending;
    return { presenting: next ?? null, queued: rest, acknowledged };
}

export interface UseBreakthroughsResult {
    /** The one breakthrough currently holding the major broadcast slot. */
    presenting: SkillBreakthrough | null;
    /** Deduped records still waiting behind it. */
    queued: SkillBreakthrough[];
    /** Already presented; kept as compact history in Team Progress. */
    acknowledged: SkillBreakthrough[];
    /** Complete the current presentation early (e.g. reduced motion). */
    acknowledge: (eventId: string) => void;
}

function readAcknowledged(storageKey: string): Set<string> {
    if (typeof window === 'undefined') return new Set();
    try {
        const raw = JSON.parse(window.localStorage.getItem(storageKey) ?? '[]');
        if (Array.isArray(raw)) return new Set(raw as string[]);
        // Older builds persisted a { [id]: true } map.
        if (raw && typeof raw === 'object') return new Set(Object.keys(raw));
        return new Set();
    } catch {
        return new Set();
    }
}

/**
 * Drive breakthroughs through queued -> presenting -> acknowledged.
 *
 * Acknowledgement is persisted only *after* a presentation completes, so a
 * reload mid-card can legitimately show it again while a reload afterwards
 * never will. Nothing here depends on the Progress rail being open - the rail
 * shows history, the broadcast presenter shows the live card.
 */
export function useBreakthroughs(
    records: readonly SkillBreakthrough[],
    worldId?: string,
    options: { blocked?: boolean; holdMs?: number } = {},
): UseBreakthroughsResult {
    const storageKey = `tank_soccer_breakthroughs_ack_${worldId ?? 'default'}`;
    const [acknowledgedIds, setAcknowledgedIds] = useState<Set<string>>(() => readAcknowledged(storageKey));
    const [holding, setHolding] = useState<string | null>(null);

    const acknowledge = useCallback((eventId: string) => {
        if (!eventId) return;
        setAcknowledgedIds((previous) => {
            if (previous.has(eventId)) return previous;
            const next = new Set(previous).add(eventId);
            try {
                window.localStorage.setItem(storageKey, JSON.stringify([...next]));
            } catch {
                // A storage-disabled browser still gets the presentation itself.
            }
            return next;
        });
        setHolding((current) => (current === eventId ? null : current));
    }, [storageKey]);

    const { presenting, queued, acknowledged } = selectBreakthroughPresentation(
        records,
        acknowledgedIds,
        { blocked: options.blocked, holding },
    );

    // Latch the card that just took the slot, so a re-render cannot swap it out
    // underneath the viewer mid-hold.
    const presentingId = presenting?.event_id ?? null;
    useEffect(() => {
        if (presentingId && presentingId !== holding) setHolding(presentingId);
    }, [presentingId, holding]);

    // One timer per presented card; acknowledgement happens when it completes,
    // never merely because the record was fetched. `acknowledge` is stable for
    // a given storage key, so this does not restart on unrelated renders.
    const holdMs = options.holdMs ?? BREAKTHROUGH_PRESENT_MS;
    useEffect(() => {
        if (!presentingId) return;
        const timer = setTimeout(() => acknowledge(presentingId), holdMs);
        return () => clearTimeout(timer);
    }, [presentingId, holdMs, acknowledge]);

    return { presenting, queued, acknowledged, acknowledge };
}
